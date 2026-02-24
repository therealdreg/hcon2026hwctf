## ###
# -*- coding: utf-8 -*-
##

# Load specified SVD and generate peripheral memory maps & structures, with RP2350 tweaks.
# Refactored for modern PyGhidra (Python 3).

#@author Thomas Roth (leveldown.de), Ryan Pavlik, Michal Jirku (wejn.org) and Adria Perez Montoro (b1n4ri0).
#@category RP2350
#@keybinding 
#@menupath 
#@toolbar 
#@runtime PyGhidra


# Original sources: 
# - https://github.com/leveldown-security/SVD-Loader-Ghidra
# - https://github.com/wejn/SVD-Loader-Ghidra-RP2040
# License: GPLv3
## ###


from cmsis_svd.parser import SVDParser
from ghidra.program.model.data import StructureDataType, PointerDataType, UnsignedIntegerDataType, DataTypeConflictHandler
from ghidra.program.model.data import UnsignedShortDataType, ByteDataType, UnsignedLongLongDataType
from ghidra.program.model.symbol import SourceType

class MemoryRegion:
    def __init__(self, name, start, end, name_parts=None):
        self.start = start
        self.end = end
        self.name_parts = name_parts if name_parts else [name]
        
    @property
    def name(self):
        return "_".join(self.name_parts)

    def length(self):
        return self.end - self.start

    def __lt__(self, other):
        return self.start < other.start

    def combine_from(self, other):
        self.start = min(self.start, other.start)
        self.end = max(self.end, other.end)
        self.name_parts.extend(other.name_parts)
    
    def overlaps(self, other):
        if other.end < self.start: return False
        if self.end < other.start: return False
        return True
    
    def __str__(self):
        return "{}({}:{})".format(self.name, hex(self.start), hex(self.end))

def reduce_memory_regions(regions):
    regions.sort()
    if not regions: return []
    result = [regions[0]]
    for region in regions[1:]:
        if region.overlaps(result[-1]):
            result[-1].combine_from(region)
        else:
            result.append(region)
    return result

