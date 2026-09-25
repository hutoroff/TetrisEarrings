#include "effects.h"
//----------------------- variables from other files ---------------------------------//

//----------------------- variables from this file -----------------------------------//
int heart_brightness = 5;   // Heart variables
int heart_fade_step = 2;

//------------------------------ functions -------------------------------------------//
void DrawSmiley(void) {                                                 // Draw a test smiley
    ClearScreen();

    // Draw the eyes (green)
    // X coordinates (0 to 5), Y (0 to 9, where 0 is the bottom)

    // Left eye
    SetPixel(1, 7, 0, 20, 0);
    SetPixel(1, 6, 0, 20, 0);


    // Right eye
    SetPixel(4, 7, 0, 20, 0);
    SetPixel(4, 6, 0, 20, 0);

    // Draw the smile (red)
    SetPixel(0, 4, 20, 0, 0); // Left edge of the smile
    SetPixel(1, 3, 20, 0, 0);
    SetPixel(2, 2, 20, 0, 0); // Center of the smile
    SetPixel(3, 2, 20, 0, 0); // Center of the smile
    SetPixel(4, 3, 20, 0, 0);
    SetPixel(5, 4, 20, 0, 0); // Right edge of the smile
}

// Draw the heart at the given brightness (0 to 255)
void DrawHeart(uint8_t brightness) {
    ClearScreen(); // Clear the buffer

    // Set the color (pure red).
    // For pink, add a little blue: b = brightness / 3;
    uint8_t r = brightness;
    uint8_t g = 0;
    uint8_t b = 0;

    // Draw the top lobes (arcs) of the heart
    SetPixel(1, 7, r, g, b);
    SetPixel(4, 7, r, g, b);

    // Upper wide part
    SetPixel(0, 6, r, g, b);
    SetPixel(1, 6, r, g, b);
    SetPixel(2, 6, r, g, b);
    SetPixel(3, 6, r, g, b);
    SetPixel(4, 6, r, g, b);
    SetPixel(5, 6, r, g, b);

    // Middle wide part
    SetPixel(0, 5, r, g, b);
    SetPixel(1, 5, r, g, b);
    SetPixel(2, 5, r, g, b);
    SetPixel(3, 5, r, g, b);
    SetPixel(4, 5, r, g, b);
    SetPixel(5, 5, r, g, b);

    // Narrowing toward the bottom
    SetPixel(1, 4, r, g, b);
    SetPixel(2, 4, r, g, b);
    SetPixel(3, 4, r, g, b);
    SetPixel(4, 4, r, g, b);

    // Very bottom (the tip)
    SetPixel(2, 3, r, g, b);
    SetPixel(3, 3, r, g, b);
}

// --- HEART TICK ---
void Heart_Tick(void) {
    DrawHeart(heart_brightness);
    UpdateMatrix();

    heart_brightness += heart_fade_step;
    if (heart_brightness >= 60) {
        heart_fade_step = -2;
    } else if (heart_brightness <= 5) {
        heart_fade_step = 2;
    }
}

// --- TRANSITION ANIMATION (CURTAIN) ---
void ModeTransition(void) {
    // Smoothly wipe the screen from top to bottom
    for (int y = MAX_Y - 1; y >= 0; y--) {
        for (int x = 0; x < MAX_X; x++) {
            SetPixel(x, y, 0, 0, 0);
        }
        UpdateMatrix();
        HAL_Delay(40); // Delay for a smooth curtain
    }
    HAL_Delay(300); // Pause in full darkness before the new mode
}

