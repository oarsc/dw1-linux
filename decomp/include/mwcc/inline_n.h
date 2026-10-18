#define __arg0	-1
#define __arg1	-2
#define __arg2	-3
#define __arg3	-4
#define __arg4	-5
#define __arg5	-6
#define __arg6	-7
#define __arg7	-8
#define __arg8	-9
#define __arg9	-10
#define __arg10	-11
#define __arg11	-12
#define __arg12	-13
#define __arg13	-14
#define __arg14	-15
#define __arg15	-16
#define __arg16	-17
#define __arg17	-18
#define __arg18	-19
#define __arg19	-20
#define __arg20	-21
#define __arg21	-22
#define __arg22	-23
#define __arg23	-24
#define __arg24	-25
#define __arg25	-26
#define __arg26	-27
#define __arg27	-28
#define __arg28	-29
#define __arg29	-30
#define __arg30	-31
#define __arg31	-32
/*
 * $PSLibId$
 */
/*
 *	Macro definitions of DMPSX version 3
 *	inline_c.h
 *	Copyright(C) 1996, Sony Computer Entertainment Inc.
 *	All rights reserved.
 */
/*
 * Type 1 functions
 */
#define gte_ldv0( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lwc2 (0, 0, __arg0);\
   __I_lwc2 (1, 4, __arg0);\
   __asm_end();

#define gte_ldv1( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lwc2 (2, 0, __arg0);\
   __I_lwc2 (3, 4, __arg0);\
   __asm_end();

#define gte_ldv2( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lwc2 (4, 0, __arg0);\
   __I_lwc2 (5, 4, __arg0);\
   __asm_end();

#define gte_ldv3( r0, r1, r2 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __evaluate (__arg2, (long)(r2));\
   __asm_start();\
   __I_lwc2 (0, 0, __arg0);\
   __I_lwc2 (1, 4, __arg0);\
   __I_lwc2 (2, 0, __arg1);\
   __I_lwc2 (3, 4, __arg1);\
   __I_lwc2 (4, 0, __arg2);\
   __I_lwc2 (5, 4, __arg2);\
   __asm_end();

#define gte_ldv3c( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lwc2 (0, 0, __arg0);\
   __I_lwc2 (1, 4, __arg0);\
   __I_lwc2 (2, 8, __arg0);\
   __I_lwc2 (3, 12, __arg0);\
   __I_lwc2 (4, 16, __arg0);\
   __I_lwc2 (5, 20, __arg0);\
   __asm_end();

#define gte_ldv3c_vertc( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lwc2 (0, 0, __arg0);\
   __I_lwc2 (1, 4, __arg0);\
   __I_lwc2 (2, 12, __arg0);\
   __I_lwc2 (3, 16, __arg0);\
   __I_lwc2 (4, 24, __arg0);\
   __I_lwc2 (5, 28, __arg0);\
   __asm_end();

#define gte_ldv01( r0, r1 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __asm_start();\
   __I_lwc2 (0, 0, __arg0);\
   __I_lwc2 (1, 4, __arg0);\
   __I_lwc2 (2, 0, __arg1);\
   __I_lwc2 (3, 4, __arg1);\
   __asm_end();

#define gte_ldv01c( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lwc2 (0, 0, __arg0);\
   __I_lwc2 (1, 4, __arg0);\
   __I_lwc2 (2, 8, __arg0);\
   __I_lwc2 (3, 12, __arg0);\
   __asm_end();

#define gte_ldrgb( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lwc2 (6, 0, __arg0);\
   __asm_end();

#define gte_ldrgb3( r0, r1, r2 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __evaluate (__arg2, (long)(r2));\
   __asm_start();\
   __I_lwc2 (20, 0, __arg0);\
   __I_lwc2 (21, 0, __arg1);\
   __I_lwc2 (22, 0, __arg2);\
   __I_lwc2 (6, 0, __arg2);\
   __asm_end();

#define gte_ldrgb3c( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lwc2 (20, 0, __arg0);\
   __I_lwc2 (21, 4, __arg0);\
   __I_lwc2 (22, 8, __arg0);\
   __I_lwc2 (6, 8, __arg0);\
   __asm_end();

#define gte_ldlv0( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lhu (13, 4, __arg0);\
   __I_lhu (12, 0, __arg0);\
   __I_sll (13, 13, 16);\
   __I_or (12, 12, 13);\
   __I_mtc2 (12, 0);\
   __I_lwc2 (1, 8, __arg0);\
   __asm_end();

