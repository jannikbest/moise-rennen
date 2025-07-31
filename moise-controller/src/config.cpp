#include "config.h"

// Mouse 1 configuration (right side)
MousePins mouse1_pins = {
  .home = 22, .win = 2,
  .score1 = 21, .score2 = 19, .score3 = 18,
  .motor_in1 = 17, .motor_in2 = 16, .motor_en = 4,
  .led = 5
};

// Mouse 2 configuration (left side)
MousePins mouse2_pins = {
  .home = 32, .win = 33,
  .score1 = 27, .score2 = 26, .score3 = 25,
  .motor_in1 = 14, .motor_in2 = 12, .motor_en = 13,
  .led = 15
}; 