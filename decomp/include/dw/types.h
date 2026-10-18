#ifndef DW_TYPES_H
#define DW_TYPES_H

#ifdef __MWERKS__

#ifndef NULL
#define NULL 0
#endif

typedef char int8_t;
typedef short int16_t;
typedef int int32_t;

typedef unsigned char uint8_t;
typedef unsigned short uint16_t;
typedef unsigned int uint32_t;

typedef int intptr_t;
typedef unsigned int uintptr_t;

#else

#include <stddef.h>
#include <stdint.h>

#endif

/*
 * A fixed PS1 RAM address, as a pointer of the given type. The native build (dw1-silicon)
 * defines this first, to point into its stand-in for PS1 RAM; everywhere else it's a cast.
 */
#ifndef DW1_PS1_ADDR
#define DW1_PS1_ADDR(type, addr) ((type)(addr))
#endif

/*
 * An address field of a TMD object record (vertop, nortop, primtop) after GsMapModelingData.
 * The native build stores these as 32-bit encoded pointers and defines this to decode them.
 */
#ifndef DW1_TMD_ADDR
#define DW1_TMD_ADDR(field) (field)
#endif

/*
 * An array index the game computes as (uint32_t)(n) where n can be negative: with 32-bit
 * pointers the address wraps and reads n elements before the base. With 64-bit pointers that
 * takes a signed index.
 */
/*
 * A struct's size the game C spells as a literal (a stride, an array's byte size). Structs that
 * hold pointers are bigger natively, so the native build takes sizeof; everywhere else it's the
 * literal, so the PS1 builds don't change.
 */
#ifdef DW1_NATIVE
#define DW1_SIZEOF(expr, ps1) ((int32_t)sizeof(expr))
#else
#define DW1_SIZEOF(expr, ps1) (ps1)
#endif

#ifdef DW1_NATIVE
#define DW1_WRAP_INDEX(n) ((int32_t)(n))
#else
#define DW1_WRAP_INDEX(n) ((uint32_t)(n))
#endif

#endif
