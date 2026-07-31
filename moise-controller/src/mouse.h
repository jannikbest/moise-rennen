#ifndef MOUSE_H
#define MOUSE_H

#include <Arduino.h>
#include <Adafruit_NeoPixel.h>
#include "config.h"

class Mouse {
private:
  MousePins pins;
  String name;

  const int NUM_LEDS = 63;
  const int LED_BRIGHTNESS = 20;
  const int MOTOR_SPEED = 255;
  const int MOTOR_STOP = 0;

  Adafruit_NeoPixel strip;
  int raceSpeed;

  int lastHomeState = HIGH;
  int lastWinState = HIGH;
  int lastScore1State = LOW;
  int lastScore2State = LOW;
  int lastScore3State = LOW;

  int currentHomeState = HIGH;
  int currentWinState = HIGH;
  int currentScore1State = LOW;
  int currentScore2State = LOW;
  int currentScore3State = LOW;

  bool isBlinking;
  int blinkR, blinkG, blinkB;
  unsigned long blinkInterval;
  unsigned long lastBlinkTime;
  bool blinkState;

  bool isRunningLight;
  int runningPosition;
  unsigned long lastRunningTime;

  bool isScoreDisplay;
  unsigned long scoreDisplayStartTime;
  unsigned long scoreDisplayDuration;
  int scoreDisplayR, scoreDisplayG, scoreDisplayB;

  bool isScoreMotor;
  unsigned long scoreMotorStartTime;
  unsigned long scoreMotorDuration;

  void updateBlinking();
  void updateRunningLight();
  void updateScoreDisplay();
  void updateScoreMotor();

public:
  Mouse(MousePins p, String n);

  void setup();
  void input();
  void update();

  void motorStop();
  void motorForward(int speed);
  void motorReverse(int speed);

  void setRaceSpeed(int speed);
  int getRaceSpeed() const;

  void setAllLEDs(int r, int g, int b);
  void clearAllLEDs();
  void startBlinking(int r, int g, int b, unsigned long interval);
  void stopBlinking();
  void startRunningLight();
  void stopRunningLight();
  void startScoreDisplay(int r, int g, int b, unsigned long duration);
  void addMotorTime(unsigned long additionalTime);

  int readHomeSwitch();
  int readWinSwitch();
  int readScore1Switch();
  int readScore2Switch();
  int readScore3Switch();

  bool homeRisingEdge();
  bool winRisingEdge();
  bool score1RisingEdge();
  bool score2RisingEdge();
  bool score3RisingEdge();

  void goHome();
  bool isHome();
};

#endif