def calculate_peripheral_size(peripheral, default_register_size):
    size = 0
    if not peripheral.registers:
        return 0x1000
    for register in peripheral.registers:
        register_size = default_register_size if not register.size else register.size
        size = max(size, register.address_offset + (register_size // 8))
    return size

def create_memory_block(program, name, start, length, comment):
    try:
        addr = program.getAddressFactory().getDefaultAddressSpace().getAddress(start)
        if program.memory.getBlock(addr) is None:
            block = program.memory.createUninitializedBlock(name, addr, length, False)
            block.setRead(True)
            block.setWrite(True)
            block.setVolatile(True)
            block.setComment(comment)
            return True
    except Exception as e:
        print("[ERROR] Failed to create block {}: {}".format(name, e))
    return False

def generate_peripheral_struct(peripheral, default_size, cache, alias_map):
    length = calculate_peripheral_size(peripheral, default_size)
    if length < 4: length = 4

    derived_name = peripheral.derived_from
    
    if derived_name and derived_name in cache:
        return cache[derived_name], length
    
    struct_name = alias_map.get(peripheral.name, peripheral.name)
    struct = StructureDataType(struct_name, int(length))

    for register in peripheral.registers:
        reg_size = default_size if not register.size else register.size
        byte_size = reg_size // 8
        
        dt = UnsignedIntegerDataType()
        if byte_size == 1: dt = ByteDataType()
        elif byte_size == 2: dt = UnsignedShortDataType()
        elif byte_size == 8: dt = UnsignedLongLongDataType()

        try:
            struct.replaceAtOffset(register.address_offset, dt, byte_size, register.name, register.description)
        except: 
            pass 

    cache[peripheral.name] = struct
    return struct, length

def main():
    print("================================================================================")
    print("[INFO] SVD Loader & Memory Mapper")
    print("[INFO] Target: Generic / RP2040 / RP2350")
    print("================================================================================")

    svd_file = askFile("Choose SVD file", "Load SVD File")
    print("[INFO] Loading SVD file: {}".format(svd_file))

    try:
        parser = SVDParser.for_xml_file(str(svd_file))
        device = parser.get_device()
    except Exception as e:
        print("[ERROR] Critical error parsing SVD file: {}".format(e))
        return

    print("[SUCCESS] SVD Parsed. Device: {}".format(device.name))
    
    cpu_endian = str(device.cpu.endian).lower()
    if "little" not in cpu_endian:
        print("[ERROR] Unsupported Endianness: {}. Only Little Endian is supported.".format(cpu_endian))
        return

    default_register_size = device.size or device.width or 32
    
    # RP2xxx Atomic Access Configuration
    dev_name = str(device.name).upper()
    is_rp_series = "RP2040" in dev_name or "RP2350" in dev_name
    
    address_extras = {}
    address_extras_comments = {}
    peripheral_name_aliases = {}

    if is_rp_series:
        print("[INFO] RP-Series device detected. Enabling atomic access aliases.")
        address_extras = {'xor': 0x1000, 'set': 0x2000, 'clr': 0x3000}
        address_extras_comments = {
            'xor': 'Atomic XOR on write',
            'set': 'Atomic Bitmask SET on write',
            'clr': 'Atomic Bitmask CLEAR on write',
        }
        peripheral_name_aliases = {'UART0': 'UART', 'SPI0': 'SPI', 'I2C0': 'I2C', 'PIO0': 'PIO'}

    prog = currentProgram
    listing = prog.getListing()
    symtbl = prog.getSymbolTable()
    dtm = prog.getDataTypeManager()
    space = prog.getAddressFactory().getDefaultAddressSpace()

    namespace = symtbl.getNamespace("Peripherals", None)
    if not namespace:
        namespace = symtbl.createNameSpace(None, "Peripherals", SourceType.ANALYSIS)

    print("[INFO] Calculating memory regions...")
    memory_regions = []
    
    for peripheral in device.peripherals:
        start = peripheral.base_address
        p_size = 0x1000
        p_offset = 0
        
        if hasattr(peripheral, 'address_blocks') and peripheral.address_blocks:
            block = peripheral.address_blocks[0]
            p_size = block.size
            p_offset = block.offset
        elif hasattr(peripheral, 'address_block') and peripheral.address_block:
             p_size = peripheral.address_block.size
             p_offset = peripheral.address_block.offset
        else:
            p_size = calculate_peripheral_size(peripheral, default_register_size)

        memory_regions.append(MemoryRegion(peripheral.name, start, start + p_offset + p_size))

    memory_regions = reduce_memory_regions(memory_regions)
    
    print("[INFO] Generated Memory Regions:")
    for r in memory_regions:
        print("\t[{}: 0x{:08x} - 0x{:08x}]".format(r.name, r.start, r.end))

    print("[INFO] Creating memory blocks in Ghidra...")
    tid = prog.startTransaction("SVD Loader")
    
    try:
        for r in memory_regions:
            create_memory_block(prog, r.name, r.start, r.length(), "SVD Peripheral Region")
            
            # Apply atomic aliases if RP series and address is in range (0x40000000 - 0xD0000000)
            if is_rp_series and (0x40000000 <= r.start < 0xd0000000):
                for k, v in address_extras.items():
                    create_memory_block(prog, r.name + '_' + k, r.start + v, r.length(), address_extras_comments[k])

        print("[INFO] Generating and applying Data Types...")
        peripherals_cache = {}
        
        for peripheral in device.peripherals:
            if not peripheral.registers:
                continue

            struct, length = generate_peripheral_struct(peripheral, default_register_size, peripherals_cache, peripheral_name_aliases)
            
            # Helper to apply struct to memory
            def apply_struct(name_suffix, offset_delta):
                addr = space.getAddress(peripheral.base_address + offset_delta)
                try:
                    dt = dtm.addDataType(struct, DataTypeConflictHandler.REPLACE_HANDLER)
                    label_name = peripheral.name + name_suffix
                    symtbl.createLabel(addr, label_name, namespace, SourceType.USER_DEFINED)
                    listing.clearCodeUnits(addr, addr.add(length - 1), False)
                    listing.createData(addr, struct)
                except Exception as ex:
                    print("[ERROR] Failed applying struct to {}: {}".format(peripheral.name, ex))

            # Apply Base
            apply_struct("", 0)

            # Apply Atomic Aliases
            if is_rp_series and (0x40000000 <= peripheral.base_address < 0xd0000000):
                for k, v in address_extras.items():
                    apply_struct('_' + k, v)

        print("[SUCCESS] Peripheral loading complete.")

    except Exception as e:
        print("[ERROR] Transaction failed: {}".format(e))
    finally:
        prog.endTransaction(tid, True)
        print("[INFO] Script finished.")

if __name__ == "__main__":
    main()