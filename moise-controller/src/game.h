#ifndef GAME_H
#define GAME_H

#include <Arduino.h>
#include <Preferences.h>

class Mouse;

enum SystemMode {
  MODE_IDLE = 0,
  MODE_RUN = 1,
  MODE_DEBUG = 2
};

class Game {
private:
  Mouse* lanes[2];
  int laneCount;

  enum GameState {
    STARTUP,
    IO_CHECK,
    HOMING,
    READY,
    RACE,
    STOP,
    ERROR,
    DEBUG_STATE
  };

  GameState currentState;
  SystemMode systemMode;
  unsigned long stateStartTime;
  bool stateJustEntered;

  int raceSpeeds[2];
  int winner;
  int controllerId;
  bool ioStreamEnabled;

  unsigned long dbgMotorUntil[2];
  unsigned long identifyUntil;
  bool identifying;

  Preferences prefs;

  void changeState(GameState newState);
  void handleStartup(unsigned long currentTime);
  void handleIOCheck(unsigned long currentTime);
  void handleHoming(unsigned long currentTime);
  void handleReady(unsigned long currentTime);
  void handleRace(unsigned long currentTime);
  void handleStop(unsigned long currentTime);
  void handleError(unsigned long currentTime);
  void handleDebug(unsigned long currentTime);

  void setMouseLEDsRed();
  void setMouseLEDsWhite();
  void turnOffAllLEDs();
  void startMouseBlinking();
  void stopAllMotors();
  String checkSwitchStates();

  void sendLine(const String& body);
  void sendBootBanner();
  void loadPrefs();
  void saveId(int id);
  void saveLanes(int count);
  void applyLaneCount();
  void setSystemMode(SystemMode mode);
  void handleDebugCommand(String command);
  void dumpIo();
  void streamIoEdges();
  Mouse* laneMouse(int localLane);
  int localLaneIndex(int localLane);

public:
  Game();

  void begin(Mouse* m1, Mouse* m2);
  void setCommand(String command);
  void update();
  void onInputsUpdated();
};

#endif