// --- POWER-OFF ANIMATION ("COLLAPSE", LIKE OLD CRT TVs) ---
// The screen shrinks vertically into a thin line, then horizontally into a bright
// dot in the center, which flashes and fades out. Called once before
// the matrix is finally turned off and power is cut.
void ShutdownAnim(void) {
    const uint8_t r = 18, g = 26, b = 18; // Cool white-green glow, like a CRT phosphor

    // 1. Collapse the screen vertically to the two center rows (4 and 5)
    for (int8_t h = MAX_Y / 2 - 1; h >= 0; h--) {
        ClearScreen();
        for (int8_t y = 0; y < MAX_Y; y++) {
            int8_t dist = (y <= 4) ? (4 - y) : (y - 5);
            if (dist <= h) {
                for (int8_t x = 0; x < MAX_X; x++) SetPixel(x, y, r, g, b);
            }
        }
        UpdateMatrix();
        HAL_Delay(35);
    }

    // 2. Shrink the resulting line horizontally to the center (columns 2 and 3)
    for (int8_t w = MAX_X / 2 - 1; w >= 0; w--) {
        ClearScreen();
        for (int8_t x = 0; x < MAX_X; x++) {
            int8_t dist = (x <= 2) ? (2 - x) : (x - 3);
            if (dist <= w) {
                SetPixel(x, 4, r, g, b);
                SetPixel(x, 5, r, g, b);
            }
        }
        UpdateMatrix();
        HAL_Delay(35);
    }

    // 3. A short bright flash of the resulting dot...
    SetPixel(2, 4, 45, 65, 45); SetPixel(3, 4, 45, 65, 45);
    SetPixel(2, 5, 45, 65, 45); SetPixel(3, 5, 45, 65, 45);
    UpdateMatrix();
    HAL_Delay(60);

    // 4. ...and a smooth fade of the dot to full darkness
    for (uint8_t fade = 5; fade > 0; fade--) {
        uint8_t fr = (r * fade) / 5, fg = (g * fade) / 5, fb = (b * fade) / 5;
        SetPixel(2, 4, fr, fg, fb); SetPixel(3, 4, fr, fg, fb);
        SetPixel(2, 5, fr, fg, fb); SetPixel(3, 5, fr, fg, fb);
        UpdateMatrix();
        HAL_Delay(40);
    }

    ClearScreen();
    UpdateMatrix();
}

// ================= MODE: FIRE (dynamic, with detaching flames) =================
void Fire_Tick(void) {
    // 1. Cooling and upward movement (read top to bottom)
    for (int y = MAX_Y - 1; y >= 1; y--) {
        for (int x = 0; x < MAX_X; x++) {
            int from_x = x;

            // Wiggle left/right only with 25% probability
            if (rand() % 4 == 0) {
                from_x = x + (rand() % 3) - 1;
                if (from_x < 0) from_x = 0;
                if (from_x >= MAX_X) from_x = MAX_X - 1;
            }

            int heat = heat_map[y - 1][from_x];

            // Progressive cooling
            int cooling = rand() % 4;
            cooling += y;

            // Icy ceiling
            if (y >= MAX_Y - 2) {
                cooling += 20;
            }

            if (heat > cooling) {
                heat_map[y][x] = heat - cooling;
            } else {
                heat_map[y][x] = 0;
            }
        }
    }

    // 2. AGGRESSIVE cooling of the bottom (so flames detach)
    for (int x = 0; x < MAX_X; x++) {
        // Cool by a random 10 to 20 per frame (used to be just 5)
        int bottom_cooling = 10 + (rand() % 10);
        if (heat_map[0][x] > bottom_cooling) {
            heat_map[0][x] -= bottom_cooling;
        } else {
            heat_map[0][x] = 0;
        }
    }

    // 3. Ragged spark generation
    // Give a 40% chance that the frame is "empty".
    // That's exactly when the flames detach from the ground and fly up!
    if (rand() % 100 < 60) {
        int sparks_count = 1 + (rand() % 2); // 1 or 2 narrow hot spots
        for (int i = 0; i < sparks_count; i++) {
            int spark_x = rand() % MAX_X;
            // Make the spark a bit brighter (60-89) so it flies high before dying out
            heat_map[0][spark_x] = 60 + (rand() % 30);
        }
    }

    // 4. Render to colors
    ClearScreen();
    for (int y = 0; y < MAX_Y; y++) {
        for (int x = 0; x < MAX_X; x++) {
            uint8_t h = heat_map[y][x];
            if (h > 0) {
                uint8_t r = h;
                // Yellow only in the hottest spots near the base (h > 40)
                uint8_t g = (h > 40) ? (h - 40) : 0;
                uint8_t b = 0;

                SetPixel(x, y, r, g, b);
            }
        }
    }
    UpdateMatrix();
}

