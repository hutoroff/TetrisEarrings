#include "games.h"
//----------------------- variables from other files ---------------------------------//

//----------------------- variables from this file -----------------------------------//
int current_brightness = 5; // Initial brightness
int fade_step = 2;          // Brightness step (pulse speed)
// Colors for the 7 classic pieces (plus 0 - empty cell). Format {R, G, B}
const uint8_t colors[8][3] = {
  {0, 0, 0},       // 0: Empty
  {0, 20, 20},     // 1: I - Cyan
  {0, 0, 20},      // 2: J - Blue
  {20, 10, 0},     // 3: L - Orange
  {20, 20, 0},     // 4: O - Yellow
  {0, 20, 0},      // 5: S - Green
  {15, 0, 15},     // 6: T - Purple
  {20, 0, 0}       // 7: Z - Red
};

// Piece array: 7 pieces x 4 rotation states
const uint16_t tetrominoes[7][4] = {
  {0x0F00, 0x2222, 0x00F0, 0x4444}, // I
  {0x44C0, 0x8E00, 0x6440, 0x0E20}, // J
  {0x4460, 0x0E80, 0xC440, 0x2E00}, // L
  {0xCC00, 0xCC00, 0xCC00, 0xCC00}, // O
  {0x06C0, 0x8C40, 0x6C00, 0x4620}, // S
  {0x0E40, 0x4C40, 0x4E00, 0x4640}, // T
  {0x0C60, 0x4C80, 0xC600, 0x2640}  // Z
};

// Tick counter for independent animation
uint8_t game_tick_counter = 0;

//------------------------------ functions -------------------------------------------//
void DrawGame(void) {                               // Updated render function (Y axis direction fixed)
  ClearScreen();
  for (int y = 0; y < MAX_Y; y++) {                 // 1. Draw the "well" (already landed pieces)
	  for (int x = 0; x < MAX_X; x++) {
		  if (gameBoard[y][x] != 0) {
			  uint8_t c_id = gameBoard[y][x];
			  SetPixel(x, y, colors[c_id][0], colors[c_id][1], colors[c_id][2]);
		  }
	  }
  }
  // 2. Draw the currently falling piece
  uint16_t piece = tetrominoes[current_id][current_rotation];
  uint8_t c_id = current_id + 1;
  for (int px = 0; px < 4; px++) {
	  for (int py = 0; py < 4; py++) {
		  if (piece & (1 << (15 - (py * 4 + px)))) {
			  int draw_x = current_x + px;
			  int draw_y = current_y - py;         // Y points up, the piece extends downward

			  if (draw_x >= 0 && draw_x < MAX_X && draw_y >= 0 && draw_y < MAX_Y) {
				  SetPixel(draw_x, draw_y, colors[c_id][0], colors[c_id][1], colors[c_id][2]);
			  }
		  }
	  }
  }
}
// Collision check
uint8_t CheckCollision(int8_t test_x, int8_t test_y, int8_t test_rot) {
  uint16_t piece = tetrominoes[current_id][test_rot];
  for (int px = 0; px < 4; px++) {
	  for (int py = 0; py < 4; py++) {
		  if (piece & (1 << (15 - (py * 4 + px)))) {
			  int board_x = test_x + px;
			  int board_y = test_y - py;
			  if (board_x < 0 || board_x >= MAX_X || board_y < 0) {       // Collision with walls and floor
				  return 1;
			  }
			  if (board_y < MAX_Y && gameBoard[board_y][board_x] != 0) {  // Collision with other blocks (if within the field)
				  return 1;
			  }
		  }
	  }
  }
  return 0;                                                               // Path is clear
}

void LockPiece(void) {                                                    // Lock the piece into the well
  uint16_t piece = tetrominoes[current_id][current_rotation];
  for (int px = 0; px < 4; px++) {
	  for (int py = 0; py < 4; py++) {
		  if (piece & (1 << (15 - (py * 4 + px)))) {
			  int board_x = current_x + px;
			  int board_y = current_y - py;
			  if (board_y >= 0 && board_y < MAX_Y && board_x >= 0 && board_x < MAX_X) {
				  gameBoard[board_y][board_x] = current_id + 1;
			  }
		  }
	  }
  }
}

