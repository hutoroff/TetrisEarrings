#ifndef INC_SAPORTANDDATA_H_
#define INC_SAPORTANDDATA_H_

#ifdef __cplusplus
extern "C" {
#endif

//----------------------- includes -------------------------------------------//
#include "stm32f0xx_hal.h"
#include "stdint.h"
#include <stdlib.h> // For rand()

//----------------------- defines --------------------------------------------//
#define MAX_X 6
#define MAX_Y 10
#define SNAKE_MAX_LEN 60

#define Led1_Pin GPIO_PIN_3
#define Led1_GPIO_Port GPIOA
#define Led2_Pin GPIO_PIN_4
#define Led2_GPIO_Port GPIOA
#define PowerOn_Pin GPIO_PIN_6
#define PowerOn_GPIO_Port GPIOA
#define ReadKey_Pin GPIO_PIN_7
#define ReadKey_GPIO_Port GPIOA

//----------------------- struct declarations --------------------------------//
typedef struct {
    int8_t x;
    int8_t y;
} Point;

typedef struct {
    int16_t x;   // X position (in hundredths)
    int16_t y;   // Y position (in hundredths)
    int16_t dx;  // X velocity
    int16_t dy;  // Y velocity
    uint8_t r, g, b; // Ball color
} Ball;

// 2. Create a shared memory buffer for ALL modes
typedef union {
    // Tetris memory
    struct {
        uint8_t board[MAX_Y][MAX_X];
        int8_t id;
        int8_t rot;
        int8_t x;
        int8_t y;
        int8_t tx;
        int8_t trot;
    } t;

    // Snake memory
    struct {
        Point body[SNAKE_MAX_LEN];
        uint8_t len;
        Point foods;
        int8_t dx;
        int8_t dy;
    } s;

    // Fire memory
    struct {
        uint8_t heat[MAX_Y][MAX_X];
    } f;

    // Matrix memory
    struct {
        uint8_t grid[MAX_Y][MAX_X];
        int8_t heads[MAX_X];
    } m;
    struct {
		uint8_t brightness[MAX_Y][MAX_X];
		uint8_t state[MAX_Y][MAX_X]; // 0 - off, 1,3,5 - brightening, 2,4,6 - fading
	} st;
	struct {                         // Ping-Pong memory (only 33 bytes!)
		Ball balls[3];
	} p;
	struct {                // Rain memory (104 bytes)
		struct {
			int8_t x;       // Column (0-5)
			int16_t y;      // Height in sub-pixels
			int16_t speed;  // Fall speed
			uint8_t active; // Whether the drop exists
		} drops[4];         // Up to 4 falling drops at once

		struct {
			int16_t x;      // X position (sub-pixels)
			int16_t y;      // Y position (sub-pixels)
			int16_t dx;     // X flight vector
			int16_t dy;     // Y flight vector (reduced by gravity)
			uint8_t life;   // Splash brightness / life
			uint8_t active; // Whether the splash exists
		} splashes[8];      // Up to 8 splashes
	} r;
} AppState;

extern AppState state;
//----------------------- function declarations ------------------------------//

//------------------------------ notes -----------------------------------------------//


#ifdef __cplusplus
}
#endif

#endif /* INC_SAPORTANDDATA_H_ */
