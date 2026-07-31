#ifndef CONFIG_H
#define CONFIG_H

#define FIRMWARE_VERSION "2.0.0"

// ===== GAME TIMING CONSTANTS =====
// Do not casually change: MAIN_LOOP_DELAY is the debounce sampling rate.
#define STARTUP_DURATION 2000
#define SCORE_DISPLAY_DURATION 2000
#define AUTO_RACE_DELAY 5000
#define AUTO_RETURN_DELAY 5000

#define SCORE_1PT_MOTOR_TIME 500
#define SCORE_2PT_MOTOR_TIME 1000
#define SCORE_3PT_MOTOR_TIME 1500

#define HOMING_BLINK_INTERVAL 500
#define WINNER_BLINK_INTERVAL 100
#define RUNNING_LIGHT_INTERVAL 50

#define SETUP_DELAY 1000
#define MAIN_LOOP_DELAY 10

#define DBG_MOTOR_DEFAULT_MS 500
#define DBG_MOTOR_MAX_MS 5000
#define IDENTIFY_DURATION_MS 3000

#define COLOR_1PT_R 0, 255, 255
#define COLOR_2PT_R 255, 0, 255
#define COLOR_3PT_R 255, 165, 0

#define COLOR_WHITE_R 255, 255, 255
#define COLOR_RED_R 255, 0, 0
#define COLOR_BLUE_R 0, 0, 255

#define LED_BRIGHTNESS_MAX 255
#define LED_BRIGHTNESS_DIM 20

#define SERIAL_BAUD_RATE 115200
#define SERIAL_LINE_MAX 96

struct MousePins {
  int home;
  int win;
  int score1;
  int score2;
  int score3;
  int motor_in1;
  int motor_in2;
  int motor_en;
  int led;
};

extern MousePins mouse1_pins;
extern MousePins mouse2_pins;

#endif