#define gte_ldlvl( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lwc2 (9, 0, __arg0);\
   __I_lwc2 (10, 4, __arg0);\
   __I_lwc2 (11, 8, __arg0);\
   __asm_end();

#define gte_ldsv( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lhu (12, 0, __arg0);\
   __I_lhu (13, 2, __arg0);\
   __I_lhu (14, 4, __arg0);\
   __I_mtc2 (12, 9);\
   __I_mtc2 (13, 10);\
   __I_mtc2 (14, 11);\
   __asm_end();

#define gte_ldbv( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lbu (12, 0, __arg0);\
   __I_lbu (13, 1, __arg0);\
   __I_mtc2 (12, 9);\
   __I_mtc2 (13, 10);\
   __asm_end();

#define gte_ldcv( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lbu (12, 0, __arg0);\
   __I_lbu (13, 1, __arg0);\
   __I_lbu (14, 2, __arg0);\
   __I_mtc2 (12, 9);\
   __I_mtc2 (13, 10);\
   __I_mtc2 (14, 11);\
   __asm_end();

#define gte_ldclmv( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lhu (12, 0, __arg0);\
   __I_lhu (13, 6, __arg0);\
   __I_lhu (14, 12, __arg0);\
   __I_mtc2 (12, 9);\
   __I_mtc2 (13, 10);\
   __I_mtc2 (14, 11);\
   __asm_end();

#define gte_lddp( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_mtc2 (__arg0, 8);\
   __asm_end();

#define gte_ldsxy0( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_mtc2 (__arg0, 12);\
   __asm_end();

#define gte_ldsxy1( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_mtc2 (__arg0, 13);\
   __asm_end();

#define gte_ldsxy2( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_mtc2 (__arg0, 14);\
   __asm_end();

#define gte_ldsxy3( r0, r1, r2 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __evaluate (__arg2, (long)(r2));\
   __asm_start();\
   __I_mtc2 (__arg0, 12);\
   __I_mtc2 (__arg2, 14);\
   __I_mtc2 (__arg1, 13);\
   __asm_end();

#define gte_ldsxy3c( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lwc2 (12, 0, __arg0);\
   __I_lwc2 (13, 4, __arg0);\
   __I_lwc2 (14, 8, __arg0);\
   __asm_end();

#define gte_ldsz3( r0, r1, r2 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __evaluate (__arg2, (long)(r2));\
   __asm_start();\
   __I_mtc2 (__arg0, 17);\
   __I_mtc2 (__arg1, 18);\
   __I_mtc2 (__arg2, 19);\
   __asm_end();

#define gte_ldsz4( r0, r1, r2, r3 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __evaluate (__arg2, (long)(r2));\
   __evaluate (__arg3, (long)(r3));\
   __asm_start();\
   __I_mtc2 (__arg0, 16);\
   __I_mtc2 (__arg1, 17);\
   __I_mtc2 (__arg2, 18);\
   __I_mtc2 (__arg3, 19);\
   __asm_end();

#define gte_ldopv1( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lw (12, 0, __arg0);\
   __I_lw (13, 4, __arg0);\
   __I_ctc2 (12, 0);\
   __I_lw (14, 8, __arg0);\
   __I_ctc2 (13, 2);\
   __I_ctc2 (14, 4);\
   __asm_end();

#define gte_ldopv2( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lwc2 (11, 8, __arg0);\
   __I_lwc2 (9, 0, __arg0);\
   __I_lwc2 (10, 4, __arg0);\
   __asm_end();

#define gte_ldlzc( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_mtc2 (__arg0, 30);\
   __asm_end();

#define gte_SetRGBcd( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lwc2 (6, 0, __arg0);\
   __asm_end();

#define gte_ldbkdir( r0, r1, r2 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __evaluate (__arg2, (long)(r2));\
   __asm_start();\
   __I_ctc2 (__arg0, 13);\
   __I_ctc2 (__arg1, 14);\
   __I_ctc2 (__arg2, 15);\
   __asm_end();

#define gte_SetBackColor( r0, r1, r2 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __evaluate (__arg2, (long)(r2));\
   __asm_start();\
   __I_sll (12,__arg0, 4);\
   __I_sll (13,__arg1, 4);\
   __I_sll (14,__arg2, 4);\
   __I_ctc2 (12, 13);\
   __I_ctc2 (13, 14);\
   __I_ctc2 (14, 15);\
   __asm_end();

#define gte_ldfcdir( r0, r1, r2 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __evaluate (__arg2, (long)(r2));\
   __asm_start();\
   __I_ctc2 (__arg0, 21);\
   __I_ctc2 (__arg1, 22);\
   __I_ctc2 (__arg2, 23);\
   __asm_end();