// ================= MODE: MATRIX =================
void Matrix_Init(void) {
    for(int x = 0; x < MAX_X; x++) {
        m_heads[x] = -1; // -1 means no falling drop in this column yet
        for(int y = 0; y < MAX_Y; y++) m_grid[y][x] = 0;
    }
}

// ================= MODE: MATRIX (green only) =================
void Matrix_Tick(void) {
    // 1. Smooth fading of old trails
    for (int y = 0; y < MAX_Y; y++) {
        for (int x = 0; x < MAX_X; x++) {
            if (m_grid[y][x] >= 6) m_grid[y][x] -= 6; // Tail fade speed
            else m_grid[y][x] = 0;
        }
    }

    // 2. Move drops down
    for (int x = 0; x < MAX_X; x++) {
        if (m_heads[x] >= 0) {
            m_grid[m_heads[x]][x] = 60; // Bright green head
            m_heads[x]--;               // Drop falls lower
        } else {
            // Chance of a new drop appearing at the top
            if (rand() % 12 == 0) {
                m_heads[x] = MAX_Y - 1;
            }
        }
    }

    // 3. Render in PURE green
    ClearScreen();
    for (int y = 0; y < MAX_Y; y++) {
        for (int x = 0; x < MAX_X; x++) {
            uint8_t val = m_grid[y][x];
            if (val > 0) {
                // No red or blue mixed in, only pure green brightness
                SetPixel(x, y, 0, val, 0);
            }
        }
    }
    UpdateMatrix();
}

// ================= MODE: STARRY SKY =================
void Stars_Init(void) {
    for (int y = 0; y < MAX_Y; y++) {
        for (int x = 0; x < MAX_X; x++) {
            st_bright[y][x] = 0;
            st_state[y][x] = 0;
        }
    }
}

void Stars_Tick(void) {
    for (int y = 0; y < MAX_Y; y++) {
        for (int x = 0; x < MAX_X; x++) {

            // If the cell is empty (no star)
            if (st_state[y][x] == 0) {
                // Spawn chance cut almost 10x (0.2%) to keep stars sparse
                if (rand() % 1000 < 4) {
                    // Pick a hue: 1 (red), 2 (blue), 3 (purple)
                    st_state[y][x] = 1 + (rand() % 3);

                    // SHARP FLASH: immediately set a high random brightness from 50 to 80
                    st_bright[y][x] = 50 + (rand() % 30);
                }
            }
            else {
                // If a star is already there, it only FADES
                if (st_bright[y][x] > 4) {
                    st_bright[y][x] -= 3; // Fade speed (bigger number = faster fade)
                } else {
                    st_bright[y][x] = 0;
                    st_state[y][x] = 0;   // Star fully faded, cell is free
                }
            }
        }
    }

    // Rendering
    ClearScreen();
    for (int y = 0; y < MAX_Y; y++) {
        for (int x = 0; x < MAX_X; x++) {
            if (st_state[y][x] != 0) {
                uint8_t b = st_bright[y][x];
                uint8_t s = st_state[y][x];
                uint8_t red = 0, green = 0, blue = 0;

                // Assign colors
                if (s == 1) {
                    red = b; blue = b / 6;       // Red
                } else if (s == 2) {
                    red = b / 6; blue = b;       // Blue
                } else if (s == 3) {
                    red = b / 2; blue = b;       // Purple
                }

                SetPixel(x, y, red, green, blue);
            }
        }
    }
    UpdateMatrix();
}

