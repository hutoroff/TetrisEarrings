#include "ledMatrix.h"
//----------------------- variables from other files ---------------------------------//
extern TIM_HandleTypeDef htim1;
extern DMA_HandleTypeDef hdma_tim1_ch2;
//----------------------- variables from this file -----------------------------------//
uint16_t pwmData[WS2812_BUFFER_SIZE];          // Timer DMA buffer (our PWM values)
//------------------------------ functions -------------------------------------------//

void HAL_TIM_PWM_PulseFinishedCallback(TIM_HandleTypeDef *htim) {
    if (htim->Instance == TIM1) {
        HAL_TIM_PWM_Stop_DMA(&htim1, TIM_CHANNEL_2);
    }
}

uint16_t GetLEDIndex(uint8_t x, uint8_t y) {
    if (y % 2 == 0) {                           // Even rows (0, 2, 4... from the bottom) run right to left
        return (y * MAX_X) + (MAX_X - 1 - x);
    }
    else {                                      // Odd rows (1, 3, 5... from the bottom) run left to right
        return (y * MAX_X) + x;
    }
}


void SetPixel(uint8_t x, uint8_t y, uint8_t r, uint8_t g, uint8_t b) {        // Now we write bits directly into the DMA buffer!
    if(x >= MAX_X || y >= MAX_Y) return;
    uint16_t led_idx = GetLEDIndex(x, y);
    uint32_t color = (g << 16) | (r << 8) | b;
    for (int bit = 23; bit >= 0; bit--) {                                     // Fill 24 bits for the current LED
        if (color & (1 << bit)) {
            pwmData[led_idx * 24 + (23 - bit)] = 38;                          // Logical "1" (~64% PWM)
        } else {
            pwmData[led_idx * 24 + (23 - bit)] = 19;                          // Logical "0" (~32% PWM)
        }
    }
}


void UpdateMatrix(void) {                                                     // Send the finished buffer to the matrix
    for (uint16_t i = NUM_LEDS * 24; i < WS2812_BUFFER_SIZE; i++) {           // Make sure the end of the array stays zero for the RESET signal
        pwmData[i] = 0;
    }
    HAL_TIM_PWM_Start_DMA(&htim1, TIM_CHANNEL_2, (uint32_t*)pwmData, WS2812_BUFFER_SIZE);
}

void ClearScreen(void) {                                                     // Clear the screen (turn off all LEDs)
    for (uint8_t y = 0; y < MAX_Y; y++) {
        for (uint8_t x = 0; x < MAX_X; x++) {
            SetPixel(x, y, 0, 0, 0);
        }
    }
}

//------------------------------ notes -------------------------------------------------//

