/*
 * Finite Impulse Respone (FIR) function taken from MDH suite and modified
 * by Adam Betts to consume a test vector supplied on the command line.
 *
 * For this program, the test vector consists of ???
 */

/**************************************************************************
 fir_filter_int - Filters int data array based on passed int coefficients.

 The length of the input and output arrays are equal and are allocated by the caller.
 The length of the coefficient array is passed.
 An integer scale factor (passed) is used to divide the accumulation result.

 in          integer pointer to input array
 out         integer pointer to output array
 in_len      length of input and output arrays
 coef        integer pointer to coefficient array
 coef_len    length of coefficient array
 scale       scale factor to divide after accumulation
 *************************************************************************/

void
fir_filter_int (long* in, long* out, long in_len, long* coef, long coef_len,
    long scale)
{
  long i;
  long j;
  long coef_len2;
  long acc_length;
  long acc;
  long *in_ptr;
  long *data_ptr;
  long *coef_start;
  long *coef_ptr;
  long *in_end;

  /* set up for coefficients */
  coef_start = coef;
  coef_len2 = (coef_len + 1) >> 1;

  /* set up input data pointers */
  in_end = in + in_len - 1;
  in_ptr = in + coef_len2 - 1;

  /* initial value of accumulation length for startup */
  acc_length = coef_len2;

  for (i = 0; i < in_len; i++)
  {
    /* set up pointer for accumulation */
    data_ptr = in_ptr;
    coef_ptr = coef_start;

    /* do accumulation and write result with scale factor */
    acc = (long) (*coef_ptr++) * (*data_ptr--);
    for (j = 1; j < acc_length; j++)
    {
      acc += (long) (*coef_ptr++) * (*data_ptr--);
    }
    *out++ = (int) (acc / scale);

    /* check for end case */
    if (in_ptr == in_end)
    {
      acc_length--; /* one shorter each time */
      coef_start++; /* next coefficient each time */
    }
    else
    {
      /* if not at end, then check for startup, add to input pointer */
      if (acc_length < coef_len)
      {
        acc_length++;
      }
      in_ptr++;
    }
  }
}

/*--------------------------------------------------
 *---- INPUT DATA FOR TESTING
 *--------------------------------------------------*/