#define gte_SetFarColor( r0, r1, r2 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __evaluate (__arg2, (long)(r2));\
   __asm_start();\
   __I_sll (12,__arg0, 4);\
   __I_sll (13,__arg1, 4);\
   __I_sll (14,__arg2, 4);\
   __I_ctc2 (12, 21);\
   __I_ctc2 (13, 22);\
   __I_ctc2 (14, 23);\
   __asm_end();

#define gte_SetGeomOffset( r0, r1 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __asm_start();\
   __I_sll (12,__arg0, 16);\
   __I_sll (13,__arg1, 16);\
   __I_ctc2 (12, 24);\
   __I_ctc2 (13, 25);\
   __asm_end();

#define gte_SetGeomScreen( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_ctc2 (__arg0, 26);\
   __asm_end();

#define gte_ldsvrtrow0( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lw (12, 0, __arg0);\
   __I_lw (13, 4, __arg0);\
   __I_ctc2 (12, 0);\
   __I_ctc2 (13, 1);\
   __asm_end();

#define gte_SetRotMatrix( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lw (12, 0, __arg0);\
   __I_lw (13, 4, __arg0);\
   __I_ctc2 (12, 0);\
   __I_ctc2 (13, 1);\
   __I_lw (12, 8, __arg0);\
   __I_lw (13, 12, __arg0);\
   __I_lw (14, 16, __arg0);\
   __I_ctc2 (12, 2);\
   __I_ctc2 (13, 3);\
   __I_ctc2 (14, 4);\
   __asm_end();

#define gte_ldsvllrow0( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lw (12, 0, __arg0);\
   __I_lw (13, 4, __arg0);\
   __I_ctc2 (12, 8);\
   __I_ctc2 (13, 9);\
   __asm_end();

#define gte_SetLightMatrix( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lw (12, 0, __arg0);\
   __I_lw (13, 4, __arg0);\
   __I_ctc2 (12, 8);\
   __I_ctc2 (13, 9);\
   __I_lw (12, 8, __arg0);\
   __I_lw (13, 12, __arg0);\
   __I_lw (14, 16, __arg0);\
   __I_ctc2 (12, 10);\
   __I_ctc2 (13, 11);\
   __I_ctc2 (14, 12);\
   __asm_end();

#define gte_ldsvlcrow0( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lw (12, 0, __arg0);\
   __I_lw (13, 4, __arg0);\
   __I_ctc2 (12, 16);\
   __I_ctc2 (13, 17);\
   __asm_end();

#define gte_SetColorMatrix( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lw (12, 0, __arg0);\
   __I_lw (13, 4, __arg0);\
   __I_ctc2 (12, 16);\
   __I_ctc2 (13, 17);\
   __I_lw (12, 8, __arg0);\
   __I_lw (13, 12, __arg0);\
   __I_lw (14, 16, __arg0);\
   __I_ctc2 (12, 18);\
   __I_ctc2 (13, 19);\
   __I_ctc2 (14, 20);\
   __asm_end();

#define gte_SetTransMatrix( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lw (12, 20, __arg0);\
   __I_lw (13, 24, __arg0);\
   __I_ctc2 (12, 5);\
   __I_lw (14, 28, __arg0);\
   __I_ctc2 (13, 6);\
   __I_ctc2 (14, 7);\
   __asm_end();

#define gte_ldtr( r0, r1, r2 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __evaluate (__arg2, (long)(r2));\
   __asm_start();\
   __I_ctc2 (__arg0, 5);\
   __I_ctc2 (__arg1, 6);\
   __I_ctc2 (__arg2, 7);\
   __asm_end();

#define gte_SetTransVector( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lw (12, 0, __arg0);\
   __I_lw (13, 4, __arg0);\
   __I_lw (14, 8, __arg0);\
   __I_ctc2 (12, 5);\
   __I_ctc2 (13, 6);\
   __I_ctc2 (14, 7);\
   __asm_end();

#define gte_ld_intpol_uv0( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lbu (12, 0, __arg0);\
   __I_lbu (13, 1, __arg0);\
   __I_ctc2 (12, 21);\
   __I_ctc2 (13, 22);\
   __asm_end();

#define gte_ld_intpol_uv1( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lbu (12, 0, __arg0);\
   __I_lbu (13, 1, __arg0);\
   __I_mtc2 (12, 9);\
   __I_mtc2 (13, 10);\
   __asm_end();

