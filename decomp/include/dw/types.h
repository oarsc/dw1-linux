#ifndef DW_TYPES_H
#define DW_TYPES_H

/* DW1_PLUS additions rely on the native runtime, so enabling them also selects its C branches. */
#if defined(DW1_PLUS) && !defined(DW1_NATIVE)
#define DW1_NATIVE 1
#endif

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

/*
 * A signed 32-bit division of the game C. The R3000A's DIV doesn't trap: with a zero divisor LO
 * comes out as -1 for a non-negative dividend and 1 for a negative one, and INT32_MIN / -1 wraps
 * to INT32_MIN, all of which the game's callers rely on (a script's zero step or speed, for
 * instance). The host's idiv raises SIGFPE on both instead, so the divisions a script or a data
 * value can drive to zero go through this; on the PS1 it's the plain `/`.
 */
#ifdef DW1_NATIVE
static inline int32_t dw1_div(int32_t dividend, int32_t divisor)
{
	if (divisor == 0) {
		return (dividend >= 0) ? -1 : 1;
	}
	if (divisor == -1) {
		return (int32_t)(0u - (uint32_t)dividend);
	}
	return dividend / divisor;
}
#define DW1_DIV(a, b) dw1_div((a), (b))
#else
#define DW1_DIV(a, b) ((a) / (b))
#endif

#endif
