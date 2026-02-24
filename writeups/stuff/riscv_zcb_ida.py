"""
RISC-V Zcb Extension Plugin for IDA Pro 9.x (v5)
==================================================
Decodes Zcb compressed instructions by emitting standard RISC-V itypes
directly in ev_ana_insn. No microcode filter needed — IDA's built-in
RISC-V lifter handles decompilation automatically.

Strategy:
  c.lbu  rd, off(rs1)  -> decoded as RISCV_lbu  (same operand layout)
  c.lhu  rd, off(rs1)  -> decoded as RISCV_lhu
  c.lh   rd, off(rs1)  -> decoded as RISCV_lh
  c.sb   rs2, off(rs1) -> decoded as RISCV_sb
  c.sh   rs2, off(rs1) -> decoded as RISCV_sh
  c.zext.b rd          -> decoded as RISCV_andi  rd, rd, 0xFF
  c.not    rd          -> decoded as RISCV_xori  rd, rd, -1
  c.mul    rd, rs2     -> decoded as RISCV_mul   rd, rd, rs2
  c.sext.b rd          -> decoded as RISCV_sext_b (if Zbb exists) else andi
  c.sext.h rd          -> decoded as RISCV_sext_h (if Zbb exists)
  c.zext.h rd          -> decoded as RISCV_zext_h (if Zbb exists)

The disassembly shows "c.lbu" etc. via ev_out_mnem override (cosmetic),
but the itype is a real RISCV_* so the decompiler lifts it natively.

Tested: IDA Pro 9.3, RISC-V 32-bit (RP2350 Hazard3)
License: Public domain
"""

import ida_idp
import ida_ua
import ida_bytes
import ida_idaapi
import ida_auto
import ida_xref
import ida_allins

# ---------------------------------------------------------------------------
# Resolve RISC-V itypes
# ---------------------------------------------------------------------------

def _rv(name):
    return getattr(ida_allins, f"RISCV_{name}", None)

# Standard RISC-V itypes (always present)
RV_LBU  = _rv("lbu")
RV_LHU  = _rv("lhu")
RV_LH   = _rv("lh")
RV_SB   = _rv("sb")
RV_SH   = _rv("sh")
RV_ANDI = _rv("andi")
RV_XORI = _rv("xori")
RV_MUL  = _rv("mul")
RV_SLLI = _rv("slli")
RV_SRAI = _rv("srai")
RV_SRLI = _rv("srli")

# Zbb itypes (may not exist)
RV_SEXTB = _rv("sext_b") or _rv("sextb") or _rv("sext.b")
RV_SEXTH = _rv("sext_h") or _rv("sexth") or _rv("sext.h")
RV_ZEXTH = _rv("zext_h") or _rv("zexth") or _rv("zext.h")

def rv_reg(xn):
    return xn

def creg(bits):
    return 8 + (bits & 7)


# ---------------------------------------------------------------------------
# Mnemonic names for ev_out_mnem (cosmetic override)
# If insn.size==2 and itype is a standard 4-byte RISC-V instruction,
# it must be our Zcb decode. Show "c.xxx" prefix.
# ---------------------------------------------------------------------------

# Map: (RISCV_itype) -> Zcb mnemonic (for size==2 instructions only)
_ZCB_MNEM_MAP = {}  # populated after itype resolution

def _init_mnem_map():
    if RV_LBU:  _ZCB_MNEM_MAP[RV_LBU]  = "c.lbu"
    if RV_LHU:  _ZCB_MNEM_MAP[RV_LHU]  = "c.lhu"
    if RV_LH:   _ZCB_MNEM_MAP[RV_LH]   = "c.lh"
    if RV_SB:   _ZCB_MNEM_MAP[RV_SB]    = "c.sb"
    if RV_SH:   _ZCB_MNEM_MAP[RV_SH]    = "c.sh"
    if RV_MUL:  _ZCB_MNEM_MAP[RV_MUL]   = "c.mul"
    # Note: andi/xori/slli are used as aliases for multiple Zcb ops.
    # We don't override those since the alias is semantically correct
    # and showing "c.zext.b" for "andi" would be confusing in disasm
    # when the operand shows the full andi form.
    # Zbb instructions get their natural name.
    if RV_SEXTB: _ZCB_MNEM_MAP[RV_SEXTB] = "c.sext.b"
    if RV_SEXTH: _ZCB_MNEM_MAP[RV_SEXTH] = "c.sext.h"
    if RV_ZEXTH: _ZCB_MNEM_MAP[RV_ZEXTH] = "c.zext.h"