long in_data[701] =
  {0x0, 0x0, 0x0, 0x0, 0x7f, 0x79, 0x72, 0x79, 0xd, 0xd, 0x0, 0x3, 0x5, 0x2,
      0x3, 0x7f, 0x7f, 0x2, 0x7e, 0x0, 0x1, 0x7e, 0x1, 0x1, 0x7f, 0x0, 0x7f,
      0x0, 0x2, 0x1, 0x1, 0x3, 0x1, 0x7f, 0x1, 0x0, 0x1, 0x1, 0x7d, 0x7b, 0x73,
      0x6a, 0x77, 0x10, 0xe, 0x1, 0x5, 0x5, 0x5, 0x5, 0x7d, 0x0, 0x2, 0x7d,
      0x0, 0x0, 0x7e, 0x1, 0x7e, 0x7f, 0x3, 0x7c, 0x7e, 0x6, 0x0, 0x7e, 0x3,
      0x2, 0x7f, 0x7e, 0x7f, 0x2, 0x1, 0x7f, 0x1, 0x1, 0x0, 0x3, 0x0, 0x7f,
      0x2, 0x0, 0x7f, 0x3, 0x1, 0x0, 0x0, 0x7d, 0x0, 0x3, 0x0, 0x7e, 0x7f, 0x2,
      0x1, 0x7e, 0x0, 0x3, 0x7f, 0x7d, 0x1, 0x1, 0x1, 0x7f, 0x0, 0x5, 0x0,
      0x7f, 0x2, 0x7e, 0x7f, 0x2, 0x1, 0x0, 0x7e, 0x0, 0x5, 0x0, 0x7f, 0x0,
      0x7e, 0x1, 0x0, 0x7d, 0x1, 0x3, 0x7f, 0x0, 0x0, 0x7e, 0x2, 0x3, 0x7e,
      0x7d, 0x72, 0x68, 0x71, 0x5, 0xc, 0x7, 0x2, 0x6, 0xd, 0x5, 0x7d, 0x3,
      0x2, 0x7f, 0x0, 0x79, 0x7a, 0x3, 0x7e, 0x7d, 0x0, 0x7d, 0x2, 0x1, 0x7d,
      0x8, 0x3, 0x7c, 0x6, 0x0, 0x7a, 0x6, 0x2, 0x7c, 0x3, 0x7e, 0x79, 0x6,
      0x5, 0x74, 0x7f, 0xd, 0x7a, 0x78, 0x6, 0x5, 0x1, 0x0, 0x7d, 0x1, 0x4,
      0x7c, 0x7f, 0x3, 0x7f, 0x5, 0x3, 0x7a, 0x6, 0xa, 0x76, 0x7c, 0xa, 0x7c,
      0x7f, 0x6, 0x79, 0x3, 0xc, 0x75, 0x78, 0xa, 0x0, 0x79, 0x3, 0x7e, 0x7c,
      0x6, 0x0, 0x79, 0x2, 0x7e, 0x7f, 0x6, 0x76, 0x7f, 0xd, 0x79, 0x7f, 0x6,
      0x79, 0x6, 0x3, 0x71, 0x6, 0xa, 0x73, 0x7f, 0xa, 0x0, 0x7f, 0x7a, 0x7c,
      0xa, 0x0, 0x75, 0x7f, 0xc, 0xa, 0x7c, 0x79, 0x9, 0xd, 0x7d, 0x7a, 0x5,
      0xb, 0xa, 0x79, 0x7c, 0x16, 0x3, 0x72, 0xd, 0x7, 0x79, 0xc, 0x7, 0x7a,
      0xb, 0x7, 0x7a, 0xa, 0x7, 0x79, 0xa, 0x5, 0x75, 0x6, 0x5, 0x79, 0x5, 0x6,
      0x1, 0x6, 0x0, 0x7a, 0x2, 0x7, 0x3, 0x7d, 0x1, 0xa, 0x7, 0x2, 0x7f, 0x7f,
      0x9, 0x7, 0x79, 0x79, 0x6, 0x8, 0x7d, 0x7a, 0x6, 0xc, 0x6, 0x7d, 0x7f,
      0xd, 0x7, 0x79, 0x1, 0x6, 0x7f, 0x7f, 0x2, 0x3, 0x1, 0x7e, 0x1, 0x1,
      0x7d, 0x1, 0x0, 0x7d, 0x6, 0x3, 0x7d, 0x5, 0x7, 0x7f, 0x7c, 0x1, 0x6,
      0x6, 0x7c, 0x7a, 0x7, 0xa, 0x0, 0x78, 0x1, 0x8, 0x0, 0x79, 0x7a, 0x4,
      0xa, 0x0, 0x78, 0x1, 0x6, 0x7a, 0x75, 0x7a, 0x0, 0x0, 0x79, 0x76, 0x7f,
      0x7, 0x0, 0x7a, 0x7d, 0x2, 0x4, 0x7c, 0x7a, 0x2, 0x5, 0x7c, 0x7a, 0x7d,
      0x7f, 0x0, 0x78, 0x75, 0x7f, 0x0, 0x79, 0x78, 0x79, 0x1, 0x3, 0x79, 0x79,
      0x0, 0x0, 0x7f, 0x7f, 0x79, 0x7f, 0x2, 0x7a, 0x7c, 0x7d, 0x7c, 0x7f,
      0x7d, 0x79, 0x7d, 0x0, 0x79, 0x7a, 0x7c, 0x7d, 0x0, 0x7d, 0x7d, 0x0, 0x0,
      0x0, 0x0, 0x7d, 0x7d, 0x0, 0x7d, 0x7e, 0x0, 0x7e, 0x3, 0x3, 0x7d, 0x1,
      0x5, 0x0, 0x7e, 0x7d, 0x7f, 0x3, 0x7d, 0x79, 0x1, 0x2, 0x7d, 0x7f, 0x1,
      0x0, 0x0, 0x7f, 0x7f, 0x7e, 0x7f, 0x0, 0x7f, 0x0, 0x7c, 0x7d, 0x0, 0x79,
      0x78, 0x7c, 0x7c, 0x7b, 0x7b, 0x7d, 0x7f, 0x0, 0x0, 0x7f, 0x0, 0x1, 0x2,
      0x0, 0x7f, 0x0, 0x0, 0x0, 0x7f, 0x7e, 0x0, 0x0, 0x7f, 0x0, 0x2, 0x1, 0x2,
      0x6, 0x5, 0x3, 0x6, 0x8, 0x5, 0x2, 0x1, 0x1, 0x3, 0x0, 0x7d, 0x7f, 0x0,
      0x7f, 0x7e, 0x0, 0x2, 0x3, 0x2, 0x1, 0x2, 0x3, 0x1, 0x7c, 0x7d, 0x0, 0x0,
      0x7e, 0x7c, 0x7f, 0x1, 0x0, 0x7e, 0x7c, 0x7f, 0x1, 0x0, 0x7e, 0x7f, 0x2,
      0x3, 0x1, 0x0, 0x4, 0x6, 0x5, 0x6, 0x7, 0xa, 0xa, 0x4, 0x2, 0x5, 0x8,
      0x9, 0x8, 0x7, 0xc, 0x14, 0x14, 0x10, 0xe, 0x14, 0x15, 0xf, 0x9, 0x7,
      0x4, 0x7e, 0x76, 0x64, 0x41, 0x48, 0x7d, 0x6c, 0x3d, 0x67, 0x10, 0x6,
      0x7d, 0x75, 0x7, 0x1d, 0x0, 0x6c, 0x2, 0x7d, 0x78, 0x77, 0x6f, 0x77, 0x1,
      0x0, 0x2, 0x7, 0xa, 0x1c, 0x1c, 0x17, 0x23, 0x2f, 0x41, 0x43, 0x4f, 0x55,
      0x58, 0x7e, 0x2, 0x4c, 0x10, 0x69, 0x2c, 0xd, 0x74, 0x2a, 0x74, 0x63,
      0x29, 0x7c, 0x5e, 0x21, 0x35, 0x46, 0x24, 0x67, 0x35, 0x3c, 0x3c, 0x26,
      0x26, 0x2f, 0x47, 0x64, 0x4, 0x13, 0x18, 0x27, 0x2b, 0x30, 0x1b, 0x7f,
      0x78, 0x72, 0x68, 0x5c, 0x5a, 0x68, 0x7c, 0x3, 0xd, 0x26, 0x41, 0x51,
      0x5a, 0x6a, 0x6c, 0x54, 0x78, 0x9, 0x45, 0x79, 0x1f, 0xb, 0x2e, 0x60,
      0xb, 0x66, 0x7f, 0x68, 0x77, 0x4e, 0x46, 0x4a, 0x3b, 0x12, 0x5b, 0x37,
      0x31, 0x21, 0xb, 0x12, 0x2e, 0x57, 0x7e, 0x19, 0x22, 0x2b, 0x3f, 0x3a,
      0x25, 0xb, 0x79, 0x71, 0x68, 0x61, 0x5c, 0x66, 0x72, 0x6, 0x16, 0x29,
      0x41, 0x5e, 0x6d, 0x66, 0x60, 0x6e, 0x17, 0x48, 0x36, 0x12, 0x17, 0x2f,
      0x63, 0x78, 0x5c, 0x77, 0x6c, 0x75, 0x41, 0x49, 0x4f, 0x3b, 0xb, 0x54,
      0x37, 0};

int
main (int argc, char *argv[])
{
  const int OUTSIZE = 720;
  long output[OUTSIZE];

  long fir_int[36] =
    {0xfffffffe, 0x1, 0x4, 0x3, 0xfffffffe, 0xfffffffc, 0x2, 0x7, 0x0,
        0xfffffff7, 0xfffffffc, 0xc, 0xb, 0xfffffff2, 0xffffffe6, 0xf, 0x59,
        0x7f, 0x59, 0xf, 0xffffffe6, 0xfffffff2, 0xb, 0xc, 0xfffffffc,
        0xfffffff7, 0x0, 0x7, 0x2, 0xfffffffc, 0xfffffffe, 0x3, 0x4, 0x1,
        0xfffffffe, 0};

  /*
   * Two integer values must be supplied
   */
  if (argc != 3)
  {
    return 1;
  }

  fir_filter_int (in_data, output, 10, fir_int, 35, 285);

  return 0;
}