void ClearLines(void) {                                                   // Remove completed lines
  for (int y = 0; y < MAX_Y; y++) {
	  uint8_t full = 1;
	  for (int x = 0; x < MAX_X; x++) {
		  if (gameBoard[y][x] == 0) {
			  full = 0;
			  break;
		  }
	  }
	  if (full) {                                                         // Shift everything above down one row
		  for (int shift_y = y; shift_y < MAX_Y - 1; shift_y++) {
			  for (int x = 0; x < MAX_X; x++) {
				  gameBoard[shift_y][x] = gameBoard[shift_y + 1][x];
			  }
		  }
		  for (int x = 0; x < MAX_X; x++) {                               // Clear the topmost row
			  gameBoard[MAX_Y - 1][x] = 0;
		  }
		  y--;                                                            // Check the same row again (new blocks fell into it)
	  }
  }
}

// Game over animation
void GameOverAnim(void) {
  // 1. Hide the current (new) piece far off screen
  // so its color doesn't cover the red animation
  current_y = 100;
  // 2. Smoothly fill the screen red from bottom to top
  for (int y = 0; y < MAX_Y; y++) {
	  for (int x = 0; x < MAX_X; x++) {
		  gameBoard[y][x] = 7;
	  }
	  DrawGame();
	  UpdateMatrix();
	  HAL_Delay(50); // Animation slightly sped up
  }

  // 3. Short pause on the fully red screen
  HAL_Delay(500);

  // 4. Clear the well for a new game
  for (int y = 0; y < MAX_Y; y++) {
	  for (int x = 0; x < MAX_X; x++) {
		  gameBoard[y][x] = 0;
	  }
  }
}

// Bot "AI": tries every rotation and column for the current piece,
// drops it into a copy of the well on the fly and scores the result with a simple
// heuristic (well height, holes under the piece, column height differences,
// cleared lines) - in the spirit of classic Tetris bots (Dellacherie/El-Tetris),
// but in integers, no float, to avoid bloating the firmware on Cortex-M0.
static void ChooseBestMove(void) {
  int16_t best_score = -32000;
  int8_t best_rot = 0;
  int8_t best_x = current_x;

  for (int8_t rot = 0; rot < 4; rot++) {
    for (int8_t x = -3; x < MAX_X + 3; x++) {
      if (CheckCollision(x, MAX_Y, rot)) continue; // Piece doesn't fit width-wise here

      // Find which row the piece actually lands on
      int8_t y = MAX_Y;
      while (!CheckCollision(x, y - 1, rot)) y--;

      // Try placing the piece into a copy of the well
      uint8_t temp[MAX_Y][MAX_X];
      for (int8_t ty = 0; ty < MAX_Y; ty++) {
        for (int8_t tx = 0; tx < MAX_X; tx++) temp[ty][tx] = gameBoard[ty][tx];
      }

      uint16_t piece = tetrominoes[current_id][rot];
      for (int8_t px = 0; px < 4; px++) {
        for (int8_t py = 0; py < 4; py++) {
          if (piece & (1 << (15 - (py * 4 + px)))) {
            int8_t bx = x + px;
            int8_t by = y - py;
            if (bx >= 0 && bx < MAX_X && by >= 0 && by < MAX_Y) temp[by][bx] = 1;
          }
        }
      }

      // Height of each column and holes under the pieces
      int8_t heights[MAX_X];
      int16_t holes = 0;
      for (int8_t tx = 0; tx < MAX_X; tx++) {
        int8_t top = -1;
        for (int8_t ty = MAX_Y - 1; ty >= 0; ty--) {
          if (temp[ty][tx] != 0) { top = ty; break; }
        }
        heights[tx] = top + 1;
        for (int8_t ty = 0; ty < top; ty++) {
          if (temp[ty][tx] == 0) holes++;
        }
      }

      int16_t agg_height = 0, bumpiness = 0;
      for (int8_t tx = 0; tx < MAX_X; tx++) {
        agg_height += heights[tx];
        if (tx > 0) {
          int8_t d = heights[tx] - heights[tx - 1];
          bumpiness += (d < 0) ? -d : d;
        }
      }

      int16_t lines = 0;
      for (int8_t ty = 0; ty < MAX_Y; ty++) {
        uint8_t full = 1;
        for (int8_t tx = 0; tx < MAX_X; tx++) {
          if (temp[ty][tx] == 0) { full = 0; break; }
        }
        if (full) lines++;
      }

      int16_t score = (lines * 8) - (agg_height * 4) - (holes * 6) - (bumpiness * 2);

      if (score > best_score) {
        best_score = score;
        best_rot = rot;
        best_x = x;
      }
    }
  }

  target_rot = best_rot;
  target_x = best_x;
}