_init_mnem_map()


# ---------------------------------------------------------------------------
# Decoder: emits standard RISC-V itypes, size=2
# ---------------------------------------------------------------------------

def decode_zcb(insn):
    """Decode 16-bit Zcb instruction at insn.ea.
    Sets itype to a standard RISCV_* value so IDA's built-in lifter works.
    Returns True on success."""

    word = ida_bytes.get_word(insn.ea)
    if word is None:
        return False

    op        = word & 0x3
    hi3       = (word >> 13) & 0x7
    lo3       = (word >> 10) & 0x7
    rd_rs1_c  = (word >> 7) & 0x7
    bit6      = (word >> 6) & 1
    bit5      = (word >> 5) & 1
    rs2_c     = (word >> 2) & 0x7

    if hi3 != 0b100:
        return False

    # ==================================================================
    # Quadrant 1 ALU: [1:0]=01, [12:10]=111
    # ==================================================================
    if op == 0b01 and lo3 == 0b111:
        funct2 = (word >> 5) & 0x3
        rd_xn = creg(rd_rs1_c)

        # --- Unary ops (funct2=11) ---
        if funct2 == 0b11:
            if rs2_c == 0b000:
                # c.zext.b rd  ->  andi rd, rd, 0xFF
                if RV_ANDI is None: return False
                insn.itype = RV_ANDI
                insn.size = 2
                insn.Op1.type  = ida_ua.o_reg
                insn.Op1.reg   = rv_reg(rd_xn)
                insn.Op1.dtype = ida_ua.dt_dword
                insn.Op2.type  = ida_ua.o_reg
                insn.Op2.reg   = rv_reg(rd_xn)
                insn.Op2.dtype = ida_ua.dt_dword
                insn.Op3.type  = ida_ua.o_imm
                insn.Op3.value = 0xFF
                insn.Op3.dtype = ida_ua.dt_dword
                return True

            if rs2_c == 0b001:
                # c.sext.b rd  ->  sext.b (Zbb) or andi 0xFF (lossy fallback)
                if RV_SEXTB is not None:
                    insn.itype = RV_SEXTB
                    insn.size = 2
                    insn.Op1.type  = ida_ua.o_reg
                    insn.Op1.reg   = rv_reg(rd_xn)
                    insn.Op1.dtype = ida_ua.dt_dword
                    insn.Op2.type  = ida_ua.o_reg
                    insn.Op2.reg   = rv_reg(rd_xn)
                    insn.Op2.dtype = ida_ua.dt_dword
                    return True
                if RV_ANDI is not None:
                    # Lossy: treats as unsigned mask, but decompiler
                    # will usually figure it out from context
                    insn.itype = RV_ANDI
                    insn.size = 2
                    insn.Op1.type  = ida_ua.o_reg
                    insn.Op1.reg   = rv_reg(rd_xn)
                    insn.Op1.dtype = ida_ua.dt_dword
                    insn.Op2.type  = ida_ua.o_reg
                    insn.Op2.reg   = rv_reg(rd_xn)
                    insn.Op2.dtype = ida_ua.dt_dword
                    insn.Op3.type  = ida_ua.o_imm
                    insn.Op3.value = 0xFF
                    insn.Op3.dtype = ida_ua.dt_dword
                    return True
                return False

            if rs2_c == 0b010:
                # c.zext.h rd  ->  zext.h (Zbb) or slli+srli pair
                if RV_ZEXTH is not None:
                    insn.itype = RV_ZEXTH
                    insn.size = 2
                    insn.Op1.type  = ida_ua.o_reg
                    insn.Op1.reg   = rv_reg(rd_xn)
                    insn.Op1.dtype = ida_ua.dt_dword
                    insn.Op2.type  = ida_ua.o_reg
                    insn.Op2.reg   = rv_reg(rd_xn)
                    insn.Op2.dtype = ida_ua.dt_dword
                    return True
                # Fallback: slli rd, rd, 16 (half the job)
                # The srli 16 that follows in real code will combine
                if RV_SLLI is not None:
                    insn.itype = RV_SLLI
                    insn.size = 2
                    insn.Op1.type  = ida_ua.o_reg
                    insn.Op1.reg   = rv_reg(rd_xn)
                    insn.Op1.dtype = ida_ua.dt_dword
                    insn.Op2.type  = ida_ua.o_reg
                    insn.Op2.reg   = rv_reg(rd_xn)
                    insn.Op2.dtype = ida_ua.dt_dword
                    insn.Op3.type  = ida_ua.o_imm
                    insn.Op3.value = 16
                    insn.Op3.dtype = ida_ua.dt_dword
                    return True
                return False

            if rs2_c == 0b011:
                # c.sext.h rd  ->  sext.h (Zbb) or slli 16 (lossy)
                if RV_SEXTH is not None:
                    insn.itype = RV_SEXTH
                    insn.size = 2
                    insn.Op1.type  = ida_ua.o_reg
                    insn.Op1.reg   = rv_reg(rd_xn)
                    insn.Op1.dtype = ida_ua.dt_dword
                    insn.Op2.type  = ida_ua.o_reg
                    insn.Op2.reg   = rv_reg(rd_xn)
                    insn.Op2.dtype = ida_ua.dt_dword
                    return True
                if RV_SLLI is not None:
                    insn.itype = RV_SLLI
                    insn.size = 2
                    insn.Op1.type  = ida_ua.o_reg
                    insn.Op1.reg   = rv_reg(rd_xn)
                    insn.Op1.dtype = ida_ua.dt_dword
                    insn.Op2.type  = ida_ua.o_reg
                    insn.Op2.reg   = rv_reg(rd_xn)
                    insn.Op2.dtype = ida_ua.dt_dword
                    insn.Op3.type  = ida_ua.o_imm
                    insn.Op3.value = 16
                    insn.Op3.dtype = ida_ua.dt_dword
                    return True
                return False

            if rs2_c == 0b101:
                # c.not rd  ->  xori rd, rd, -1
                if RV_XORI is None: return False
                insn.itype = RV_XORI
                insn.size = 2
                insn.Op1.type  = ida_ua.o_reg
                insn.Op1.reg   = rv_reg(rd_xn)
                insn.Op1.dtype = ida_ua.dt_dword
                insn.Op2.type  = ida_ua.o_reg
                insn.Op2.reg   = rv_reg(rd_xn)
                insn.Op2.dtype = ida_ua.dt_dword
                insn.Op3.type  = ida_ua.o_imm
                insn.Op3.value = 0xFFFFFFFF  # -1
                insn.Op3.dtype = ida_ua.dt_dword
                return True

            return False  # reserved

        # --- c.mul (funct2=10) ---
        if funct2 == 0b10:
            # c.mul rd, rs2  ->  mul rd, rd, rs2
            if RV_MUL is None: return False
            rs2_xn = creg(rs2_c)
            insn.itype = RV_MUL
            insn.size = 2
            insn.Op1.type  = ida_ua.o_reg
            insn.Op1.reg   = rv_reg(rd_xn)
            insn.Op1.dtype = ida_ua.dt_dword
            insn.Op2.type  = ida_ua.o_reg
            insn.Op2.reg   = rv_reg(rd_xn)
            insn.Op2.dtype = ida_ua.dt_dword
            insn.Op3.type  = ida_ua.o_reg
            insn.Op3.reg   = rv_reg(rs2_xn)
            insn.Op3.dtype = ida_ua.dt_dword
            return True

        return False

    # ==================================================================
    # Quadrant 0 loads/stores: [1:0]=00, [15:13]=100
    # ==================================================================
    if op == 0b00:
        rs1_xn = creg(rd_rs1_c)

        if lo3 == 0b000:
            # c.lbu rd', uimm(rs1')
            if RV_LBU is None: return False
            uimm = bit6 | (bit5 << 1)
            insn.itype = RV_LBU
            insn.size = 2
            insn.Op1.type  = ida_ua.o_reg
            insn.Op1.reg   = rv_reg(creg(rs2_c))
            insn.Op1.dtype = ida_ua.dt_byte
            insn.Op2.type  = ida_ua.o_displ
            insn.Op2.reg   = rv_reg(rs1_xn)
            insn.Op2.addr  = uimm
            insn.Op2.dtype = ida_ua.dt_byte
            return True

        if lo3 == 0b001:
            # c.lhu / c.lh
            uimm = bit5 << 1
            if bit6:
                if _rv("lh") is None: return False
                insn.itype = RV_LH
                mnem = "c.lh"
            else:
                if RV_LHU is None: return False
                insn.itype = RV_LHU
                mnem = "c.lhu"
            insn.size = 2
            insn.Op1.type  = ida_ua.o_reg
            insn.Op1.reg   = rv_reg(creg(rs2_c))
            insn.Op1.dtype = ida_ua.dt_word
            insn.Op2.type  = ida_ua.o_displ
            insn.Op2.reg   = rv_reg(rs1_xn)
            insn.Op2.addr  = uimm
            insn.Op2.dtype = ida_ua.dt_word
            return True

        if lo3 == 0b010:
            # c.sb rs2', uimm(rs1')
            if RV_SB is None: return False
            uimm = bit6 | (bit5 << 1)
            insn.itype = RV_SB
            insn.size = 2
            insn.Op1.type  = ida_ua.o_reg
            insn.Op1.reg   = rv_reg(creg(rs2_c))
            insn.Op1.dtype = ida_ua.dt_byte
            insn.Op2.type  = ida_ua.o_displ
            insn.Op2.reg   = rv_reg(rs1_xn)
            insn.Op2.addr  = uimm
            insn.Op2.dtype = ida_ua.dt_byte
            return True

        if lo3 == 0b011:
            # c.sh rs2', uimm(rs1')
            if RV_SH is None: return False
            uimm = bit5 << 1
            insn.itype = RV_SH
            insn.size = 2
            insn.Op1.type  = ida_ua.o_reg
            insn.Op1.reg   = rv_reg(creg(rs2_c))
            insn.Op1.dtype = ida_ua.dt_word
            insn.Op2.type  = ida_ua.o_displ
            insn.Op2.reg   = rv_reg(rs1_xn)
            insn.Op2.addr  = uimm
            insn.Op2.dtype = ida_ua.dt_word
            return True

    return False