// ================= Rainbow helper function =================
// Converts a position (0-255) into an RGB color.
void ColorWheel(uint8_t pos, uint8_t *r, uint8_t *g, uint8_t *b) {
    pos = 255 - pos;
    if (pos < 85) {
        *r = 255 - pos * 3;
        *g = 0;
        *b = pos * 3;
    } else if (pos < 170) {
        pos -= 85;
        *r = 0;
        *g = pos * 3;
        *b = 255 - pos * 3;
    } else {
        pos -= 170;
        *r = pos * 3;
        *g = 255 - pos * 3;
        *b = 0;
    }
    // Dim brightness 8x so the earrings don't burn your eyes out (~12% brightness)
    *r = *r / 8;
    *g = *g / 8;
    *b = *b / 8;
}

// ================= MODE: RAINBOW WAVE =================
static uint8_t rainbow_offset = 0; // Wave offset (global variable, uses almost no memory)

void Rainbow_Tick(void) {
    rainbow_offset += 3; // Wave speed

    ClearScreen();
    for (int y = 0; y < MAX_Y; y++) {
        for (int x = 0; x < MAX_X; x++) {
            uint8_t r, g, b;

            // Diagonal math: multiply coordinates by the band "width"
            uint8_t pixel_hue = (x * 20) + (y * 20) + rainbow_offset;

            ColorWheel(pixel_hue, &r, &g, &b);
            SetPixel(x, y, r, g, b);
        }
    }
    UpdateMatrix();
}

// Random color on impact
void ChangeBallColor(uint8_t idx) {
    uint8_t c = rand() % 6;
    if (c == 0) { balls_data[idx].r = 40; balls_data[idx].g = 0;  balls_data[idx].b = 0;  }
    else if (c == 1) { balls_data[idx].r = 0;  balls_data[idx].g = 40; balls_data[idx].b = 0;  }
    else if (c == 2) { balls_data[idx].r = 0;  balls_data[idx].g = 0;  balls_data[idx].b = 40; }
    else if (c == 3) { balls_data[idx].r = 30; balls_data[idx].g = 30; balls_data[idx].b = 0;  }
    else if (c == 4) { balls_data[idx].r = 30; balls_data[idx].g = 0;  balls_data[idx].b = 30; }
    else if (c == 5) { balls_data[idx].r = 0;  balls_data[idx].g = 30; balls_data[idx].b = 30; }
}

// ================= SMOOTH BALL RENDERING (Anti-Aliasing) =================
void DrawSmoothBall(int16_t x, int16_t y, uint8_t r, uint8_t g, uint8_t b) {
    // Floor division and modulo instead of plain / and % - those round toward zero and for
    // negative x/y give a negative remainder, which makes rx/ry (uint8_t)
    // wrap around to huge values and the weights w00..w11 go outside 0..100.
    int16_t px16 = x / 100;
    int16_t rx16 = x % 100;
    if (rx16 < 0) { rx16 += 100; px16--; }

    int16_t py16 = y / 100;
    int16_t ry16 = y % 100;
    if (ry16 < 0) { ry16 += 100; py16--; }

    int8_t px = (int8_t)px16;     // Base pixel X
    int8_t py = (int8_t)py16;     // Base pixel Y
    uint8_t rx = (uint8_t)rx16;   // Offset from 0 to 99
    uint8_t ry = (uint8_t)ry16;   // Offset from 0 to 99

    // Compute glow percentage (0 to 100) for the 4 neighboring LEDs
    uint8_t w00 = ((100 - rx) * (100 - ry)) / 100; // Top left
    uint8_t w10 = (rx * (100 - ry)) / 100;         // Top right
    uint8_t w01 = ((100 - rx) * ry) / 100;         // Bottom left
    uint8_t w11 = (rx * ry) / 100;                 // Bottom right

    // Draw 4 pixels, distributing color brightness proportionally (bounds-checked in SetPixel)
    if (w00 > 0) SetPixel(px,     py,     (r * w00)/100, (g * w00)/100, (b * w00)/100);
    if (w10 > 0) SetPixel(px + 1, py,     (r * w10)/100, (g * w10)/100, (b * w10)/100);
    if (w01 > 0) SetPixel(px,     py + 1, (r * w01)/100, (g * w01)/100, (b * w01)/100);
    if (w11 > 0) SetPixel(px + 1, py + 1, (r * w11)/100, (g * w11)/100, (b * w11)/100);
}