void SpawnPiece(void) {
  // 1. Generate parameters for the new piece
  current_id = rand() % 7;
  current_rotation = 0;
  current_x = 2;
  current_y = MAX_Y;

  ChooseBestMove(); // Instead of a random target - a deliberate choice of rotation and column

  // 2. Check whether there's room on the field
  if (CheckCollision(current_x, MAX_Y - 1, current_rotation)) {
	  // No room - play the game over animation (piece hides at Y=100)
	  GameOverAnim();

	  // 3. FIX: After clearing the well, regenerate the piece
	  // so it appears right above the screen instead of falling from height 100!
	  current_id = rand() % 7;
	  current_rotation = 0;
	  current_x = 2;
	  current_y = MAX_Y;
	  ChooseBestMove();
  }
}

// Steps the piece toward the target chosen in ChooseBestMove (rotate, then shift)
void BotMove(void) {
  // First try to rotate the piece if the target isn't reached yet
  if (current_rotation != target_rot) {
	  int8_t next_rot = (current_rotation + 1) % 4;
	  if (!CheckCollision(current_x, current_y, next_rot)) {
		  current_rotation = next_rot;
	  } else {
		  target_rot = current_rotation; // Blocked - cancel the rotation plan
	  }
  }
  // Once rotated correctly, start moving horizontally
  else if (current_x < target_x) {
	  if (!CheckCollision(current_x + 1, current_y, current_rotation)) {
		  current_x++;
	  } else {
		  target_x = current_x; // Hit a wall or block - stay here
	  }
  }
  else if (current_x > target_x) {
	  if (!CheckCollision(current_x - 1, current_y, current_rotation)) {
		  current_x--;
	  } else {
		  target_x = current_x;
	  }
  }
}
// Main game tick
void GameTick(void) {
  game_tick_counter++;

  // Bot makes a horizontal step or rotation every 3 ticks
  if (game_tick_counter % 3 == 0) {
	  BotMove();
  }

  // Gravity pulls the piece down every 5 ticks (falls slower than it moves sideways)
  if (game_tick_counter >= 5) {
	  game_tick_counter = 0; // Reset the counter

	  if (!CheckCollision(current_x, current_y - 1, current_rotation)) {
		  current_y--;
	  } else {
		  LockPiece();
		  ClearLines();
		  SpawnPiece();
	  }
  }

  DrawGame();
  UpdateMatrix();
}

// Spawn food at a random free spot
void Snake_SpawnFood(void) {
  uint8_t valid = 0;
  while (!valid) {
	  food.x = rand() % MAX_X;
	  food.y = rand() % MAX_Y;

	  valid = 1;
	  // Make sure the food doesn't spawn inside the snake
	  for (int i = 0; i < snake_len; i++) {
		  if (snake[i].x == food.x && snake[i].y == food.y) {
			  valid = 0;
			  break;
		  }
	  }
  }
}

// Reset and init the Snake game
void Snake_Init(void) {
  snake_len = 3;
  // Snake starting position in the center
  snake[0].x = 3; snake[0].y = 5; // Head
  snake[1].x = 2; snake[1].y = 5;
  snake[2].x = 1; snake[2].y = 5; // Tail

  dir_x = 1; // Moving right
  dir_y = 0;

  Snake_SpawnFood();
}