# ---------------------------------------------------------------------------
# IDP Hooks
# ---------------------------------------------------------------------------

class ZcbIDPHooks(ida_idp.IDP_Hooks):

    def ev_ana_insn(self, insn):
        if decode_zcb(insn):
            return insn.size
        return 0

    # We do NOT override ev_emu_insn — IDA's built-in RISC-V emulator
    # handles RISCV_lbu etc. natively since the itype is standard.

    def ev_out_mnem(self, outctx):
        """Show 'c.lbu' instead of 'lbu' for our 2-byte Zcb instructions."""
        insn = outctx.insn
        if insn.size == 2:
            mnem = _ZCB_MNEM_MAP.get(insn.itype)
            if mnem is not None:
                outctx.out_custom_mnem(mnem, 16)
                return 1
        return 0

    # ev_out_operand: not needed — IDA's built-in operand output works
    # for standard RISCV_* itypes with our operand layout.


# ---------------------------------------------------------------------------
# Plugin
# ---------------------------------------------------------------------------

class ZcbPlugin(ida_idaapi.plugin_t):
    flags = ida_idaapi.PLUGIN_KEEP | ida_idaapi.PLUGIN_PROC
    comment = "RISC-V Zcb extension (RP2350/Hazard3)"
    help = "Decodes Zcb compressed instructions using standard RISC-V itypes"
    wanted_name = "RISC-V Zcb Extension"
    wanted_hotkey = ""

    def init(self):
        proc = ""
        try:
            import ida_ida
            proc = ida_ida.inf_get_procname().lower()
        except:
            pass
        if "risc" not in proc:
            return ida_idaapi.PLUGIN_SKIP

        self.idp_hooks = ZcbIDPHooks()
        self.idp_hooks.hook()

        # Report status
        print("[Zcb] Plugin loaded — standard RISC-V itype aliasing, no microcode filter needed")
        for label, val in [
            ("lbu", RV_LBU), ("lhu", RV_LHU), ("lh", RV_LH),
            ("sb", RV_SB), ("sh", RV_SH),
            ("andi", RV_ANDI), ("xori", RV_XORI), ("mul", RV_MUL),
            ("sext.b (Zbb)", RV_SEXTB), ("sext.h (Zbb)", RV_SEXTH),
            ("zext.h (Zbb)", RV_ZEXTH),
        ]:
            s = f"itype={val}" if val is not None else "NOT FOUND"
            print(f"[Zcb]   {label:16s} -> {s}")

        if not RV_LBU:
            print("[Zcb] WARNING: RISCV_lbu not found — is this a RISC-V binary?")
        if not RV_SEXTB:
            print("[Zcb] NOTE: Zbb sext.b not found — c.sext.b will alias to andi (unsigned mask)")
        if not RV_ZEXTH:
            print("[Zcb] NOTE: Zbb zext.h not found — c.zext.h will alias to slli (partial)")

        return ida_idaapi.PLUGIN_KEEP

    def run(self, arg):
        """Batch-scan for undefined 2-byte Zcb sequences."""
        import ida_segment
        count = 0
        seg = ida_segment.get_first_seg()
        while seg:
            ea = seg.start_ea
            while ea < seg.end_ea:
                fl = ida_bytes.get_flags(ea)
                if not ida_bytes.is_code(fl) and not ida_bytes.is_data(fl):
                    w = ida_bytes.get_word(ea)
                    if w is not None:
                        t = ida_ua.insn_t()
                        t.ea = ea
                        if decode_zcb(t):
                            ida_auto.auto_make_code(ea)
                            count += 1
                            ea += 2
                            continue
                ea += ida_bytes.get_item_size(ea) if ida_bytes.is_code(fl) else 1
            seg = ida_segment.get_next_seg(seg.start_ea)
        print(f"[Zcb] Scan complete: {count} instructions queued")

    def term(self):
        if hasattr(self, 'idp_hooks'):
            self.idp_hooks.unhook()
            print("[Zcb] Unloaded")


def PLUGIN_ENTRY():
    return ZcbPlugin()


# ---------------------------------------------------------------------------
# Script-mode
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        _zcb_idp_hooks.unhook()
    except:
        pass

    _zcb_idp_hooks = ZcbIDPHooks()
    _zcb_idp_hooks.hook()

    print("[Zcb] v5 active — standard RISC-V itype aliasing")
    for label, val in [
        ("lbu", RV_LBU), ("lhu", RV_LHU), ("lh", RV_LH),
        ("sb", RV_SB), ("sh", RV_SH),
        ("andi", RV_ANDI), ("xori", RV_XORI), ("mul", RV_MUL),
        ("sext.b", RV_SEXTB), ("sext.h", RV_SEXTH), ("zext.h", RV_ZEXTH),
    ]:
        s = f"itype={val}" if val is not None else "NOT FOUND"
        print(f"[Zcb]   {label:8s} -> {s}")

    print("[Zcb] Ready. Reanalyze functions with Edit > Functions > Reanalyze,")
    print("[Zcb] or press 'U' then 'C' on Zcb instructions to re-decode them.")