#define gte_ld_intpol_bv0( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lbu (12, 0, __arg0);\
   __I_lbu (13, 1, __arg0);\
   __I_ctc2 (12, 21);\
   __I_ctc2 (13, 22);\
   __asm_end();

#define gte_ld_intpol_bv1( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lbu (12, 0, __arg0);\
   __I_lbu (13, 1, __arg0);\
   __I_mtc2 (12, 9);\
   __I_mtc2 (13, 10);\
   __asm_end();

#define gte_ld_intpol_sv0( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lh (12, 0, __arg0);\
   __I_lh (13, 2, __arg0);\
   __I_lh (14, 4, __arg0);\
   __I_ctc2 (12, 21);\
   __I_ctc2 (13, 22);\
   __I_ctc2 (14, 23);\
   __asm_end();

#define gte_ld_intpol_sv1( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lh (12, 0, __arg0);\
   __I_lh (13, 2, __arg0);\
   __I_lh (14, 4, __arg0);\
   __I_mtc2 (12, 9);\
   __I_mtc2 (13, 10);\
   __I_mtc2 (14, 11);\
   __asm_end();

#define gte_ldfc( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_lw (12, 0, __arg0);\
   __I_lw (13, 4, __arg0);\
   __I_lw (14, 8, __arg0);\
   __I_ctc2 (12, 21);\
   __I_ctc2 (13, 22);\
   __I_ctc2 (14, 23);\
   __asm_end();

/*
 * Type 2 functions
 */
#define gte_rtps()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a180001);\
   __asm_end();

#define gte_rtpt()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a280030);\
   __asm_end();

#define gte_rt()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a480012);\
   __asm_end();

#define gte_rtv0()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a486012);\
   __asm_end();

#define gte_rtv1()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a48e012);\
   __asm_end();

#define gte_rtv2()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a496012);\
   __asm_end();

#define gte_rtir()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a49e012);\
   __asm_end();

#define gte_rtir_sf0()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a41e012);\
   __asm_end();

#define gte_rtv0tr()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a480012);\
   __asm_end();

#define gte_rtv1tr()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a488012);\
   __asm_end();

#define gte_rtv2tr()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a490012);\
   __asm_end();

#define gte_rtirtr()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a498012);\
   __asm_end();

#define gte_rtv0bk()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a482012);\
   __asm_end();

#define gte_rtv1bk()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a48a012);\
   __asm_end();

#define gte_rtv2bk()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a492012);\
   __asm_end();

#define gte_rtirbk()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a49a012);\
   __asm_end();

#define gte_rtv0fc()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a484012);\
   __asm_end();

#define gte_rtv1fc()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a48c012);\
   __asm_end();

#define gte_rtv2fc()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a494012);\
   __asm_end();

#define gte_rtirfc()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a49c012);\
   __asm_end();

#define gte_ll()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4a6412);\
   __asm_end();

#define gte_llv0()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4a6012);\
   __asm_end();

#define gte_llv1()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4ae012);\
   __asm_end();

#define gte_llv2()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4b6012);\
   __asm_end();

#define gte_llir()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4be012);\
   __asm_end();

#define gte_llv0tr()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4a0012);\
   __asm_end();

#define gte_llv1tr()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4a8012);\
   __asm_end();

#define gte_llv2tr()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4b0012);\
   __asm_end();

#define gte_llirtr()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4b8012);\
   __asm_end();

#define gte_llv0bk()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4a2012);\
   __asm_end();

#define gte_llv1bk()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4aa012);\
   __asm_end();

#define gte_llv2bk()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4b2012);\
   __asm_end();

#define gte_llirbk()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4ba012);\
   __asm_end();

#define gte_llv0fc()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4a4012);\
   __asm_end();

#define gte_llv1fc()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4ac012);\
   __asm_end();

#define gte_llv2fc()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4b4012);\
   __asm_end();

#define gte_llirfc()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4bc012);\
   __asm_end();

#define gte_lc()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4da412);\
   __asm_end();

#define gte_lcv0()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4c6012);\
   __asm_end();

#define gte_lcv1()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4ce012);\
   __asm_end();

#define gte_lcv2()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4d6012);\
   __asm_end();

#define gte_lcir()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4de012);\
   __asm_end();

#define gte_lcv0tr()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4c0012);\
   __asm_end();

#define gte_lcv1tr()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4c8012);\
   __asm_end();

#define gte_lcv2tr()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4d0012);\
   __asm_end();

#define gte_lcirtr()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4d8012);\
   __asm_end();

