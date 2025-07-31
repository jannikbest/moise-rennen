#include "game.h"
#include "mouse.h"
#include "config.h"

Game::Game() : mouse1(nullptr), mouse2(nullptr), currentState(STARTUP), stateStartTime(0), stateJustEntered(true), mouse1Homing(false), mouse2Homing(false) {
  winner = 0;
  // Initialize reference time tracking
  mouse1ReferenceTime = 0;
  mouse2ReferenceTime = 0;
  referenceRunStartTime = 0;
  mouse1ReferenceRunning = false;
  mouse2ReferenceRunning = false;
  // Initialize race speeds to maximum (255)
  mouse1RaceSpeed = 255;
  mouse2RaceSpeed = 255;
  // Initialize simulation scores
  mouse1Score = 0;
  mouse2Score = 0;
}

void Game::registerMouse1(Mouse* m) {
  mouse1 = m;
  // Set initial race speed
  if (mouse1) {
    mouse1->setRaceSpeed(mouse1RaceSpeed);
  }
}

void Game::registerMouse2(Mouse* m) {
  mouse2 = m;
  // Set initial race speed
  if (mouse2) {
    mouse2->setRaceSpeed(mouse2RaceSpeed);
  }
}

void Game::setCommand(String command) {
  // Process commands - no logging, serial is for host communication
  if (command == "go") {
    if (currentState == READY) {
      changeState(RACE);
    } else {
      Serial.println("Error: Invalid state");
    }
  }
  else if (command == "home") {
    changeState(HOMING);
  }
  else if (command == "lose") {
    // External game over - another controller won
    stopAllMotors();
    turnOffAllLEDs();
    winner = 0;  // No local winner
    changeState(STOP);
  }
  else if (command == "reset") {
    // Stop both mouse motors
    if (mouse1) mouse1->motorStop();
    if (mouse2) mouse2->motorStop();
    
    // Reset to IO_CHECK state
    changeState(IO_CHECK);
  }
  else if (command == "ready?") {
    // Query if system is in READY state
    if (currentState == READY) {
      Serial.println("ready");
    } else if (currentState == ERROR) {
      Serial.println("error");
    } else {
      Serial.println("no");
    }
  }
  else if (command.startsWith("speed1 ")) {
    // Set mouse 1 race speed: "speed1 200"
    int speed = command.substring(7).toInt();
    if (speed >= 0 && speed <= 255) {
      mouse1RaceSpeed = speed;
      // Update mouse object immediately
      if (mouse1) {
        mouse1->setRaceSpeed(speed);
      }
    } else {
      Serial.println("Error: Speed must be 0-255");
    }
  }
  else if (command.startsWith("speed2 ")) {
    // Set mouse 2 race speed: "speed2 150"
    int speed = command.substring(7).toInt();
    if (speed >= 0 && speed <= 255) {
      mouse2RaceSpeed = speed;
      // Update mouse object immediately
      if (mouse2) {
        mouse2->setRaceSpeed(speed);
      }
    } else {
      Serial.println("Error: Speed must be 0-255");
    }
  }
  else {
    Serial.print("Error: Invalid command: ");
    Serial.println(command);
  }
}

void Game::update() {
  if (TEST_IO) {
    return;
  }
  
  #if TEST_STATE_MACHINE
  // Call simulation function for state machine testing
  simulateStateMachine();
  return;
  #endif
  
  unsigned long currentTime = millis();
  
  switch (currentState) {
    case STARTUP:
      handleStartup(currentTime);
      break;
    case IO_CHECK:
      handleIOCheck(currentTime);
      break;
    case HOMING:
      handleHoming(currentTime);
      break;
    case REFERENCE_RUN:
      handleReferenceRun(currentTime);
      break;
    case READY:
      handleReady(currentTime);
      break;
    case RACE:
      handleRace(currentTime);
      break;
    case STOP:
      handleStop(currentTime);
      break;
    case ERROR:
      handleError(currentTime);
      break;
  }
}

void Game::changeState(GameState newState) {
  currentState = newState;
  stateStartTime = millis();
  stateJustEntered = true;
}

void Game::handleStartup(unsigned long currentTime) {
  // Set both mice LEDs to red on state entry
  if (stateJustEntered) {
    setMouseLEDsRed();
    stateJustEntered = false;
  }
  
  // Wait for startup duration, then go to IO check
  if (currentTime - stateStartTime >= STARTUP_DURATION) {
    changeState(IO_CHECK);
  }
}

void Game::handleIOCheck(unsigned long currentTime) {
  // Check switch states and get detailed error info
  String errorMessage = checkSwitchStates();
  
  if (errorMessage != "") {
    Serial.println(errorMessage);
    changeState(ERROR);
    return;
  }
  
  // IO check passed, start homing
  changeState(HOMING);
}