// Check: is the cell safe to step on?
uint8_t Snake_IsSafe(int8_t x, int8_t y) {
  // Out of bounds
  if (x < 0 || x >= MAX_X || y < 0 || y >= MAX_Y) return 0;

  // Self-collision (skip the last tail segment, since it will move away)
  for (int i = 0; i < snake_len - 1; i++) {
	  if (snake[i].x == x && snake[i].y == y) return 0;
  }
  return 1;
}

// Direction selection logic for the auto-bot
void Snake_BotLogic(void) {
  Point head = snake[0];

  // Possible directions: Up, Down, Left, Right
  int8_t dx[4] = {0, 0, -1, 1};
  int8_t dy[4] = {1, -1, 0, 0};

  int best_dir = -1;
  int min_dist = 999;

  // 1. Try to find a safe step that brings us closer to the food
  for (int i = 0; i < 4; i++) {
	  // Can't turn 180 degrees
	  if (dx[i] == -dir_x && dy[i] == -dir_y) continue;

	  int8_t next_x = head.x + dx[i];
	  int8_t next_y = head.y + dy[i];

	  if (Snake_IsSafe(next_x, next_y)) {
		  // Distance to food (Manhattan)
		  int dist = abs(food.x - next_x) + abs(food.y - next_y);
		  if (dist < min_dist) {
			  min_dist = dist;
			  best_dir = i;
		  }
	  }
  }

  // 2. If the path to food is blocked, pick ANY safe turn
  if (best_dir == -1) {
	  for (int i = 0; i < 4; i++) {
		  if (dx[i] == -dir_x && dy[i] == -dir_y) continue;
		  if (Snake_IsSafe(head.x + dx[i], head.y + dy[i])) {
			  best_dir = i;
			  break;
		  }
	  }
  }

  // Apply the chosen direction
  if (best_dir != -1) {
	  dir_x = dx[best_dir];
	  dir_y = dy[best_dir];
  }
}

// Crash animation (Game Over)
void Snake_GameOverAnim(void) {
  // Red flash
  for (int i = 0; i < 3; i++) {
	  ClearScreen();
	  UpdateMatrix();
	  HAL_Delay(100);

	  // Fill everything red
	  for (int y = 0; y < MAX_Y; y++) {
		  for (int x = 0; x < MAX_X; x++) {
			  SetPixel(x, y, 30, 0, 0);
		  }
	  }
	  UpdateMatrix();
	  HAL_Delay(100);
  }

  Snake_Init(); // Restart the game
}

// Main Snake tick
void Snake_Tick(void) {
  Snake_BotLogic(); // Bot makes its choice

  int8_t new_x = snake[0].x + dir_x;
  int8_t new_y = snake[0].y + dir_y;

  // No moves left - game over
  if (!Snake_IsSafe(new_x, new_y)) {
	  Snake_GameOverAnim();
	  return;
  }

  // Check whether food is eaten
  uint8_t ate_food = (new_x == food.x && new_y == food.y);

  if (ate_food) {
	  if (snake_len < SNAKE_MAX_LEN) snake_len++;
	  Snake_SpawnFood();
  }

  // Move the body (each segment takes the previous one's place)
  for (int i = snake_len - 1; i > 0; i--) {
	  snake[i] = snake[i - 1];
  }

  // Move the head
  snake[0].x = new_x;
  snake[0].y = new_y;

  // RENDERING
  ClearScreen();

  // 1. Draw the food (blue)
  SetPixel(food.x, food.y, 0, 0, 40);

  // 2. Draw the snake body (green)
  for (int i = 1; i < snake_len; i++) {
	  SetPixel(snake[i].x, snake[i].y, 0, 30, 0);
  }

  // 3. Draw the snake head (red)
  SetPixel(snake[0].x, snake[0].y, 40, 0, 0);

  UpdateMatrix();
}

// --- TETRIS INIT ---
void Tetris_Init(void) {
  for(int y = 0; y < MAX_Y; y++) {
	  for(int x = 0; x < MAX_X; x++) {
		  gameBoard[y][x] = 0;
	  }
  }
  SpawnPiece();
}

//------------------------------ notes -------------------------------------------------//