#define gte_lcv0bk()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4c2012);\
   __asm_end();

#define gte_lcv1bk()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4ca012);\
   __asm_end();

#define gte_lcv2bk()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4d2012);\
   __asm_end();

#define gte_lcirbk()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4da012);\
   __asm_end();

#define gte_lcv0fc()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4c4012);\
   __asm_end();

#define gte_lcv1fc()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4cc012);\
   __asm_end();

#define gte_lcv2fc()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4d4012);\
   __asm_end();

#define gte_lcirfc()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a4dc012);\
   __asm_end();

#define gte_dpcl()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a680029);\
   __asm_end();

#define gte_dpcs()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a780010);\
   __asm_end();

#define gte_dpct()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4af8002a);\
   __asm_end();

#define gte_intpl()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4a980011);\
   __asm_end();

#define gte_sqr12()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4aa80428);\
   __asm_end();

#define gte_sqr0()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4aa00428);\
   __asm_end();

#define gte_ncs()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4ac8041e);\
   __asm_end();

#define gte_nct()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4ad80420);\
   __asm_end();

#define gte_ncds()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4ae80413);\
   __asm_end();

#define gte_ncdt()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4af80416);\
   __asm_end();

#define gte_nccs()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4b08041b);\
   __asm_end();

#define gte_ncct()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4b18043f);\
   __asm_end();

#define gte_cdp()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4b280414);\
   __asm_end();

#define gte_cc()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4b38041c);\
   __asm_end();

#define gte_nclip()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4b400006);\
   __asm_end();

#define gte_avsz3()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4b58002d);\
   __asm_end();

#define gte_avsz4()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4b68002e);\
   __asm_end();

#define gte_op12()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4b78000c);\
   __asm_end();

#define gte_op0()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4b70000c);\
   __asm_end();

#define gte_gpf12()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4b98003d);\
   __asm_end();

#define gte_gpf0()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4b90003d);\
   __asm_end();

#define gte_gpl12()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4ba8003e);\
   __asm_end();

#define gte_gpl0()  \
   __asm_start();\
   __I_nop ();\
   __I_nop ();\
   __I_word (0x4ba0003e);\
   __asm_end();

/*
 * Type 3 functions
 */
#define gte_stsxy( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (14, 0, __arg0);\
   __asm_end();

#define gte_stsxy3( r0, r1, r2 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __evaluate (__arg2, (long)(r2));\
   __asm_start();\
   __I_swc2 (12, 0, __arg0);\
   __I_swc2 (13, 0, __arg1);\
   __I_swc2 (14, 0, __arg2);\
   __asm_end();

#define gte_stsxy3c( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (12, 0, __arg0);\
   __I_swc2 (13, 4, __arg0);\
   __I_swc2 (14, 8, __arg0);\
   __asm_end();

#define gte_stsxy2( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (14, 0, __arg0);\
   __asm_end();

#define gte_stsxy1( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (13, 0, __arg0);\
   __asm_end();

#define gte_stsxy0( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (12, 0, __arg0);\
   __asm_end();

#define gte_stsxy01( r0, r1 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __asm_start();\
   __I_swc2 (12, 0, __arg0);\
   __I_swc2 (13, 0, __arg1);\
   __asm_end();

#define gte_stsxy01c( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (12, 0, __arg0);\
   __I_swc2 (13, 4, __arg0);\
   __asm_end();

#define gte_stsxy3_f3( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (12, 8, __arg0);\
   __I_swc2 (13, 12, __arg0);\
   __I_swc2 (14, 16, __arg0);\
   __asm_end();

#define gte_stsxy3_g3( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (12, 8, __arg0);\
   __I_swc2 (13, 16, __arg0);\
   __I_swc2 (14, 24, __arg0);\
   __asm_end();

#define gte_stsxy3_ft3( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (12, 8, __arg0);\
   __I_swc2 (13, 16, __arg0);\
   __I_swc2 (14, 24, __arg0);\
   __asm_end();

#define gte_stsxy3_gt3( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (12, 8, __arg0);\
   __I_swc2 (13, 20, __arg0);\
   __I_swc2 (14, 32, __arg0);\
   __asm_end();

#define gte_stsxy3_f4( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (12, 8, __arg0);\
   __I_swc2 (13, 12, __arg0);\
   __I_swc2 (14, 16, __arg0);\
   __asm_end();

#define gte_stsxy3_g4( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (12, 8, __arg0);\
   __I_swc2 (13, 16, __arg0);\
   __I_swc2 (14, 24, __arg0);\
   __asm_end();

