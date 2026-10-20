/*
 * Native replacement for Psy-Q's <setjmp.h> (whose jmp_buf holds the 12 MIPS registers).
 *
 * The script interpreter (src/main/script_interp.c) uses setjmp/longjmp as a non-local exit;
 * the host's _setjmp/_longjmp do the same without touching the signal mask, which the PS1
 * doesn't have. The buffer is the host's: x86_64 glibc's jmp_buf is a struct of 200 bytes, but
 * _setjmp (unlike setjmp) only stores the 64-byte jump buffer and a 4-byte "mask saved" flag,
 * so 48 ints (192 bytes) covers it — the same figure the old macOS build used.
 */
#ifndef DW1_NATIVE_SETJMP_H
#define DW1_NATIVE_SETJMP_H

#define DW1_HOST_JBLEN 48
typedef int jmp_buf[DW1_HOST_JBLEN];

int _setjmp(jmp_buf) __attribute__((returns_twice));
void _longjmp(jmp_buf, int) __attribute__((noreturn));

#define setjmp(env) _setjmp(env)
#define longjmp(env, value) _longjmp(env, value)

#endif