// ================= MODE: PING-PONG =================
void Balls_Init(void) {
    balls_data[0].x = 100; balls_data[0].y = 100;
    balls_data[0].dx = 12; balls_data[0].dy = 18;
    ChangeBallColor(0);

    balls_data[1].x = 400; balls_data[1].y = 200;
    balls_data[1].dx = -16; balls_data[1].dy = 12;
    ChangeBallColor(1);

    balls_data[2].x = 200; balls_data[2].y = 700;
    balls_data[2].dx = 14; balls_data[2].dy = -20;
    ChangeBallColor(2);
}

void Balls_Tick(void) {
    int16_t max_x = (MAX_X - 1) * 100;
    int16_t max_y = (MAX_Y - 1) * 100;

    // 1. Move the balls and bounce off walls
    for (int i = 0; i < 3; i++) {
        balls_data[i].x += balls_data[i].dx;
        balls_data[i].y += balls_data[i].dy;

        uint8_t bounced = 0;

        if (balls_data[i].x <= 0) {
            balls_data[i].x = 0;
            balls_data[i].dx = -balls_data[i].dx;
            bounced = 1;
        } else if (balls_data[i].x >= max_x) {
            balls_data[i].x = max_x;
            balls_data[i].dx = -balls_data[i].dx;
            bounced = 1;
        }

        if (balls_data[i].y <= 0) {
            balls_data[i].y = 0;
            balls_data[i].dy = -balls_data[i].dy;
            bounced = 1;
        } else if (balls_data[i].y >= max_y) {
            balls_data[i].y = max_y;
            balls_data[i].dy = -balls_data[i].dy;
            bounced = 1;
        }

        if (bounced) ChangeBallColor(i);
    }

    // 2. Check collisions between balls
    for (int i = 0; i < 3; i++) {
        for (int j = i + 1; j < 3; j++) {
            int16_t dist_x = (balls_data[i].x > balls_data[j].x) ? (balls_data[i].x - balls_data[j].x) : (balls_data[j].x - balls_data[i].x);
            int16_t dist_y = (balls_data[i].y > balls_data[j].y) ? (balls_data[i].y - balls_data[j].y) : (balls_data[j].y - balls_data[i].y);

            if (dist_x < 100 && dist_y < 100) {
                int16_t temp_dx = balls_data[i].dx;
                int16_t temp_dy = balls_data[i].dy;
                balls_data[i].dx = balls_data[j].dx;
                balls_data[i].dy = balls_data[j].dy;
                balls_data[j].dx = temp_dx;
                balls_data[j].dy = temp_dy;

                balls_data[i].x += balls_data[i].dx * 5;
                balls_data[i].y += balls_data[i].dy * 5;
                balls_data[j].x += balls_data[j].dx * 5;
                balls_data[j].y += balls_data[j].dy * 5;

                // Separating after a collision can push a ball off the field
                // (e.g. if it hit another ball right after bouncing off a wall) -
                // clamp it back in bounds, otherwise DrawSmoothBall gets stray coordinates.
                if (balls_data[i].x < 0) balls_data[i].x = 0;
                else if (balls_data[i].x > max_x) balls_data[i].x = max_x;
                if (balls_data[i].y < 0) balls_data[i].y = 0;
                else if (balls_data[i].y > max_y) balls_data[i].y = max_y;

                if (balls_data[j].x < 0) balls_data[j].x = 0;
                else if (balls_data[j].x > max_x) balls_data[j].x = max_x;
                if (balls_data[j].y < 0) balls_data[j].y = 0;
                else if (balls_data[j].y > max_y) balls_data[j].y = max_y;

                ChangeBallColor(i);
                ChangeBallColor(j);
            }
        }
    }

    // 3. Smooth rendering
    ClearScreen();
    for (int i = 0; i < 3; i++) {
        // Instead of one coarse pixel, draw a smooth sub-pixel ball!
        DrawSmoothBall(balls_data[i].x, balls_data[i].y, balls_data[i].r, balls_data[i].g, balls_data[i].b);
    }
    UpdateMatrix();
}