#define gte_stsxy3_ft4( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (12, 8, __arg0);\
   __I_swc2 (13, 16, __arg0);\
   __I_swc2 (14, 24, __arg0);\
   __asm_end();

#define gte_stsxy3_gt4( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (12, 8, __arg0);\
   __I_swc2 (13, 20, __arg0);\
   __I_swc2 (14, 32, __arg0);\
   __asm_end();

#define gte_stdp( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (8, 0, __arg0);\
   __asm_end();

#define gte_stflg( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_cfc2 (12, 31);\
   __I_nop ();\
   __I_sw (12, 0, __arg0);\
   __asm_end();

#define gte_stflg_4( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_cfc2 (12, 31);\
   __I_addi (13, 0, 4);\
   __I_sll (13, 13, 16);\
   __I_and (12, 12, 13);\
   __I_sw (12, 0, __arg0);\
   __asm_end();

#define gte_stsz( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (19, 0, __arg0);\
   __asm_end();

#define gte_stsz3( r0, r1, r2 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __evaluate (__arg2, (long)(r2));\
   __asm_start();\
   __I_swc2 (17, 0, __arg0);\
   __I_swc2 (18, 0, __arg1);\
   __I_swc2 (19, 0, __arg2);\
   __asm_end();

#define gte_stsz4( r0, r1, r2, r3 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __evaluate (__arg2, (long)(r2));\
   __evaluate (__arg3, (long)(r3));\
   __asm_start();\
   __I_swc2 (16, 0, __arg0);\
   __I_swc2 (17, 0, __arg1);\
   __I_swc2 (18, 0, __arg2);\
   __I_swc2 (19, 0, __arg3);\
   __asm_end();

#define gte_stsz3c( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (17, 0, __arg0);\
   __I_swc2 (18, 4, __arg0);\
   __I_swc2 (19, 8, __arg0);\
   __asm_end();

#define gte_stsz4c( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (16, 0, __arg0);\
   __I_swc2 (17, 4, __arg0);\
   __I_swc2 (18, 8, __arg0);\
   __I_swc2 (19, 12, __arg0);\
   __asm_end();

#define gte_stszotz( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_mfc2 (12, 19);\
   __I_nop ();\
   __I_sra (12, 12, 2);\
   __I_sw (12, 0, __arg0);\
   __asm_end();

#define gte_stotz( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (7, 0, __arg0);\
   __asm_end();

#define gte_stopz( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (24, 0, __arg0);\
   __asm_end();

#define gte_stlvl( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (9, 0, __arg0);\
   __I_swc2 (10, 4, __arg0);\
   __I_swc2 (11, 8, __arg0);\
   __asm_end();

#define gte_stlvnl( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (25, 0, __arg0);\
   __I_swc2 (26, 4, __arg0);\
   __I_swc2 (27, 8, __arg0);\
   __asm_end();

#define gte_stlvnl0( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (25, 0, __arg0);\
   __asm_end();

#define gte_stlvnl1( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (26, 0, __arg0);\
   __asm_end();

#define gte_stlvnl2( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (27, 0, __arg0);\
   __asm_end();

#define gte_stsv( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_mfc2 (12, 9);\
   __I_mfc2 (13, 10);\
   __I_mfc2 (14, 11);\
   __I_sh (12, 0, __arg0);\
   __I_sh (13, 2, __arg0);\
   __I_sh (14, 4, __arg0);\
   __asm_end();

#define gte_stclmv( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_mfc2 (12, 9);\
   __I_mfc2 (13, 10);\
   __I_mfc2 (14, 11);\
   __I_sh (12, 0, __arg0);\
   __I_sh (13, 6, __arg0);\
   __I_sh (14, 12, __arg0);\
   __asm_end();

#define gte_stbv( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_mfc2 (12, 9);\
   __I_mfc2 (13, 10);\
   __I_sb (12, 0, __arg0);\
   __I_sb (13, 1, __arg0);\
   __asm_end();

#define gte_stcv( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_mfc2 (12, 9);\
   __I_mfc2 (13, 10);\
   __I_mfc2 (14, 11);\
   __I_sb (12, 0, __arg0);\
   __I_sb (13, 1, __arg0);\
   __I_sb (14, 2, __arg0);\
   __asm_end();

#define gte_strgb( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (22, 0, __arg0);\
   __asm_end();

#define gte_strgb3( r0, r1, r2 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __evaluate (__arg2, (long)(r2));\
   __asm_start();\
   __I_swc2 (20, 0, __arg0);\
   __I_swc2 (21, 0, __arg1);\
   __I_swc2 (22, 0, __arg2);\
   __asm_end();