void Game::handleHoming(unsigned long currentTime) {
  // Start blinking and motors on state entry
  if (stateJustEntered) {
    startMouseBlinking();
    startHomingSequence();
    stateJustEntered = false;
  }
  
  // Check each mouse individually and stop when home
  if (mouse1Homing && mouse1->isHome()) {
    mouse1->motorStop();
    mouse1Homing = false;
  }
  
  if (mouse2Homing && mouse2->isHome()) {
    mouse2->motorStop();
    mouse2Homing = false;
  }
  
  // Check if both mice are home
  if (mouse1->isHome() && mouse2->isHome()) {
    mouse1->stopBlinking();
    mouse2->stopBlinking();
    
    // Check if we need to do reference run (only if not in test mode and reference time missing)
    #if !TEST_AUTO_RACE
    if (mouse1ReferenceTime == 0 || mouse2ReferenceTime == 0) {
      changeState(REFERENCE_RUN);
    } else {
      setMouseLEDsWhite();
      changeState(READY);
    }
    #else
    // In test mode, skip reference run and go directly to READY
    setMouseLEDsWhite();
    changeState(READY);
    #endif
  }
}

void Game::handleReferenceRun(unsigned long currentTime) {
  // Set blue LEDs and start reference run on state entry
  if (stateJustEntered) {
    setMouseLEDsBlue();
    startReferenceRun();
    stateJustEntered = false;
  }
  
  // Check for win switch hits to measure reference times
  if (mouse1ReferenceRunning && mouse1->readWinSwitch() == HIGH) {
    // Mouse 1 reached the end - record time
    mouse1ReferenceTime = currentTime - referenceRunStartTime;
    mouse1->motorStop();
    mouse1ReferenceRunning = false;
    Serial.print("M1 reference time: ");
    Serial.print(mouse1ReferenceTime);
    Serial.println("ms");
  }
  
  if (mouse2ReferenceRunning && mouse2->readWinSwitch() == HIGH) {
    // Mouse 2 reached the end - record time
    mouse2ReferenceTime = currentTime - referenceRunStartTime;
    mouse2->motorStop();
    mouse2ReferenceRunning = false;
    Serial.print("M2 reference time: ");
    Serial.print(mouse2ReferenceTime);
    Serial.println("ms");
  }
  
  // Check if both mice have completed their reference runs
  if (!mouse1ReferenceRunning && !mouse2ReferenceRunning) {
    // Both mice finished - return to homing
    changeState(HOMING);
  }
}

void Game::handleReady(unsigned long currentTime) {
  // Send ready message on state entry
  if (stateJustEntered) {
    Serial.println("ready");
    stateJustEntered = false;
  }
  
  // Auto-start race after delay in test mode
  #if TEST_AUTO_RACE
  if (currentTime - stateStartTime >= AUTO_RACE_DELAY) {
    changeState(RACE);
  }
  #endif
  
  // Ready state - waiting for game start
}

void Game::handleRace(unsigned long currentTime) {
  // Start running light animation on state entry
  if (stateJustEntered) {
    if (mouse1) {
      mouse1->stopBlinking();
      mouse1->startRunningLight();
    }
    if (mouse2) {
      mouse2->stopBlinking();
      mouse2->startRunningLight();
    }
    stateJustEntered = false;
  }
  
  // Check for score button presses
  if (mouse1 && mouse2) {
    // Check WIN switches first - game ending condition
    if (mouse1->readWinSwitch() == LOW) {
      // Mouse 1 wins!
      winner = 1;
      Serial.println("win1");
      changeState(STOP);
      return;  // Exit race handling
    }
    
    if (mouse2->readWinSwitch() == LOW) {
      // Mouse 2 wins!
      winner = 2;
      Serial.println("win2");
      changeState(STOP);
      return;  // Exit race handling
    }
    
    // Mouse 1 score buttons - Game controls all score logic
    if (mouse1->score1RisingEdge()) {
      // 1 point = Green color + motor time + display
      mouse1->startScoreDisplay(COLOR_1PT_R, SCORE_DISPLAY_DURATION);
      mouse1->addMotorTime(SCORE_1PT_MOTOR_TIME);
      Serial.println("11");
    }
    if (mouse1->score2RisingEdge()) {
      // 2 points = Blue color + motor time + display
      mouse1->startScoreDisplay(COLOR_2PT_R, SCORE_DISPLAY_DURATION);
      mouse1->addMotorTime(SCORE_2PT_MOTOR_TIME);
      Serial.println("12");
    }
    if (mouse1->score3RisingEdge()) {
      // 3 points = Red color + motor time + display
      mouse1->startScoreDisplay(COLOR_3PT_R, SCORE_DISPLAY_DURATION);
      mouse1->addMotorTime(SCORE_3PT_MOTOR_TIME);
      Serial.println("13");
    }
    
    // Mouse 2 score buttons - Game controls all score logic
    if (mouse2->score1RisingEdge()) {
      // 1 point = Green color + motor time + display
      mouse2->startScoreDisplay(COLOR_1PT_R, SCORE_DISPLAY_DURATION);
      mouse2->addMotorTime(SCORE_1PT_MOTOR_TIME);
      Serial.println("21");
    }
    if (mouse2->score2RisingEdge()) {
      // 2 points = Blue color + motor time + display
      mouse2->startScoreDisplay(COLOR_2PT_R, SCORE_DISPLAY_DURATION);
      mouse2->addMotorTime(SCORE_2PT_MOTOR_TIME);
      Serial.println("22");
    }
    if (mouse2->score3RisingEdge()) {
      // 3 points = Red color + motor time + display
      mouse2->startScoreDisplay(COLOR_3PT_R, SCORE_DISPLAY_DURATION);
      mouse2->addMotorTime(SCORE_3PT_MOTOR_TIME);
      Serial.println("23");
    }
  }
  
  // Race state - mice are racing to the finish line
}

