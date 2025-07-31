#ifndef CONFIG_H
#define CONFIG_H

// Test configuration
#define TEST_IO 0       // Enable IO testing
#define TEST_AUTO_RACE 0  // Auto-start race after 5 seconds in IDLE
#define TEST_STATE_MACHINE 1  // Test state machine without IOs

// ===== GAME TIMING CONSTANTS =====
// State machine timings (milliseconds)
#define STARTUP_DURATION 2000       // STARTUP state duration
#define SCORE_DISPLAY_DURATION 2000 // How long to show score colors
#define AUTO_RACE_DELAY 5000        // Auto-start race in test mode
#define AUTO_RETURN_DELAY 5000      // Auto-return to homing after win

// Score system timings (milliseconds)  
#define SCORE_1PT_MOTOR_TIME 2000   // Motor time for 1 point
#define SCORE_2PT_MOTOR_TIME 4000   // Motor time for 2 points  
#define SCORE_3PT_MOTOR_TIME 6000   // Motor time for 3 points

// LED animation timings (milliseconds)
#define HOMING_BLINK_INTERVAL 500   // Homing state blink speed
#define WINNER_BLINK_INTERVAL 100   // Winner celebration blink speed
#define RUNNING_LIGHT_INTERVAL 50   // Running light animation speed

// System timings (milliseconds)
#define SETUP_DELAY 1000           // Initial setup delay
#define MAIN_LOOP_DELAY 10         // Main loop polling interval

// ===== COLOR CONSTANTS =====
// Score colors (RGB)
#define COLOR_1PT_R 0, 255, 0      // Green for 1 point
#define COLOR_2PT_R 0, 0, 255      // Blue for 2 points
#define COLOR_3PT_R 255, 0, 0      // Red for 3 points

// System colors (RGB)
#define COLOR_WHITE_R 255, 255, 255  // White (homing, idle)
#define COLOR_RED_R 255, 0, 0        // Red (startup, winner, test)
#define COLOR_BLUE_R 0, 0, 255       // Blue (reference run)

// LED brightness values
#define LED_BRIGHTNESS_MAX 255      // Maximum brightness
#define LED_BRIGHTNESS_DIM 20       // Dimmed brightness (running light sides)

// ===== HARDWARE CONSTANTS =====
#define SERIAL_BAUD_RATE 115200      // Serial communication speed

// Pin configuration structure
struct MousePins {
  // Limit Switches (NO) - Ground switching with pullup
  int home;
  int win;
  
  // Score Buttons (NO)
  int score1;
  int score2;
  int score3;
  
  // H-Bridge Motor Control
  int motor_in1;
  int motor_in2;
  int motor_en;
  
  // LED Strip
  int led;
};

// Mouse 1 configuration (right side)
extern MousePins mouse1_pins;

// Mouse 2 configuration (left side)
extern MousePins mouse2_pins;

#endif 