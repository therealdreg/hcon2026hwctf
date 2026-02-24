# RP2350 CTF Auto-Setup Tool (H-Con 2026 HW Hacking Challenge)
#@author b1n4ri0
#@category RP2350
#@keybinding 
#@menupath
#@toolbar 
#@runtime PyGhidra


from ghidra.program.model.data import PointerDataType
from ghidra.program.model.symbol import SourceType
from java.math import BigInteger

#ROM = 0x00000000
XIP = 0x10000000
SRAM = 0x20000000
#APBP = 0x40000000
#AHBP = 0x50000000
#SIO = 0xd0000000

BINFO_MARKER_START = "\xf2\xeb\x88\x71"
BINFO_MARKER_END = 0xe71aa390
PBIN_BLOCK_MARKER_START = "\xd3\xde\xff\xff"
#PBIN_BLOCK_MARKER_END = 0xab123579

ptr_type = PointerDataType()
prog = currentProgram
mem = prog.getMemory()

def set_rwx(block, r, w, x):
    print("[INFO] Setting permissions for block '{}': R={}, W={}, X={}".format(block.getName(), bool(r), bool(w), bool(x)))
    block.setRead(bool(r))
    block.setWrite(bool(w))
    block.setExecute(bool(x))

def get_binary_info():
    print("[INFO] Searching for Binary Info Marker...")
    matches = findBytes(prog.getImageBase(), BINFO_MARKER_START, 256)
    
    if not matches:
        print("[ERROR] BINARY_INFO_MARKER_START could not be located.")
        return None
    
    if (mem.getInt(matches[0].add(0x10)) & 0xffffffff) == BINFO_MARKER_END:
        print("[SUCCESS] BINARY_INFO_MARKER_START located at {}.".format(matches[0]))

        createLabel(matches[0], "BINARY_INFO_MARKER_START", True)
        createLabel(matches[0].add(0x04), "__binary_info_start", True)
        createLabel(matches[0].add(0x08), "__binary_info_end", True)
        createLabel(matches[0].add(0x0c), "__address_mapping_table", True)
        createLabel(matches[0].add(0x10), "BINARY_INFO_MARKER_END", True)

        createDWord(matches[0])
        createData(matches[0].add(0x04), ptr_type)
        createData(matches[0].add(0x08), ptr_type)
        createData(matches[0].add(0x0c), ptr_type)
        createDWord(matches[0].add(0x10))

        return [matches[0], matches[0].add(0x04), matches[0].add(0x08), matches[0].add(0x0c)]

    print("[ERROR] Binary Info Marker structure validation failed.")
    return None

def get_addr_map(addrptr):
    print("[INFO] Parsing address mapping table at: {}".format(addrptr))
    entries = []
    createLabel(addrptr, "COPY_TABLE_DATA", True)

    while True:
        try:
            src = mem.getInt(addrptr) & 0xffffffff
            if src == 0:
                print("[INFO] End of copy table reached at: {}".format(addrptr))
                createLabel(addrptr, "END_OF_COPY_TABLE_DATA", True)
                createData(addrptr, ptr_type)
                disassemble(addrptr.add(0x04))
                break
            
            createData(addrptr, ptr_type)
            createData(addrptr.add(0x04), ptr_type)
            createData(addrptr.add(0x08), ptr_type)

            src = toAddr(src)
            dst = toAddr(mem.getInt(addrptr.add(0x04)) & 0xffffffff)
            end = toAddr(mem.getInt(addrptr.add(0x08)) & 0xffffffff)
            entries.append([src, dst, end])
            
            addrptr = addrptr.add(0x0c)
        
        except Exception as e:
            print("[ERROR] Failed reading table entry at {}: {}".format(addrptr, e))
            break
    
    print("[INFO] Total mapping entries found: {}".format(len(entries)))
    return entries

def copy_table_data(entries):
    print("[INFO] Initiating data copy from Flash to RAM...")
    
    for i, entry in enumerate(entries):
        src = entry[0]
        dst = entry[1]
        end = entry[2]

        size = end.getOffset() - dst.getOffset()
        
        if size > 0:
            try:
                data = getBytes(src, size)
                setBytes(dst, data)
                print("[INFO] Entry {}: Copied 0x{:x} bytes from {} to {}.".format(i, size, src, dst))
            except Exception as e:
                print("[ERROR] Entry {}: Failed copying block {} -> {}. Exception: {}".format(i, src, dst, e))
        else:
            print("[WARNING] Entry {}: Skipped (Size 0) for {} -> {}.".format(i, src, dst))

    print("[SUCCESS] Data copy process completed.")