#define gte_strgb3_g3( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (20, 4, __arg0);\
   __I_swc2 (21, 12, __arg0);\
   __I_swc2 (22, 20, __arg0);\
   __asm_end();

#define gte_strgb3_gt3( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (20, 4, __arg0);\
   __I_swc2 (21, 16, __arg0);\
   __I_swc2 (22, 28, __arg0);\
   __asm_end();

#define gte_strgb3_g4( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (20, 4, __arg0);\
   __I_swc2 (21, 12, __arg0);\
   __I_swc2 (22, 20, __arg0);\
   __asm_end();

#define gte_strgb3_gt4( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (20, 4, __arg0);\
   __I_swc2 (21, 16, __arg0);\
   __I_swc2 (22, 28, __arg0);\
   __asm_end();

#define gte_ReadGeomOffset( r0, r1 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __asm_start();\
   __I_cfc2 (12, 24);\
   __I_cfc2 (13, 25);\
   __I_sra (12, 12, 16);\
   __I_sra (13, 13, 16);\
   __I_sw (12, 0, __arg0);\
   __I_sw (13, 0, __arg1);\
   __asm_end();

#define gte_ReadGeomScreen( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_cfc2 (12, 26);\
   __I_nop ();\
   __I_sw (12, 0, __arg0);\
   __asm_end();

#define gte_ReadRotMatrix( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_cfc2 (12, 0);\
   __I_cfc2 (13, 1);\
   __I_sw (12, 0, __arg0);\
   __I_sw (13, 4, __arg0);\
   __I_cfc2 (12, 2);\
   __I_cfc2 (13, 3);\
   __I_cfc2 (14, 4);\
   __I_sw (12, 8, __arg0);\
   __I_sw (13, 12, __arg0);\
   __I_sw (14, 16, __arg0);\
   __I_cfc2 (12, 5);\
   __I_cfc2 (13, 6);\
   __I_cfc2 (14, 7);\
   __I_sw (12, 20, __arg0);\
   __I_sw (13, 24, __arg0);\
   __I_sw (14, 28, __arg0);\
   __asm_end();

#define gte_sttr( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_cfc2 (12, 5);\
   __I_cfc2 (13, 6);\
   __I_cfc2 (14, 7);\
   __I_sw (12, 0, __arg0);\
   __I_sw (13, 4, __arg0);\
   __I_sw (14, 8, __arg0);\
   __asm_end();

#define gte_ReadLightMatrix( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_cfc2 (12, 8);\
   __I_cfc2 (13, 9);\
   __I_sw (12, 0, __arg0);\
   __I_sw (13, 4, __arg0);\
   __I_cfc2 (12, 10);\
   __I_cfc2 (13, 11);\
   __I_cfc2 (14, 12);\
   __I_sw (12, 8, __arg0);\
   __I_sw (13, 12, __arg0);\
   __I_sw (14, 16, __arg0);\
   __I_cfc2 (12, 13);\
   __I_cfc2 (13, 14);\
   __I_cfc2 (14, 15);\
   __I_sw (12, 20, __arg0);\
   __I_sw (13, 24, __arg0);\
   __I_sw (14, 28, __arg0);\
   __asm_end();

#define gte_ReadColorMatrix( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_cfc2 (12, 16);\
   __I_cfc2 (13, 17);\
   __I_sw (12, 0, __arg0);\
   __I_sw (13, 4, __arg0);\
   __I_cfc2 (12, 18);\
   __I_cfc2 (13, 19);\
   __I_cfc2 (14, 20);\
   __I_sw (12, 8, __arg0);\
   __I_sw (13, 12, __arg0);\
   __I_sw (14, 16, __arg0);\
   __I_cfc2 (12, 21);\
   __I_cfc2 (13, 22);\
   __I_cfc2 (14, 23);\
   __I_sw (12, 20, __arg0);\
   __I_sw (13, 24, __arg0);\
   __I_sw (14, 28, __arg0);\
   __asm_end();

#define gte_stlzc( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_swc2 (31, 0, __arg0);\
   __asm_end();

#define gte_stfc( r0 )  \
   __evaluate (__arg0, (long)(r0));\
   __asm_start();\
   __I_cfc2 (12, 21);\
   __I_cfc2 (13, 22);\
   __I_cfc2 (14, 23);\
   __I_sw (12, 0, __arg0);\
   __I_sw (13, 4, __arg0);\
   __I_sw (14, 8, __arg0);\
   __asm_end();

