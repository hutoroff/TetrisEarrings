#include "work.h"
//----------------------- variables from other files ---------------------------------//
// ADC handle initialized in main.c
extern ADC_HandleTypeDef hadc;

//----------------------- variables from this file -----------------------------------//
// Mode switching variables
uint8_t current_mode = 0;   // 0 - Ping-Pong, 1 - Tetris, 2 - Snake ... 8 - Rain
uint32_t mode_timer = 0;    // Mode switch timer (45 s)
uint32_t action_timer = 0;  // Frame timer (FPS)

// Smart button and ADC variables
uint32_t btn_press_time = 0;
uint8_t btn_prev_state = 0;
uint8_t auto_mode_switch = 1; // 1 - auto-switching enabled, 0 - stopped
uint32_t adc_timer = 0;

//------------------------------ functions -------------------------------------------//
void doWork (void){
	Balls_Init();                    // Start with the first mode (Ping-Pong)
    mode_timer = HAL_GetTick();
    action_timer = HAL_GetTick();

    // Wait for debounce and power-up
    if (HAL_GPIO_ReadPin(ReadKey_GPIO_Port, ReadKey_Pin)){
        HAL_Delay(200);
    }
    if (HAL_GPIO_ReadPin(ReadKey_GPIO_Port, ReadKey_Pin)) {
        HAL_GPIO_WritePin(PowerOn_GPIO_Port, PowerOn_Pin, GPIO_PIN_SET);
        DrawSmiley();
        UpdateMatrix();
    }
    // Wait for the user to release the button after power-on
    while (HAL_GPIO_ReadPin(ReadKey_GPIO_Port, ReadKey_Pin));
    HAL_Delay(200);
}

void Work (void){
    uint32_t current_time = HAL_GetTick();

    // ================= 1. SMART BUTTON LOGIC =================
    uint8_t btn_state = HAL_GPIO_ReadPin(ReadKey_GPIO_Port, ReadKey_Pin);

    // Button just pressed
    if (btn_state == GPIO_PIN_SET && btn_prev_state == GPIO_PIN_RESET) {
        btn_press_time = current_time;
    }
    // Button held
    else if (btn_state == GPIO_PIN_SET && btn_prev_state == GPIO_PIN_SET) {
        if (current_time - btn_press_time > 1000) { // Long press (1 second) - POWER OFF
            ShutdownAnim();
            HAL_GPIO_WritePin(PowerOn_GPIO_Port, PowerOn_Pin, GPIO_PIN_RESET);
            while(1); // Wait for the board to lose power
        }
    }
    // Button released
    else if (btn_state == GPIO_PIN_RESET && btn_prev_state == GPIO_PIN_SET) {
        if (current_time - btn_press_time > 50 && current_time - btn_press_time <= 1000) {
            // Short press (50 to 1000 ms) - NEXT MODE
            ModeTransition();
            current_mode++;
            if (current_mode > MODE_STEP) current_mode = 0; // <-- Now cycles up to 8!
            if (current_mode == 0) Balls_Init();    // Ping-Pong init
    		if (current_mode == 1) Tetris_Init();
    		if (current_mode == 2) Snake_Init();
    		if (current_mode == 5) Matrix_Init();   // Fire and Heart need no init
    		if (current_mode == 6) Stars_Init();    // Stars init
    		if (current_mode == 8) Rain_Init();     // <-- Rain init
            auto_mode_switch = 0; // User switched mode manually, disable auto-switching!
        }
    }
    btn_prev_state = btn_state; // Remember button state for the next loop


    // ================= 2. ADC LOGIC (polled every 500 ms) =================
    if (current_time - adc_timer >= 500) {
        adc_timer = current_time;

        HAL_ADC_Start(&hadc); // Start conversion
        // Wait for conversion to finish (5 ms max)
        if (HAL_ADC_PollForConversion(&hadc, 5) == HAL_OK) {
            uint16_t adc_val = HAL_ADC_GetValue(&hadc); // Read the result
            if (adc_val < 2700) {
                // Voltage dropped - save the battery, power off!
                ShutdownAnim();
                HAL_GPIO_WritePin(PowerOn_GPIO_Port, PowerOn_Pin, GPIO_PIN_RESET);
                while(1);
            }
        }
    }


    // ================= 3. AUTOMATIC MODE SWITCHING =================
    // Only fires if auto-switching is enabled (auto_mode_switch == 1)
    if (auto_mode_switch && (current_time - mode_timer >= 45000)) {
        ModeTransition();
        current_mode++;
        if (current_mode > MODE_STEP) current_mode = 0; // 9 modes total (0-8)

        if (current_mode == 0) Balls_Init();    // Ping-Pong init
		if (current_mode == 1) Tetris_Init();
		if (current_mode == 2) Snake_Init();
		if (current_mode == 5) Matrix_Init();   // Fire and Heart need no init
		if (current_mode == 6) Stars_Init();    // Stars init
		if (current_mode == 8) Rain_Init();     // <-- Rain init
        mode_timer = HAL_GetTick();
    }


    // ================= 4. GAME RENDERING =================
	if (current_mode == 0) {                              // MODE 0: Ping-Pong
	    if (current_time - action_timer >= 30) {          // 30 ms (high FPS for smoothness)
	        Balls_Tick();
	        action_timer = current_time;
	    }
	}
	else if (current_mode == 1) {                         // 1: Tetris
		if (current_time - action_timer >= 50) {
			GameTick();
			action_timer = current_time;
		}
	}
	else if (current_mode == 2) {                         // 2: Snake
		if (current_time - action_timer >= 220) {
			Snake_Tick();
			action_timer = current_time;
		}
	}
	else if (current_mode == 3) {                         // 3: Heart
		if (current_time - action_timer >= 30) {
			Heart_Tick();
			action_timer = current_time;
		}
	}
	else if (current_mode == 4) {                         // 4: Fire
		if (current_time - action_timer >= 60) {          // 60 ms - optimal burn speed
			Fire_Tick();
			action_timer = current_time;
		}
	}
	else if (current_mode == 5) {                         // 5: Matrix
		if (current_time - action_timer >= 80) {          // 80 ms - so the tails have time to fade
			Matrix_Tick();
			action_timer = current_time;
		}
	}
	else if (current_mode == 6) {                         // MODE 6: Starry sky
	    if (current_time - action_timer >= 40) {          // 40 ms - optimal twinkle speed
	        Stars_Tick();
	        action_timer = current_time;
	    }
	}
	else if (current_mode == 7) {                         // MODE 7: Rainbow
		if (current_time - action_timer >= 30) {      // 30 ms - smooth color flow
			Rainbow_Tick();
			action_timer = current_time;
		}
	}
	else if (current_mode == 8) {                         // MODE 8: Rain
	    if (current_time - action_timer >= 30) {          // 30 ms for smooth physics
	        Rain_Tick();
	        action_timer = current_time;
	    }
	}
}
//------------------------------ notes -------------------------------------------------//