// ================= MODE: RAIN ON GLASS =================
void Rain_Init(void) {
    for(int i = 0; i < 4; i++) rain_drops[i].active = 0;
    for(int i = 0; i < 8; i++) rain_splashes[i].active = 0;
}

void Rain_Tick(void) {
    // 1. Spawn new drops (rarely now!)
    if (rand() % 100 < 4) { // Chance lowered from 15% to 4%
        for (int i = 0; i < 4; i++) {
            if (!rain_drops[i].active) {
                rain_drops[i].x = rand() % MAX_X;
                rain_drops[i].y = (MAX_Y - 1) * 100;
                rain_drops[i].speed = 18 + (rand() % 12); // Was 15 + rand()%10, fall sped up by about 20%
                rain_drops[i].active = 1;
                break;
            }
        }
    }

    // 2. Drops falling
    for (int i = 0; i < 4; i++) {
        if (rain_drops[i].active) {
            rain_drops[i].y -= rain_drops[i].speed;

            // If the drop hit the bottom
            if (rain_drops[i].y <= 0) {
                rain_drops[i].active = 0;

                // Create 2 splashes
                int spawned = 0;
                for (int j = 0; j < 8 && spawned < 2; j++) {
                    if (!rain_splashes[j].active) {
                        rain_splashes[j].active = 1;
                        rain_splashes[j].x = rain_drops[i].x * 100;
                        rain_splashes[j].y = 0;

                        // Scatter sideways
                        rain_splashes[j].dx = (spawned == 0) ? (-12 - (rand() % 10)) : (12 + (rand() % 10));
                        // Splashes don't fly as high
                        rain_splashes[j].dy = 15 + (rand() % 15);
                        // Splash brightness (fades faster)
                        rain_splashes[j].life = 40 + (rand() % 20);
                        spawned++;
                    }
                }
            }
        }
    }

    // 3. Splash flight (with physics)
    for (int i = 0; i < 8; i++) {
        if (rain_splashes[i].active) {
            rain_splashes[i].x += rain_splashes[i].dx;
            rain_splashes[i].y += rain_splashes[i].dy;

            rain_splashes[i].dy -= 5; // Stronger gravity (splashes fall faster)

            // Splash fades faster
            if (rain_splashes[i].life > 5) {
                rain_splashes[i].life -= 5;
            } else {
                rain_splashes[i].active = 0;
            }

            if (rain_splashes[i].x <= 0 || rain_splashes[i].x >= (MAX_X - 1) * 100) {
                rain_splashes[i].dx = -rain_splashes[i].dx;
            }

            if (rain_splashes[i].y <= 0) {
                rain_splashes[i].y = 0;
                rain_splashes[i].dy = 0;
                rain_splashes[i].dx = rain_splashes[i].dx / 2;
            }
        }
    }

    // 4. Rendering
    ClearScreen();

    // Draw splashes first
    for (int i = 0; i < 8; i++) {
        if (rain_splashes[i].active) {
            uint8_t l = rain_splashes[i].life;
            // Splash color: add red and green so splashes look WHITE, not blue
            DrawSmoothBall(rain_splashes[i].x, rain_splashes[i].y, l/3, l/2, l);
        }
    }

    // Draw the raindrops on top
    for (int i = 0; i < 4; i++) {
        if (rain_drops[i].active) {
            int8_t px = rain_drops[i].x;
            int8_t py = rain_drops[i].y / 100;

            SetPixel(px, py, 0, 15, 45); // Drop head (deep blue-cyan)
            if (py + 1 < MAX_Y) SetPixel(px, py + 1, 0, 5, 20); // Tail
            if (py + 2 < MAX_Y) SetPixel(px, py + 2, 0, 1, 5);  // Tail end
        }
    }

    UpdateMatrix();
}
//------------------------------ notes -------------------------------------------------//
