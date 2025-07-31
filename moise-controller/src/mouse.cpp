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
  raceSpeed = 255;  // Initialize to maximum speed
}

void Mouse::setup() {
  // Limit switches with pullup (NO) - Ground switching
  pinMode(pins.home, INPUT_PULLUP);
  pinMode(pins.win, INPUT_PULLUP);
  
  // Score buttons with pulldown (NO)
  pinMode(pins.score1, INPUT_PULLDOWN);
  pinMode(pins.score2, INPUT_PULLDOWN);
  pinMode(pins.score3, INPUT_PULLDOWN);
  
  // H-Bridge motor control pins
  pinMode(pins.motor_in1, OUTPUT);
  pinMode(pins.motor_in2, OUTPUT);
  pinMode(pins.motor_en, OUTPUT);
  motorStop();
  
  // Initialize LED strip
  strip.begin();
  strip.setBrightness(LED_BRIGHTNESS);
  strip.show();
}

void Mouse::input() {
  // Save current states to last variables
  lastHomeState = currentHomeState;
  lastWinState = currentWinState;
  lastScore1State = currentScore1State;
  lastScore2State = currentScore2State;
  lastScore3State = currentScore3State;
  
  // Read new hardware states
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
  if (TEST_IO) {
    test_io();
  } else {
    // Handle score motor timing
    if (isScoreMotor) {
      updateScoreMotor();
    }
    
    // Handle score display (highest priority)
    if (isScoreDisplay) {
      updateScoreDisplay();
    }
    // Handle blinking
    else if (isBlinking) {
      updateBlinking();
    }
    // Handle running light
    else if (isRunningLight) {
      updateRunningLight();
    }
  }
}

void Mouse::setAllLEDs(int r, int g, int b) {
  for(int i = 0; i < NUM_LEDS; i++) {
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

// Edge detection helpers
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
  // Show initial color
  for(int i = 0; i < NUM_LEDS; i++) {
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
  
  // Set colors directly (no points-to-color logic)
  scoreDisplayR = r;
  scoreDisplayG = g; 
  scoreDisplayB = b;
  
  // Show color immediately
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
  // Handle motor timing - add to existing time or start new
  if (isScoreMotor) {
    // Motor already running - add time to existing duration
    unsigned long currentTime = millis();
    unsigned long remainingTime = scoreMotorDuration - (currentTime - scoreMotorStartTime);
    scoreMotorDuration = remainingTime + additionalTime;
    scoreMotorStartTime = currentTime;  // Reset start time to now
  } else {
    // Start new motor sequence - use race speed for scoring movement
    isScoreMotor = true;
    scoreMotorStartTime = millis();
    scoreMotorDuration = additionalTime;
    motorForward(raceSpeed);  // Use race speed instead of MOTOR_SPEED
  }
}

void Mouse::updateBlinking() {
  unsigned long currentTime = millis();
  if (currentTime - lastBlinkTime >= blinkInterval) {
    blinkState = !blinkState;
    lastBlinkTime = currentTime;
    
    if (blinkState) {
      // Turn on with blink color
      for(int i = 0; i < NUM_LEDS; i++) {
        strip.setPixelColor(i, blinkR, blinkG, blinkB);
      }
    } else {
      // Turn off
      strip.clear();
    }
    strip.show();
  }
}

void Mouse::updateRunningLight() {
  unsigned long currentTime = millis();
  if (currentTime - lastRunningTime >= RUNNING_LIGHT_INTERVAL) {  // Animation interval
    lastRunningTime = currentTime;
    
    // Clear all LEDs first
    strip.clear();
    
    // Create moving pattern: 2 dim left + 2 bright center + 2 dim right
    for(int i = 0; i < NUM_LEDS; i++) {
      int brightness = 0;
      
      // Calculate distance from running position
      int distance = abs(i - runningPosition);
      
      if (distance == 0 || distance == 1) {
        // Center 2 LEDs - super bright
        brightness = LED_BRIGHTNESS_MAX;
      } else if (distance == 2 || distance == 3) {
        // Side 2+2 LEDs - dimmed
        brightness = LED_BRIGHTNESS_DIM;
      }
      
      if (brightness > 0) {
        strip.setPixelColor(i, brightness, brightness, brightness);  // White
      }
    }
    
    strip.show();
    
    // Move to next position
    runningPosition++;
    if (runningPosition >= NUM_LEDS) {
      runningPosition = 0;  // Loop back to start
    }
  }
}

void Mouse::updateScoreDisplay() {
  unsigned long currentTime = millis();
  // Use the specified duration instead of hardcoded 2000ms
  if (currentTime - scoreDisplayStartTime >= scoreDisplayDuration) {
    isScoreDisplay = false;
    // Resume running light if we were in race mode
    if (isRunningLight) {
      startRunningLight();
    }
  }
}

void Mouse::updateScoreMotor() {
  unsigned long currentTime = millis();
  // Stop motor after specified duration
  if (currentTime - scoreMotorStartTime >= scoreMotorDuration) {
    isScoreMotor = false;
    motorStop();
  }
}

void Mouse::test_io() {
  // Check for button presses using edge detection helpers
  if (homeRisingEdge()) {
    Serial.println(name + ": HOME switch pressed!");
    motorStop();
  }
  
  if (winRisingEdge()) {
    Serial.println(name + ": WIN switch pressed!");
    motorStop();
  }
  
  if (score1RisingEdge()) {
    Serial.println(name + ": SCORE 1 point!");
    motorForward(MOTOR_SPEED);
  }
  
  if (score2RisingEdge()) {
    Serial.println(name + ": SCORE 2 points!");
    motorReverse(MOTOR_SPEED);
  }
  
  if (score3RisingEdge()) {
    Serial.println(name + ": SCORE 3 points!");
    motorForward(MOTOR_SPEED);
  }
  
  // Test LED pattern

  for(int i = 0; i < NUM_LEDS; i++) {
    strip.setPixelColor(i, COLOR_RED_R); // Red for test mode
  }
  strip.show();
  
} 