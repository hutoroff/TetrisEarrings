# ✨ TetrisEarrings

Earrings built on a 6×10 LED matrix with nine mesmerizing animated modes — from ping-pong and Tetris with an autonomous bot to fire, a starry sky, and rain on glass.

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![MCU](https://img.shields.io/badge/MCU-STM32F070F6-03234B)
![Core](https://img.shields.io/badge/core-Cortex--M0-lightgrey)
![IDE](https://img.shields.io/badge/IDE-STM32CubeIDE%201.17.0-03234B)
![LEDs](https://img.shields.io/badge/matrix-6×10%20WS2812-orange)

<p align="center">
  <img src="20260912_095812.jpg" width="420" alt="TetrisEarrings in action">
</p>

## About

A tiny STM32 board hidden inside the earring drives a matrix of 60 addressable RGB LEDs (6 columns × 10 rows). A single button switches modes manually, or they cycle on their own every 45 seconds. The device runs on a battery and can power itself off — either on a long button press or when the battery runs low — with a short farewell animation.

## Features

- 🎮 **9 modes** — from classic games to generative visual effects
- 🧠 **Tetris with a "smart" bot** — pieces don't just fall randomly: before each drop the bot tries every rotation and column and picks the placement using a heuristic (fewest holes, lowest height and bumpiness, most cleared lines)
- 🐍 **Snake with an autonomous bot** — finds its own path to the food and never runs into itself
- 🎨 **Sub-pixel smoothing** — the ping-pong balls move smoothly instead of jumping from LED to LED
- 🔋 **Smart power management** — continuous battery voltage monitoring and automatic shutdown on low battery
- 📺 **Power-off animation** — the screen "collapses" into a dot and fades out, like an old CRT TV
- 🧩 **Everything in 6 KB of RAM** — all modes share the same memory region (a union) instead of each mode keeping its own data

## Modes

| # | Mode | Description |
|---|---|---|
| 0 | Ping-Pong | Three balls fly around and bounce off each other, changing color on impact |
| 1 | Tetris | Autonomous game with a bot that deliberately chooses where to place each piece |
| 2 | Snake | Autonomous game; the bot steers the snake to the food by itself |
| 3 | Heart | A smoothly pulsing heart |
| 4 | Fire | Procedural simulation of a living flame with sparks |
| 5 | Matrix | Falling green "digital rain" in the style of *The Matrix* |
| 6 | Starry Sky | Sparse twinkling stars of different hues that slowly fade out |
| 7 | Rainbow | A shimmering diagonal rainbow wave |
| 8 | Rain on Glass | Drops trickle down and burst into splashes when they hit the bottom |

Short button press — next mode; hold for about a second — power off (with animation). With no presses, modes cycle automatically every 45 seconds.

## Hardware

| Parameter | Value |
|---|---|
| Microcontroller | STM32F070F6Px (Cortex-M0, 48 MHz, 32 KB Flash, 6 KB RAM) |
| Matrix | 6×10 (60 pcs) addressable RGB LEDs, WS2812-compatible protocol |
| Matrix data line | PA9 (TIM1_CH2 + DMA, per-bit PWM signal encoding) |
| Button | PA7 |
| Power control | PA6 (board power self-latch / shutdown) |
| Battery monitoring | PA1 (ADC1_IN1), auto-shutdown on low battery |
| Development environment | STM32CubeIDE 1.17.0, GNU Arm Embedded Toolchain 12.3.rel1 |

The matrix LEDs are wired in a "serpentine" layout: even rows run in one direction, odd rows in the other (see `GetLEDIndex()` in [ledMatrix.c](Core/Src/ledMatrix.c)).

## Electronics (Altium)

Board sources (schematic, layout, BOM) in Altium Designer: **[link coming soon]**

> Once the project is uploaded to Google Drive, replace this line with the link.

## Building and Flashing

1. Clone the repository and open the project folder in **STM32CubeIDE 1.17.0** (File → Import → General → Existing Projects into Workspace).
2. Choose a build configuration:
   - **Debug** — full debug symbols, `-Og` optimization (chosen specifically so the firmware fits into the chip's 32 KB of flash while still being easy to debug);
   - **Release** — `-Os` build, minimal size.
3. **Project → Build Project**.
4. Flash via ST-Link: **Run → Debug** (or **Run**) with the programmer connected.

## Project Structure

```
Core/
├── Inc/                  # Headers
│   ├── effects.h          # Visual effects
│   ├── games.h            # Tetris and Snake
│   ├── ledMatrix.h        # WS2812 driver
│   └── saportAndData.h    # Shared state (pins, shared mode memory)
└── Src/
    ├── main.c              # Entry point, peripheral initialization
    ├── work.c               # Mode dispatcher, button, ADC, auto-shutdown
    ├── effects.c             # Ping-Pong, Fire, Matrix, Stars, Rainbow, Rain, Heart
    ├── games.c               # Tetris (with AI bot) and Snake (with autonomous bot)
    └── ledMatrix.c            # Addressable matrix driver on top of TIM1 + DMA
```

## License

This project is distributed under the [MIT](LICENSE) license.
