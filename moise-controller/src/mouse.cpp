#include "mouse.h"

Mouse::Mouse(MousePins p, String n)
  : pins(p), name(n), strip(NUM_LEDS, p.led, NEO_GRB + NEO_KHZ800) {
  isBlinking = false;
  blinkState = false;
  lastBlinkTime = 0;
  isRunningLight = false;
  runningPosition = 0;
  lastRunningTime = 0;
  isScoreDisplay = false;
  scoreDisplayStartTime = 0;
  scoreDisplayDuration = 0;
  scoreDisplayR = scoreDisplayG = scoreDisplayB = 0;
  isScoreMotor = false;
  scoreMotorStartTime = 0;
  scoreMotorDuration = 0;
  raceSpeed = 255;
}

void Mouse::setup() {
  pinMode(pins.home, INPUT_PULLUP);
  pinMode(pins.win, INPUT_PULLUP);

  pinMode(pins.score1, INPUT_PULLDOWN);
  pinMode(pins.score2, INPUT_PULLDOWN);
  pinMode(pins.score3, INPUT_PULLDOWN);

  pinMode(pins.motor_in1, OUTPUT);
  pinMode(pins.motor_in2, OUTPUT);
  pinMode(pins.motor_en, OUTPUT);
  motorStop();

  strip.begin();
  strip.setBrightness(LED_BRIGHTNESS);
  strip.show();
}

void Mouse::input() {
  lastHomeState = currentHomeState;
  lastWinState = currentWinState;
  lastScore1State = currentScore1State;
  lastScore2State = currentScore2State;
  lastScore3State = currentScore3State;

  currentHomeState = digitalRead(pins.home);
  currentWinState = digitalRead(pins.win);
  currentScore1State = digitalRead(pins.score1);
  currentScore2State = digitalRead(pins.score2);
  currentScore3State = digitalRead(pins.score3);
}

void Mouse::motorStop() {
  digitalWrite(pins.motor_in1, LOW);
  digitalWrite(pins.motor_in2, LOW);
  analogWrite(pins.motor_en, MOTOR_STOP);
}

void Mouse::motorForward(int speed) {
  digitalWrite(pins.motor_in1, HIGH);
  digitalWrite(pins.motor_in2, LOW);
  analogWrite(pins.motor_en, speed);
}

void Mouse::motorReverse(int speed) {
  digitalWrite(pins.motor_in1, LOW);
  digitalWrite(pins.motor_in2, HIGH);
  analogWrite(pins.motor_en, speed);
}

void Mouse::update() {
  if (isScoreMotor) {
    updateScoreMotor();
  }

  if (isScoreDisplay) {
    updateScoreDisplay();
  } else if (isBlinking) {
    updateBlinking();
  } else if (isRunningLight) {
    updateRunningLight();
  }
}

void Mouse::setAllLEDs(int r, int g, int b) {
  for (int i = 0; i < NUM_LEDS; i++) {
    strip.setPixelColor(i, r, g, b);
  }
  strip.show();
}

void Mouse::clearAllLEDs() {
  strip.clear();
  strip.show();
}

int Mouse::readHomeSwitch() { return currentHomeState; }
int Mouse::readWinSwitch() { return currentWinState; }
int Mouse::readScore1Switch() { return currentScore1State; }
int Mouse::readScore2Switch() { return currentScore2State; }
int Mouse::readScore3Switch() { return currentScore3State; }

bool Mouse::homeRisingEdge() {
  return currentHomeState == LOW && lastHomeState == HIGH;
}

bool Mouse::winRisingEdge() {
  return currentWinState == LOW && lastWinState == HIGH;
}

bool Mouse::score1RisingEdge() {
  return currentScore1State == HIGH && lastScore1State == LOW;
}

bool Mouse::score2RisingEdge() {
  return currentScore2State == HIGH && lastScore2State == LOW;
}

bool Mouse::score3RisingEdge() {
  return currentScore3State == HIGH && lastScore3State == LOW;
}

void Mouse::goHome() {
  if (!isHome()) {
    motorReverse(MOTOR_SPEED);
  }
}

bool Mouse::isHome() {
  return currentHomeState == LOW;
}

void Mouse::startBlinking(int r, int g, int b, unsigned long interval) {
  blinkR = r;
  blinkG = g;
  blinkB = b;
  blinkInterval = interval;
  isBlinking = true;
  blinkState = true;
  lastBlinkTime = millis();
  for (int i = 0; i < NUM_LEDS; i++) {
    strip.setPixelColor(i, r, g, b);
  }
  strip.show();
}

void Mouse::stopBlinking() {
  isBlinking = false;
}

void Mouse::startRunningLight() {
  isRunningLight = true;
  runningPosition = 0;
  lastRunningTime = millis();
  clearAllLEDs();
}

void Mouse::stopRunningLight() {
  isRunningLight = false;
  clearAllLEDs();
}

void Mouse::startScoreDisplay(int r, int g, int b, unsigned long duration) {
  isScoreDisplay = true;
  scoreDisplayStartTime = millis();
  scoreDisplayDuration = duration;
  scoreDisplayR = r;
  scoreDisplayG = g;
  scoreDisplayB = b;
  setAllLEDs(scoreDisplayR, scoreDisplayG, scoreDisplayB);
}

void Mouse::setRaceSpeed(int speed) {
  if (speed >= 0 && speed <= 255) {
    raceSpeed = speed;
  }
}

int Mouse::getRaceSpeed() const {
  return raceSpeed;
}

void Mouse::addMotorTime(unsigned long additionalTime) {
  if (isScoreMotor) {
    unsigned long currentTime = millis();
    unsigned long remainingTime = scoreMotorDuration - (currentTime - scoreMotorStartTime);
    scoreMotorDuration = remainingTime + additionalTime;
    scoreMotorStartTime = currentTime;
  } else {
    isScoreMotor = true;
    scoreMotorStartTime = millis();
    scoreMotorDuration = additionalTime;
    motorForward(raceSpeed);
  }
}

void Mouse::updateBlinking() {
  unsigned long currentTime = millis();
  if (currentTime - lastBlinkTime >= blinkInterval) {
    blinkState = !blinkState;
    lastBlinkTime = currentTime;

    if (blinkState) {
      for (int i = 0; i < NUM_LEDS; i++) {
        strip.setPixelColor(i, blinkR, blinkG, blinkB);
      }
    } else {
      strip.clear();
    }
    strip.show();
  }
}

void Mouse::updateRunningLight() {
  unsigned long currentTime = millis();
  if (currentTime - lastRunningTime >= RUNNING_LIGHT_INTERVAL) {
    lastRunningTime = currentTime;
    strip.clear();

    int brightnessPattern[10] = {20, 60, 120, 200, 255, 255, 200, 120, 60, 20};

    for (int i = 0; i < NUM_LEDS; i++) {
      int patternIndex = (i + runningPosition) % 10;
      int brightness = brightnessPattern[patternIndex];
      strip.setPixelColor(i, brightness, brightness, brightness);
    }

    strip.show();
    runningPosition++;
    if (runningPosition >= 10) {
      runningPosition = 0;
    }
  }
}

void Mouse::updateScoreDisplay() {
  unsigned long currentTime = millis();
  if (currentTime - scoreDisplayStartTime >= scoreDisplayDuration) {
    isScoreDisplay = false;
    if (isRunningLight) {
      startRunningLight();
    }
  }
}

void Mouse::updateScoreMotor() {
  unsigned long currentTime = millis();
  if (currentTime - scoreMotorStartTime >= scoreMotorDuration) {
    isScoreMotor = false;
    motorStop();
  }
}