void Game::handleStop(unsigned long currentTime) {
  // Set winner/loser LED effects on state entry
  if (stateJustEntered) {
    // Stop all motors first - ensure everything is stopped
    stopAllMotors();
    
    if (winner == 1) {
      // Mouse 1 wins - fast red blinking, Mouse 2 off
      mouse1->stopRunningLight();
      mouse1->startBlinking(COLOR_RED_R, WINNER_BLINK_INTERVAL);  // Fast red blink
      mouse2->stopRunningLight();
      mouse2->clearAllLEDs();
    } else if (winner == 2) {
      // Mouse 2 wins - fast red blinking, Mouse 1 off
      mouse2->stopRunningLight();
      mouse2->startBlinking(COLOR_RED_R, WINNER_BLINK_INTERVAL);  // Fast red blink
      mouse1->stopRunningLight();
      mouse1->clearAllLEDs();
    }
    stateJustEntered = false;
  }
  
  // Auto-return to homing after delay in test mode
  #if TEST_AUTO_RACE
  if (currentTime - stateStartTime >= AUTO_RETURN_DELAY) {
    winner = 0;  // Reset winner for new game
    changeState(HOMING);
  }
  #endif
  
  // Stay in STOP state - game is over
}

void Game::handleError(unsigned long currentTime) {
  // Error state - stay here until reset
}


void Game::setMouseLEDsRed() {
  if (mouse1) {
    mouse1->setAllLEDs(COLOR_RED_R);  // Red
  }
  if (mouse2) {
    mouse2->setAllLEDs(COLOR_RED_R);  // Red
  }
}

void Game::setMouseLEDsWhite() {
  if (mouse1) {
    mouse1->setAllLEDs(COLOR_WHITE_R);  // White
  }
  if (mouse2) {
    mouse2->setAllLEDs(COLOR_WHITE_R);  // White
  }
}

void Game::turnOffAllLEDs() {
  if (mouse1) {
    mouse1->clearAllLEDs();
  }
  if (mouse2) {
    mouse2->clearAllLEDs();
  }
}

void Game::startMouseBlinking() {
  if (mouse1) {
    mouse1->startBlinking(COLOR_WHITE_R, HOMING_BLINK_INTERVAL);  // White, 1Hz
  }
  if (mouse2) {
    mouse2->startBlinking(COLOR_WHITE_R, HOMING_BLINK_INTERVAL);  // White, 1Hz
  }
}

void Game::startHomingSequence() {
  mouse1Homing = true;
  mouse2Homing = true;
  
  if (mouse1) {
    mouse1->goHome();
  }
  if (mouse2) {
    mouse2->goHome();
  }
}

void Game::stopAllMotors() {
  if (mouse1) mouse1->motorStop();
  if (mouse2) mouse2->motorStop();
}

