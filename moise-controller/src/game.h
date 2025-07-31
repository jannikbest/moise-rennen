#ifndef GAME_H
#define GAME_H

#include <Arduino.h>

// Forward declaration
class Mouse;

// Game class
class Game {
private:
  Mouse* mouse1;
  Mouse* mouse2;
  
  // State machine
  enum GameState {
    STARTUP,
    IO_CHECK,
    HOMING,
    REFERENCE_RUN,  // New state for measuring reference times
    READY,          // Renamed from IDLE
    RACE,
    STOP,
    ERROR
  };
  
  GameState currentState;
  unsigned long stateStartTime;
  bool stateJustEntered;
  
  // Homing state tracking
  bool mouse1Homing;
  bool mouse2Homing;
  
  // Reference run tracking
  unsigned long mouse1ReferenceTime;  // Reference time in ms (0 = not measured)
  unsigned long mouse2ReferenceTime;  // Reference time in ms (0 = not measured)
  unsigned long referenceRunStartTime;  // When reference run started
  bool mouse1ReferenceRunning;  // Is mouse1 currently doing reference run
  bool mouse2ReferenceRunning;  // Is mouse2 currently doing reference run
  
  // Race speed tracking (only for race mode, not homing/reference)
  int mouse1RaceSpeed;  // Max speed for mouse1 during race (0-255)
  int mouse2RaceSpeed;  // Max speed for mouse2 during race (0-255)
  
  // Winner tracking
  int winner;  // 0 = no winner, 1 = mouse1, 2 = mouse2
  
  // State transition timing
  unsigned long stateTransitionDelay;  // Calculated delay for current state
  
  // Score tracking for simulation
  int mouse1Score;  // Current score for mouse 1
  int mouse2Score;  // Current score for mouse 2
  
public:
  Game();
  
  void registerMouse1(Mouse* m);
  void registerMouse2(Mouse* m);
  void setCommand(String command);
  void update();
  
  // Speed control
  int getMouse1RaceSpeed() const;
  int getMouse2RaceSpeed() const;
  
private:
  void changeState(GameState newState);
  void handleStartup(unsigned long currentTime);
  void handleIOCheck(unsigned long currentTime);
  void handleHoming(unsigned long currentTime);
  void handleReferenceRun(unsigned long currentTime);  // New handler
  void handleReady(unsigned long currentTime);  // Renamed from handleIdle
  void handleRace(unsigned long currentTime);
  void handleStop(unsigned long currentTime);
  void handleError(unsigned long currentTime);
  
  // Simulation function for state machine testing
  void simulateStateMachine();
  
  void setMouseLEDsRed();
  void setMouseLEDsWhite();
  void setMouseLEDsBlue();  // New method for reference run
  void turnOffAllLEDs();
  void startMouseBlinking();
  void startHomingSequence();
  void startReferenceRun();  // New method for reference run
  void stopAllMotors();
  String checkSwitchStates();
};

#endif 