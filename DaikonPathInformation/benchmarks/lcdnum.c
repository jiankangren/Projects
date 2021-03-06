/*
 * LCD number (lcdnum) program taken from MDH suite and modified by Adam Betts
 * to consume a test vector supplied on the command line.
 *
 * For this program, the test vector is a single hexadecimal digit
 * The input range is therefore [0..15]
 */

unsigned char
lcdnum (unsigned char a)
{
#ifdef CBMC
//==========> lcdnum : header 1
int __count_20 = 0;
int __count_1_19 = 0;
int __count_2_4 = 0;
int __count_2_5 = 0;
int __count_2_6 = 0;
int __count_2_9 = 0;
int __count_2_12 = 0;
int __count_2_13 = 0;
int __count_2_14 = 0;
int __count_2_17 = 0;
int __count_3_20 = 0;
int __count_7_20 = 0;
int __count_8_20 = 0;
int __count_10_20 = 0;
int __count_11_20 = 0;
int __count_15_20 = 0;
int __count_16_20 = 0;
int __count_18_20 = 0;
#endif
  switch (a)
  {
    case 0x00: // 3
      #ifdef CBMC
      __count_3_20++;
      __count_20++;
      #endif
      return 0; //=0
    case 0x01: // 4
      #ifdef CBMC
      __count_2_4++;
      __count_20++;
      #endif
      return 0x24; //=36
    case 0x02: // 5
      #ifdef CBMC
      __count_2_5++;
      __count_20++;
      #endif
      return 1 + 4 + 8 + 16 + 64; //=93
    case 0x03: // 6
      #ifdef CBMC
      __count_2_6++;
      __count_20++;
      #endif
      return 1 + 4 + 8 + 32 + 64; //=109
    case 0x04: // 7
      #ifdef CBMC
      __count_7_20++;
      __count_20++;
      #endif
      return 2 + 4 + 8 + 32; //=46
    case 0x05: // 8
      #ifdef CBMC
      __count_8_20++;
      __count_20++;
      #endif
      return 1 + 4 + 8 + 16 + 64; //=93
    case 0x06: // 9
      #ifdef CBMC
      __count_2_9++;
      __count_20++;
      #endif
      return 1 + 2 + 8 + 16 + 32 + 64; //=123
    case 0x07: // 10
      #ifdef CBMC
      __count_10_20++;
      __count_20++;
      #endif
      return 1 + 4 + 32; //=37
    case 0x08: // 11
      #ifdef CBMC
      __count_11_20++;
      __count_20++;
      #endif
      return 0x7F; /* light all */ //=127
    case 0x09: // 12
      #ifdef CBMC
      __count_2_12++;
      __count_20++;
      #endif
      return 0x0F + 32 + 64; //=111
    case 0x0A: // 13
      #ifdef CBMC
      __count_2_13++;
      __count_20++;
      #endif
      return 0x0F + 16 + 32; //=63
    case 0x0B: // 14
      #ifdef CBMC
      __count_2_14++;
      __count_20++;
      #endif
      return 2 + 8 + 16 + 32 + 64; //=122
    case 0x0C: // 15
      #ifdef CBMC
      __count_15_20++;
      __count_20++;
      #endif
      return 1 + 2 + 16 + 64; //=83
    case 0x0D: // 16
      #ifdef CBMC
      __count_16_20++;
      __count_20++;
      #endif
      return 4 + 8 + 16 + 32 + 64; //=124
    case 0x0E: // 17
      #ifdef CBMC
      __count_2_17++;
      __count_20++;
      #endif
      return 1 + 2 + 8 + 16 + 64; //=91
    case 0x0F: // 18
      #ifdef CBMC
      __count_18_20++;
      __count_20++;
      #endif
      return 1 + 2 + 8 + 16; //=27
  }

  // 19
  #ifdef CBMC
  __count_1_19++;
  __count_20++;
  #endif
  
  #ifdef CBMC
assert(__count_2_12 <= 1); // Upper capacity constraint
assert(__count_2_13 == 0); // Dead code
assert(__count_2_14 == 0); // Dead code
assert(__count_18_20 <= 1); // Upper capacity constraint
assert(__count_3_20 <= 1); // Upper capacity constraint
assert(__count_7_20 == 0); // Dead code
assert(__count_8_20 <= 1); // Upper capacity constraint
assert(__count_10_20 <= 1); // Upper capacity constraint
assert(__count_11_20 <= 1); // Upper capacity constraint
assert(__count_15_20 <= 1); // Upper capacity constraint
assert(__count_16_20 == 0); // Dead code
//assert(__count_1_19 == 0); // Execution dependence
#endif

  return 0;
}

int
main (int argc, char *argv[])
{
  int i;
  volatile unsigned char OUT;
  unsigned char a;

  /*
   * One integer must be supplied
   */
  if (argc != 2)
  {
    return 1;
  }

  a = atoi (argv[1]);
  
  #ifdef CBMC
  __CPROVER_assume(a >= 0 && a <= 15);
  #endif

  for (i = 0; i < 10; i++)
  {
    if (i < 5)
    {
      a = a & 0x0F;
      OUT = lcdnum(a);
    }
  }

  return 0;
}