#define gte_mvlvtr()  \
   __asm_start();\
   __I_mfc2 (12, 25);\
   __I_mfc2 (13, 26);\
   __I_mfc2 (14, 27);\
   __I_ctc2 (12, 5);\
   __I_ctc2 (13, 6);\
   __I_ctc2 (14, 7);\
   __asm_end();

#define gte_nop()  \
   __asm_start();\
   __asm_end();

#define gte_subdvl( r0, r1, r2 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __evaluate (__arg2, (long)(r2));\
   __asm_start();\
   __I_lw (12, 0, __arg0);\
   __I_lw (13, 0, __arg1);\
   __I_mtc2 (12, 9);\
   __I_mtc2 (13, 10);\
   __I_sra (12, 12, 16);\
   __I_sra (13, 13, 16);\
   __I_subu (15, 12, 13);\
   __I_mfc2 (12, 9);\
   __I_mfc2 (13, 10);\
   __I_sw (15, 4, __arg2);\
   __I_subu (12, 12, 13);\
   __I_sw (12, 0, __arg2);\
   __asm_end();

#define gte_subdvd( r0, r1, r2 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __evaluate (__arg2, (long)(r2));\
   __asm_start();\
   __I_lw (12, 0, __arg0);\
   __I_lw (13, 0, __arg1);\
   __I_mtc2 (12, 9);\
   __I_mtc2 (13, 10);\
   __I_sra (12, 12, 16);\
   __I_sra (13, 13, 16);\
   __I_subu (15, 12, 13);\
   __I_mfc2 (12, 9);\
   __I_mfc2 (13, 10);\
   __I_sh (15, 2, __arg2);\
   __I_subu (12, 12, 13);\
   __I_sh (12, 0, __arg2);\
   __asm_end();

#define gte_adddvl( r0, r1, r2 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __evaluate (__arg2, (long)(r2));\
   __asm_start();\
   __I_lw (12, 0, __arg0);\
   __I_lw (13, 0, __arg1);\
   __I_mtc2 (12, 9);\
   __I_mtc2 (13, 10);\
   __I_sra (12, 12, 16);\
   __I_sra (13, 13, 16);\
   __I_addu (15, 12, 13);\
   __I_mfc2 (12, 9);\
   __I_mfc2 (13, 10);\
   __I_sw (15, 4, __arg2);\
   __I_addu (12, 12, 13);\
   __I_sw (12, 0, __arg2);\
   __asm_end();

#define gte_adddvd( r0, r1, r2 )  \
   __evaluate (__arg0, (long)(r0));\
   __evaluate (__arg1, (long)(r1));\
   __evaluate (__arg2, (long)(r2));\
   __asm_start();\
   __I_lw (12, 0, __arg0);\
   __I_lw (13, 0, __arg1);\
   __I_mtc2 (12, 9);\
   __I_mtc2 (13, 10);\
   __I_sra (12, 12, 16);\
   __I_sra (13, 13, 16);\
   __I_addu (15, 12, 13);\
   __I_mfc2 (12, 9);\
   __I_mfc2 (13, 10);\
   __I_sh (15, 2, __arg2);\
   __I_addu (12, 12, 13);\
   __I_sh (12, 0, __arg2);\
   __asm_end();

#define gte_FlipRotMatrixX()  \
   __asm_start();\
   __I_cfc2 (12, 0);\
   __I_cfc2 (13, 1);\
   __I_sll (14, 12, 16);\
   __I_sra (14, 14, 16);\
   __I_subu (14, 0, 14);\
   __I_sra (15, 12, 16);\
   __I_subu (15, 0, 15);\
   __I_sll (15, 15, 16);\
   __I_sll (14, 14, 16);\
   __I_srl (14, 14, 16);\
   __I_or (14, 14, 15);\
   __I_ctc2 (14, 0);\
   __I_sll (14, 13, 16);\
   __I_sra (14, 14, 16);\
   __I_subu (14, 0, 14);\
   __I_sra (15, 13, 16);\
   __I_sll (15, 15, 16);\
   __I_sll (14, 14, 16);\
   __I_srl (14, 14, 16);\
   __I_or (14, 14, 15);\
   __I_ctc2 (14, 1);\
   __asm_end();

#define gte_FlipTRX()  \
   __asm_start();\
   __I_cfc2 (12, 5);\
   __I_nop ();\
   __I_subu (12, 0, 12);\
   __I_ctc2 (12, 5);\
   __asm_end();


