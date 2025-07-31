# Dual Mouse Racing Game Controller

## Overview
Professional ESP32-based controller for a 2-player competitive racing game where players throw balls to score points, moving their "mouse" forward toward a winning position. Features modular architecture, centralized configuration, and robust state management.

## Hardware Configuration
**2 identical mouse units**, each with:
- **H-Bridge Motor**: Forward/backward movement control
- **2 Limit Switches**: Home (NO) and Win (NO) position detection (Ground switching)  
- **3 Score Buttons**: 1, 2, 3 point scoring (NO switches)
- **20-LED NeoPixel Strip**: Visual feedback and animations
- **ESP32 Controller**: Manages all I/O and game logic

## GPIO Pinout

### Mouse 1 (Right Side)
| Component | Pin | Type | Description |
|-----------|-----|------|-------------|
| Motor IN1 | GPIO 17 | Output | H-Bridge direction control 1 |
| Motor IN2 | GPIO 16 | Output | H-Bridge direction control 2 |
| Motor EN  | GPIO 4  | Output | H-Bridge speed control (PWM) |
| Home Switch | GPIO 22 | Input (Pullup) | Home position limit (NO) |
| Win Switch  | GPIO 2  | Input (Pullup) | Win position limit (NO) |
| Score 1pt | GPIO 21 | Input (Pulldown) | 1 point button (NO) |
| Score 2pt | GPIO 19 | Input (Pulldown) | 2 point button (NO) |
| Score 3pt | GPIO 18 | Input (Pulldown) | 3 point button (NO) |
| LED Strip | GPIO 5  | Output | 20x NeoPixel status LEDs |

### Mouse 2 (Left Side)
| Component | Pin | Type | Description |
|-----------|-----|------|-------------|
| Motor IN1 | GPIO 14 | Output | H-Bridge direction control 1 |
| Motor IN2 | GPIO 12 | Output | H-Bridge direction control 2 |
| Motor EN  | GPIO 13 | Output | H-Bridge speed control (PWM) |
| Home Switch | GPIO 32 | Input (Pullup) | Home position limit (NO) |
| Win Switch  | GPIO 33 | Input (Pullup) | Win position limit (NO) |
| Score 1pt | GPIO 27 | Input (Pulldown) | 1 point button (NO) |
| Score 2pt | GPIO 26 | Input (Pulldown) | 2 point button (NO) |
| Score 3pt | GPIO 25 | Input (Pulldown) | 3 point button (NO) |
| LED Strip | GPIO 15 | Output | 20x NeoPixel status LEDs |

## Architecture & Code Structure

### Core Classes
- **`Mouse`** (`mouse.h/cpp`): Hardware abstraction layer
  - Input reading and edge detection
  - Motor control and LED management  
  - Hardware-agnostic interface
- **`Game`** (`game.h/cpp`): Game logic and state management
  - State machine (STARTUP → IO_CHECK → HOMING → IDLE → RACE → STOP)
  - Score system and win detection
  - Serial communication protocol
- **`config.h/cpp`**: Centralized configuration
  - GPIO pin definitions
  - Timing constants and game rules
  - Color definitions and hardware settings

### Key Features
✅ **Input/Logic Separation**: Clean `input()` → `update()` flow  
✅ **Edge Detection Helpers**: Reusable button state detection  
✅ **Centralized Configuration**: All constants in `config.h`  
✅ **Modular Architecture**: Hardware vs Logic separation  
✅ **Additive Scoring System**: Multiple hits extend motor time  
✅ **LED Animations**: Running lights, score displays, win celebrations  

## Game Flow & States

### State Machine
1. **STARTUP** (2s): Red LEDs, system initialization
2. **IO_CHECK**: Hardware validation and error detection
3. **HOMING**: Individual mouse homing with white blinking LEDs
4. **IDLE**: White solid LEDs, sends "ready", waits for "go" command
5. **RACE**: Running light animation, score detection, win monitoring
6. **STOP**: Winner celebration (fast red blink), loser LEDs off

### Scoring System
- **1 Point**: Green LED (2s) + 2s motor forward
- **2 Points**: Blue LED (2s) + 4s motor forward  
- **3 Points**: Red LED (2s) + 6s motor forward
- **Additive**: Multiple hits accumulate motor time
- **Serial Output**: "11"/"12"/"13" for Mouse 1, "21"/"22"/"23" for Mouse 2

### Win Detection
- WIN switch triggers immediate game end
- Serial announcements: "win1" or "win2"
- Winner: Fast red blinking LEDs
- Loser: LEDs turned off

## Communication Protocol

### Serial Settings
- **Baud Rate**: 9600  
- **Format**: Human-readable text commands

### Command Interface
| Command | Description | Valid States |
|---------|-------------|--------------|
| `go` | Start race | IDLE |
| `home` | Force homing | Any |
| `lose` | External game over | Any |
| `reset` | Emergency stop → IO_CHECK | Any |

### Status Messages
| Message | Description |
|---------|-------------|
| `ready` | System ready for race start |
| `win1` / `win2` | Mouse 1/2 reached win position |
| `11`-`13` / `21`-`23` | Score events (mouse + points) |
| `Error: *` | Error conditions and invalid commands |

## Configuration & Customization

### Easy Tuning via `config.h`
```cpp
// Game timing (milliseconds)
#define SCORE_1PT_MOTOR_TIME 2000   // Motor time for 1 point
#define SCORE_2PT_MOTOR_TIME 4000   // Motor time for 2 points  
#define SCORE_3PT_MOTOR_TIME 6000   // Motor time for 3 points

// Colors (RGB)
#define COLOR_1PT_R 0, 255, 0      // Green for 1 point
#define COLOR_2PT_R 0, 0, 255      // Blue for 2 points
#define COLOR_3PT_R 255, 0, 0      // Red for 3 points

// Test modes
#define TEST_IO 0           // Enable hardware testing
#define TEST_AUTO_RACE 1    // Auto-cycling for demos
```

## Development Status

### ✅ Completed Features
- **Hardware Abstraction**: Complete Mouse class with all I/O
- **State Machine**: Full game flow implementation
- **Score System**: Additive scoring with visual feedback
- **LED Animations**: Running lights, score displays, celebrations
- **Communication**: Complete serial protocol
- **Error Handling**: Hardware validation and graceful error recovery
- **Test Modes**: IO testing and auto-racing demos
- **Code Quality**: Modular architecture, centralized constants

### Current Phase: Production Ready
The system is fully functional with professional code organization:
- Clean separation of concerns (Hardware/Logic)
- Comprehensive error handling and validation
- Configurable game rules and timing
- Robust state management
- Complete feature set for competitive gaming

## Technical Specifications
- **Microcontroller**: ESP32 DevKit
- **LED Technology**: WS2812/NeoPixel compatible (20 LEDs per player)
- **Motor Control**: PWM speed control (0-255) with direction switching
- **Debouncing**: Hardware-level edge detection with state tracking
- **Communication**: 9600 baud serial over USB
- **Update Rate**: 10ms main loop for responsive control 