def get_entrypoint():
    print("[INFO] Searching for RISC-V Header (PBIN_BLOCK_MARKER)...")
    matches = findBytes(prog.getImageBase(), PBIN_BLOCK_MARKER_START, 1024)
    
    if not matches:
        print("[ERROR] RISC-V Header marker not found within search range.")
        return None

    print("[SUCCESS] RISC-V Header found at {}.".format(matches[0]))
    createLabel(matches[0], "RISC-V_IMAGE_DEF", True)
    
    ep_addr = toAddr(mem.getInt(matches[0].add(0x0c)))
    sp_addr = toAddr(mem.getInt(matches[0].add(0x10)))

    createLabel(ep_addr, "ENTRY_POINT", True)
    createLabel(sp_addr, "STACK_POINTER", True)
    
    createDWord(matches[0])
    createDWord(matches[0].add(0x04))
    createDWord(matches[0].add(0x08))
    createData(matches[0].add(0x0c), ptr_type)
    createData(matches[0].add(0x10), ptr_type)
    createDWord(matches[0].add(0x14))
    createDWord(matches[0].add(0x18))
    createDWord(matches[0].add(0x1c))

    disassemble(matches[0].add(0x20))
    
    print("[INFO] Disassembling entry point at: {}".format(ep_addr))
    disassemble(ep_addr)
    
    createFunction(ep_addr, "entry")
    addEntryPoint(ep_addr)

    return ep_addr

def setup_global_pointer(entry_addr):
    if not entry_addr:
        print("[ERROR] Cannot setup Global Pointer: Invalid entry address.")
        return

    print("[INFO] Calculating Global Pointer (GP) from entry instructions...")
    try:
        i1 = getInstructionAt(entry_addr)
        imm1 = i1.getOpObjects(1)[0].getSignedValue()

        i2 = getInstructionAt(entry_addr.add(4))
        imm2 = i2.getOpObjects(2)[0].getSignedValue()

        gp_val = entry_addr.getOffset() + (imm1 << 12) + imm2
        print("[INFO] Calculated GP Value: 0x{:x}".format(gp_val))

        reg = currentProgram.getRegister("gp")
        ctx = currentProgram.getProgramContext()
        val_big = BigInteger.valueOf(gp_val)
        
        ctx.setValue(reg, entry_addr, toAddr(0x20082000), val_big)
        print("[SUCCESS] GP register set for program context.")

    except Exception as e:
        print("[ERROR] Failed to calculate or set 'gp' register: {}".format(e))

def analyze_entry_calls(entry_addr):
    print("[INFO] Analyzing entry function for runtime calls (init, main, exit)...")
    
    func = getFunctionAt(entry_addr)
    if not func:
        print("[ERROR] Function object not found at entry address {}.".format(entry_addr))
        return

    listing = currentProgram.getListing()
    insts = listing.getInstructions(func.getBody(), True)
    
    found_targets = []
    
    for inst in insts:
        if inst.getMnemonicString() == "jalr":
            refs = inst.getReferencesFrom()
            if refs:
                dest = refs[0].getToAddress()
                if dest not in found_targets:
                    found_targets.append(dest)
                    if len(found_targets) == 3: break
    
    names = ["runtime_init", "main", "exit"]
    
    for i in range(len(found_targets)):
        if i >= len(names): break
        
        tgt = found_targets[i]
        name = names[i]
        
        print("[INFO] Identified call target: {} -> {}".format(tgt, name))
        
        disassemble(tgt)
        f = getFunctionAt(tgt)
        if f:
            f.setName(name, SourceType.USER_DEFINED)
        else:
            createFunction(tgt, name)

def main():
    print("================================================================================")
    print("[INFO] Script Author: b1n4ri0")
    print("[INFO] H-CON 2026 Hardware Hacking Challenge")
    print("[INFO] Note: This script is specifically adapted for the challenge.")
    print("       Future scripts may support universal RP2350 binaries (ARM/RISC-V).")
    print("       However, with minor modifications, it should remain compatible with")
    print("       similar RP2350 on-ram RISC-V binaries.")
    print("================================================================================")

    img = prog.getImageBase()
    tid = prog.startTransaction("RP2350 on_ram .bin configuration")

    try:
        print("[INFO] Configuring XIP Memory Block...")
        mem.getBlock(img).setName("XIP")
        set_rwx(mem.getBlock(img), 1, 0, 0)
        prog.setImageBase(toAddr(XIP), True)

        print("[INFO] Creating and Initializing SRAM Block...")
        sram = mem.createInitializedBlock("SRAM", toAddr(SRAM), 0x82001, 0x00, monitor, False)
        set_rwx(sram, 1, 1, 1)

        addrptr_info = get_binary_info()
        if addrptr_info:
            entries = get_addr_map(toAddr(mem.getInt(addrptr_info[3])))
            copy_table_data(entries)
            
            ep = get_entrypoint()
            if ep:
                setup_global_pointer(ep)
                print("[INFO] Triggering changes-analysis...")
                analyzeChanges(prog)
                analyze_entry_calls(ep)
        else:
            print("[ERROR] Critical binary markers missing. Aborting further analysis.")

    except Exception as e:
        print("[ERROR] Critical failure during configuration: {}".format(e))

    finally:
        print("[INFO] Ending transaction.")
        prog.endTransaction(tid, True)
        
        print("\n\n================================================================================")
        print("[GUIDANCE] Next Steps:")
        print("   1. Execute 'SVD-Loader-RP2350.py' to load peripherals.")
        print("   2. Run Auto Analysis.")
        print("   3. Manually verify decompilation. Some regions may remain undecompiled.")
        print("\t- To disassemble these regions, hover over the address and press 'D'.")
        print("   4. Run Version Tracker.")
        print("   5. Check the (https://github.com/therealdreg/hcon2026hwctf) if further assistance is required.")
        print("================================================================================")

if __name__ == "__main__":
    main()
