#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include "config.h"
#include "mouse.h"
#include "game.h"

// Create mouse instances
Mouse mouse1(mouse1_pins, "M1");  // Red
Mouse mouse2(mouse2_pins, "M2");  // Blue

// Create game instance
Game game;

void setup() {
  Serial.begin(SERIAL_BAUD_RATE);
  delay(SETUP_DELAY);
  
  mouse1.setup();
  mouse2.setup();
  
  // Register mice with game
  game.registerMouse1(&mouse1);
  game.registerMouse2(&mouse2);
}

void loop() {
  // Check for serial commands
  if (Serial.available() > 0) {
    String command = Serial.readString();
    command.trim(); // Remove whitespace/newlines
    if (command.length() > 0) {
      game.setCommand(command);
    }
  }
  
  #if !TEST_STATE_MACHINE
  // Read hardware inputs first
  mouse1.input();
  mouse2.input();
  
  // Then process logic
  mouse1.update();
  mouse2.update();
  #endif
  
  game.update();
  delay(MAIN_LOOP_DELAY);  // Polling interval
}