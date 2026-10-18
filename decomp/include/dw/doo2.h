#ifndef DW_DOO2_H
#define DW_DOO2_H

#include <libgpu.h>
#include <libgs.h>
#include <libgte.h>

#include <dw/types.h>

typedef struct {
	int8_t icon[4];
} Doo2EggIcons;

typedef struct {
	int16_t vx;
	int16_t vy;
	int16_t vz;
} Doo2ModelVertex;

/* An address held as an integer: 32 bits on the PS1, pointer width natively. */
#ifdef DW1_NATIVE
typedef intptr_t Doo2Addr;
typedef uintptr_t Doo2UAddr;
#else
typedef int32_t Doo2Addr;
typedef u_long Doo2UAddr;
#endif

typedef struct {
	int16_t timer;
	int16_t primitiveCount;
	Doo2Addr centers;
	Doo2Addr vertices;
	Doo2Addr primitives;
	int16_t centerCount;
	uint8_t pad12[2];
} Doo2ShardSet;

extern RECT MAIN_D_80134B90;
extern RECT MAIN_D_80134B98;
extern Doo2EggIcons EGG_ICONS;
extern RECT MAIN_D_80134BA4;
extern Doo2ShardSet DOO2_SHARD_SETS[6];
extern u_long DOO2_D_80071B5C[33];
extern u_long DOO2_D_80071BE0[193];
extern u_long DOO2_D_80071EE4[9730];
extern Doo2Addr MAIN_D_80135310;
extern uint8_t *MAIN_D_80135314;
extern Doo2ModelVertex *MAIN_D_80135318;
extern int16_t MAIN_D_8013531C[3];

int32_t DOO2_buildShardSet(VECTOR *offset, Doo2UAddr modelList, int32_t modelIndex);
void DOO2_fadeClut(int16_t *srcClut, void *entity, int16_t *dstClut, int32_t startFrame, int32_t endFrame, int32_t frame);
void DOO2_openEggBox(void);
void DOO2_releaseAllShardSets(void);
void DOO2_renderSparkStreak(int32_t *pos, SVECTOR *rot);
void DOO2_renderWireframeModel(GsDOBJ2 *obj, int32_t wireThreshold);
void DOO2_resetShardSets(Doo2Addr size);
void DOO2_saveClutTile(Doo2UAddr pixels, int32_t tile);
void DOO2_saveModelClut(Doo2UAddr pixels);
int32_t DOO2_tickEggInput(void);

#endif
