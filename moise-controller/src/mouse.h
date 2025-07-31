#ifndef MOUSE_H
#define MOUSE_H

#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include "config.h"

class Mouse {
private:
  MousePins pins;
  String name;
  
  // Constants
  const int NUM_LEDS = 20;
  const int LED_BRIGHTNESS = 20;
  const int MOTOR_SPEED = 255;  // Used for homing and reference run
  const int MOTOR_STOP = 0;
  
  // LED strip object
  Adafruit_NeoPixel strip;
  
  // Speed control
  int raceSpeed;  // Current race speed (0-255), set by Game via setRaceSpeed()
  
  // State tracking
  int lastHomeState = HIGH;
  int lastWinState = HIGH;
  int lastScore1State = LOW;
  int lastScore2State = LOW;
  int lastScore3State = LOW;
  
  // Current input states (read by input() method)
  int currentHomeState = HIGH;
  int currentWinState = HIGH;
  int currentScore1State = LOW;
  int currentScore2State = LOW;
  int currentScore3State = LOW;
  
  // Blinking state
  bool isBlinking;
  int blinkR, blinkG, blinkB;
  unsigned long blinkInterval;
  unsigned long lastBlinkTime;
  bool blinkState;
  
  // Running light state
  bool isRunningLight;
  int runningPosition;
  unsigned long lastRunningTime;
  
  // Score display state
  bool isScoreDisplay;
  unsigned long scoreDisplayStartTime;
  unsigned long scoreDisplayDuration;
  int scoreDisplayR, scoreDisplayG, scoreDisplayB;
  
  // Score motor state
  bool isScoreMotor;
  unsigned long scoreMotorStartTime;
  unsigned long scoreMotorDuration;

  // Private methods
  void updateBlinking();
  void updateRunningLight();
  void updateScoreDisplay();
  void updateScoreMotor();

public:
  Mouse(MousePins p, String n);
  
  void setup();
  void input();  // Read all hardware inputs
  void update();
  
  // Motor control
  void motorStop();
  void motorForward(int speed);
  void motorReverse(int speed);
  
  // Speed control
  void setRaceSpeed(int speed);  // Set race speed (0-255)
  int getRaceSpeed() const;      // Get current race speed
  
  // LED control
  void setAllLEDs(int r, int g, int b);
  void clearAllLEDs();
  void startBlinking(int r, int g, int b, unsigned long interval);
  void stopBlinking();
  void startRunningLight();
  void stopRunningLight();
  void startScoreDisplay(int r, int g, int b, unsigned long duration);
  void addMotorTime(unsigned long additionalTime);
  
  // Switch reading
  int readHomeSwitch();
  int readWinSwitch();
  int readScore1Switch();
  int readScore2Switch();
  int readScore3Switch();
  
  // Edge detection helpers (use after input() call)
  bool homeRisingEdge();  // Detects when home switch closes (HIGH->LOW)
  bool winRisingEdge();   // Detects when win switch closes (HIGH->LOW)
  bool score1RisingEdge();
  bool score2RisingEdge();
  bool score3RisingEdge();
  
  // Movement control
  void goHome();
  bool isHome();
  
  // Test functionality
  void test_io();
};

#endif 