String Game::checkSwitchStates() {
  if (!mouse1 || !mouse2) return "ERROR: Mice not registered";
  
  // Read current switch states
  int m1_home = mouse1->readHomeSwitch();
  int m1_win = mouse1->readWinSwitch();
  int m1_score1 = mouse1->readScore1Switch();
  int m1_score2 = mouse1->readScore2Switch();
  int m1_score3 = mouse1->readScore3Switch();
  
  int m2_home = mouse2->readHomeSwitch();
  int m2_win = mouse2->readWinSwitch();
  int m2_score1 = mouse2->readScore1Switch();
  int m2_score2 = mouse2->readScore2Switch();
  int m2_score3 = mouse2->readScore3Switch();
  
  // Check Mouse 1 score buttons (should be LOW/off)
  if (m1_score1 == HIGH) {
    return "ERROR: Mouse 1 Score1 button pressed (is HIGH, should be LOW)";
  }
  if (m1_score2 == HIGH) {
    return "ERROR: Mouse 1 Score2 button pressed (is HIGH, should be LOW)";
  }
  if (m1_score3 == HIGH) {
    return "ERROR: Mouse 1 Score3 button pressed (is HIGH, should be LOW)";
  }
  
  // Check Mouse 2 score buttons (should be LOW/off)
  if (m2_score1 == HIGH) {
    return "ERROR: Mouse 2 Score1 button pressed (is HIGH, should be LOW)";
  }
  if (m2_score2 == HIGH) {
    return "ERROR: Mouse 2 Score2 button pressed (is HIGH, should be LOW)";
  }
  if (m2_score3 == HIGH) {
    return "ERROR: Mouse 2 Score3 button pressed (is HIGH, should be LOW)";
  }
  
  // Check that both win switches are not pressed at the same time
  if (m1_win == LOW && m2_win == LOW) {
    return "ERROR: Both win switches pressed (Mouse 1 and Mouse 2 win switches are HIGH, only one should be HIGH at a time)";
  }
  
  return "";  // No error
} 

void Game::setMouseLEDsBlue() {
  if (mouse1) {
    mouse1->setAllLEDs(COLOR_BLUE_R);  // Blue
  }
  if (mouse2) {
    mouse2->setAllLEDs(COLOR_BLUE_R);  // Blue
  }
}

void Game::startReferenceRun() {
  referenceRunStartTime = millis();
  
  // Start only mice that need reference measurement
  if (mouse1ReferenceTime == 0) {
    mouse1ReferenceRunning = true;
    if (mouse1) {
      mouse1->motorForward(255);  // Maximum speed
    }
  }
  
  if (mouse2ReferenceTime == 0) {
    mouse2ReferenceRunning = true;
    if (mouse2) {
      mouse2->motorForward(255);  // Maximum speed
    }
  }
} 

int Game::getMouse1RaceSpeed() const {
  return mouse1RaceSpeed;
}

int Game::getMouse2RaceSpeed() const {
  return mouse2RaceSpeed;
}

// ===== SIMULATION FUNCTION =====

void Game::simulateStateMachine() {
  unsigned long currentTime = millis();
  
  switch (currentState) {
    case STARTUP:
      if (stateJustEntered) {
        stateJustEntered = false;
        // Calculate random delay for startup (2-3 seconds)
        stateTransitionDelay = 2000 + random(1000);
      }
      
      // Random delay between 2-3 seconds before going to HOMING
      if (currentTime - stateStartTime >= stateTransitionDelay) {
        changeState(HOMING);
      }
      break;
    case IO_CHECK:
      break;
    case HOMING:
      if (stateJustEntered) {
        stateJustEntered = false;
        // Calculate random delay for homing (4-6 seconds)
        stateTransitionDelay = 4000 + random(2000);
      }
      
      // Homing takes 4-6 seconds, then go to READY
      if (currentTime - stateStartTime >= stateTransitionDelay) {
        changeState(READY);
      }
      break;
    case REFERENCE_RUN:
      break;
    case READY:
      if (stateJustEntered) {
        Serial.println("ready");
        stateJustEntered = false;
      }
      break;
    case RACE:
      if (stateJustEntered) {
        stateJustEntered = false;
        mouse1Score = 0;
        mouse2Score = 0;
        // Calculate random delay for next score event (2-3 seconds)
        stateTransitionDelay = 2000 + random(1000);
      }
      
      // Every 2-3 seconds, give random points to a random mouse
      if (currentTime - stateStartTime >= stateTransitionDelay) {
        // Randomly choose mouse (1 or 2)
        int mouse = random(1, 3);  // 1 or 2
        // Randomly choose points (1, 2, or 3)
        int points = random(1, 4);  // 1, 2, or 3
        
        // Add points to the chosen mouse
        if (mouse == 1) {
          mouse1Score += points;
        } else {
          mouse2Score += points;
        }
        
        // Send score message over serial
        Serial.print(mouse);
        Serial.println(points);
        
        // Check for winner (>10 points)
        if (mouse1Score > 10) {
          winner = 1;
          Serial.println("win1");
          changeState(STOP);
          return;
        } else if (mouse2Score > 10) {
          winner = 2;
          Serial.println("win2");
          changeState(STOP);
          return;
        }
        
        // Reset timer for next score event
        stateStartTime = currentTime;
        stateTransitionDelay = 2000 + random(1000);
      }
      break;
    case STOP:
      break;
    case ERROR:
      handleError(currentTime);
      break;
  }
} 