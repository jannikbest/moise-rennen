#include "game.h"
#include "mouse.h"
#include "config.h"

Game::Game()
  : laneCount(2),
    currentState(STARTUP),
    systemMode(MODE_IDLE),
    stateStartTime(0),
    stateJustEntered(true),
    winner(0),
    raceId(0),
    raceStartMs(0),
    raceDurationMs(0),
    controllerId(0),
    ioStreamEnabled(false),
    identifyUntil(0),
    identifying(false) {
  lanes[0] = nullptr;
  lanes[1] = nullptr;
  raceSpeeds[0] = 255;
  raceSpeeds[1] = 255;
  points[0] = 0;
  points[1] = 0;
  dbgMotorUntil[0] = 0;
  dbgMotorUntil[1] = 0;
}

void Game::begin(Mouse* m1, Mouse* m2) {
  lanes[0] = m1;
  lanes[1] = m2;
  loadPrefs();
  applyLaneCount();

  if (lanes[0]) lanes[0]->setRaceSpeed(raceSpeeds[0]);
  if (lanes[1]) lanes[1]->setRaceSpeed(raceSpeeds[1]);

  sendBootBanner();

  if (controllerId == 0) {
    systemMode = MODE_IDLE;
    changeState(DEBUG_STATE);
    sendLine("st idle");
  } else {
    systemMode = MODE_RUN;
    changeState(STARTUP);
    sendLine("st startup");
  }
}

void Game::loadPrefs() {
  prefs.begin("moise", true);
  controllerId = prefs.getInt("id", 0);
  laneCount = prefs.getInt("lanes", 2);
  prefs.end();
  if (laneCount < 1) laneCount = 1;
  if (laneCount > 2) laneCount = 2;
}

void Game::saveId(int id) {
  controllerId = id;
  prefs.begin("moise", false);
  prefs.putInt("id", controllerId);
  prefs.end();
}

void Game::saveLanes(int count) {
  if (count < 1) count = 1;
  if (count > 2) count = 2;
  laneCount = count;
  prefs.begin("moise", false);
  prefs.putInt("lanes", laneCount);
  prefs.end();
  applyLaneCount();
}

void Game::applyLaneCount() {
  // Physical mice always exist; laneCount limits which ones participate in run mode.
}

void Game::sendLine(const String& body) {
  Serial.print('#');
  Serial.println(body);
}

void Game::sendBootBanner() {
  String line = "rdy id=";
  line += controllerId;
  line += " lanes=";
  line += laneCount;
  line += " fw=";
  line += FIRMWARE_VERSION;
  sendLine(line);
}

Mouse* Game::laneMouse(int localLane) {
  int idx = localLaneIndex(localLane);
  if (idx < 0) return nullptr;
  return lanes[idx];
}

int Game::localLaneIndex(int localLane) {
  if (localLane < 1 || localLane > laneCount) return -1;
  return localLane - 1;
}

void Game::setSystemMode(SystemMode mode) {
  systemMode = mode;
  stopAllMotors();
  ioStreamEnabled = false;

  if (mode == MODE_RUN) {
    if (controllerId == 0) {
      sendLine("err no_id Controller has no ID");
      systemMode = MODE_IDLE;
      changeState(DEBUG_STATE);
      sendLine("mode idle");
      return;
    }
    changeState(STARTUP);
    sendLine("mode run");
    sendLine("st startup");
  } else if (mode == MODE_DEBUG) {
    changeState(DEBUG_STATE);
    sendLine("mode debug");
    sendLine("st debug");
  } else {
    changeState(DEBUG_STATE);
    sendLine("mode idle");
    sendLine("st idle");
  }
}

void Game::setCommand(String command) {
  command.trim();
  if (command.length() == 0) return;

  if (command == "id?") {
    sendLine(String("id ") + controllerId);
    return;
  }
  if (command.startsWith("id ")) {
    int id = command.substring(3).toInt();
    if (id < 0) id = 0;
    saveId(id);
    sendLine(String("id ") + controllerId);
    return;
  }
  if (command == "lanes?") {
    sendLine(String("lanes ") + laneCount);
    return;
  }
  if (command.startsWith("lanes ")) {
    int count = command.substring(6).toInt();
    saveLanes(count);
    sendLine(String("lanes ") + laneCount);
    return;
  }
  if (command == "mode?") {
    if (systemMode == MODE_RUN) sendLine("mode run");
    else if (systemMode == MODE_DEBUG) sendLine("mode debug");
    else sendLine("mode idle");
    return;
  }
  if (command.startsWith("mode ")) {
    String m = command.substring(5);
    m.trim();
    if (m == "run") setSystemMode(MODE_RUN);
    else if (m == "debug") setSystemMode(MODE_DEBUG);
    else if (m == "idle") setSystemMode(MODE_IDLE);
    else sendLine("err bad_mode Unknown mode");
    return;
  }
  if (command == "identify") {
    identifying = true;
    identifyUntil = millis() + IDENTIFY_DURATION_MS;
    for (int i = 0; i < laneCount; i++) {
      if (lanes[i]) lanes[i]->startBlinking(0, 255, 255, 150);
    }
    sendLine("st identify");
    return;
  }

  if (systemMode == MODE_DEBUG || command.startsWith("dbg ")) {
    handleDebugCommand(command);
    return;
  }

  if (systemMode != MODE_RUN) {
    sendLine("err wrong_mode Command requires run mode");
    return;
  }

  if (command == "go") {
    if (currentState == READY) {
      changeState(RACE);
    } else {
      sendLine("err bad_state Invalid state for go");
    }
  } else if (command == "home") {
    changeState(HOMING);
  } else if (command == "lose") {
    stopAllMotors();
    for (int i = 0; i < laneCount; i++) {
      if (!lanes[i]) continue;
      lanes[i]->stopRunningLight();
      lanes[i]->startBlinking(255, 0, 0, WINNER_BLINK_INTERVAL);
    }
    winner = 0;
    changeState(STOP);
  } else if (command == "reset") {
    stopAllMotors();
    changeState(IO_CHECK);
  } else if (command == "ready?") {
    if (currentState == READY) sendLine("ready");
    else if (currentState == ERROR) sendLine("error");
    else sendLine("no");
  } else if (command.startsWith("speed ")) {
    // speed <lane> <0-255>
    int space = command.indexOf(' ', 6);
    if (space < 0) {
      sendLine("err bad_cmd speed <lane> <0-255>");
      return;
    }
    int localLane = command.substring(6, space).toInt();
    int speed = command.substring(space + 1).toInt();
    int idx = localLaneIndex(localLane);
    if (idx < 0 || speed < 0 || speed > 255) {
      sendLine("err bad_speed Invalid lane or speed");
      return;
    }
    raceSpeeds[idx] = speed;
    if (lanes[idx]) lanes[idx]->setRaceSpeed(speed);
  } else {
    sendLine(String("err bad_cmd Invalid command: ") + command);
  }
}

void Game::handleDebugCommand(String command) {
  if (systemMode != MODE_DEBUG && !command.startsWith("dbg ")) {
    // allow dbg commands only after mode debug; identify/id already handled
  }
  if (systemMode != MODE_DEBUG) {
    sendLine("err wrong_mode Debug command requires debug mode");
    return;
  }

  if (command == "dbg io?") {
    dumpIo();
    return;
  }
  if (command == "dbg stream on") {
    ioStreamEnabled = true;
    sendLine("dbg stream on");
    return;
  }
  if (command == "dbg stream off") {
    ioStreamEnabled = false;
    sendLine("dbg stream off");
    return;
  }
  if (command.startsWith("dbg motor ")) {
    // dbg motor <lane> fwd|rev|stop [ms]
    String rest = command.substring(10);
    rest.trim();
    int sp1 = rest.indexOf(' ');
    if (sp1 < 0) {
      sendLine("err bad_cmd dbg motor <lane> fwd|rev|stop [ms]");
      return;
    }
    int localLane = rest.substring(0, sp1).toInt();
    String actionRest = rest.substring(sp1 + 1);
    actionRest.trim();
    int sp2 = actionRest.indexOf(' ');
    String action = sp2 < 0 ? actionRest : actionRest.substring(0, sp2);
    unsigned long ms = DBG_MOTOR_DEFAULT_MS;
    if (sp2 >= 0) {
      ms = actionRest.substring(sp2 + 1).toInt();
      if (ms == 0) ms = DBG_MOTOR_DEFAULT_MS;
      if (ms > DBG_MOTOR_MAX_MS) ms = DBG_MOTOR_MAX_MS;
    }
    int idx = localLaneIndex(localLane);
    Mouse* m = laneMouse(localLane);
    if (!m || idx < 0) {
      sendLine("err bad_lane Invalid lane");
      return;
    }
    if (action == "stop") {
      m->motorStop();
      dbgMotorUntil[idx] = 0;
    } else if (action == "fwd") {
      m->motorForward(255);
      dbgMotorUntil[idx] = millis() + ms;
    } else if (action == "rev") {
      m->motorReverse(255);
      dbgMotorUntil[idx] = millis() + ms;
    } else {
      sendLine("err bad_cmd dbg motor action");
    }
    return;
  }
  if (command.startsWith("dbg led ")) {
    // dbg led <lane> on|off|<r,g,b>
    String rest = command.substring(8);
    rest.trim();
    int sp1 = rest.indexOf(' ');
    if (sp1 < 0) {
      sendLine("err bad_cmd dbg led <lane> on|off|r,g,b");
      return;
    }
    int localLane = rest.substring(0, sp1).toInt();
    String arg = rest.substring(sp1 + 1);
    arg.trim();
    Mouse* m = laneMouse(localLane);
    if (!m) {
      sendLine("err bad_lane Invalid lane");
      return;
    }
    m->stopBlinking();
    m->stopRunningLight();
    if (arg == "on") {
      m->setAllLEDs(255, 255, 255);
    } else if (arg == "off") {
      m->clearAllLEDs();
    } else {
      int c1 = arg.indexOf(',');
      int c2 = arg.indexOf(',', c1 + 1);
      if (c1 < 0 || c2 < 0) {
        sendLine("err bad_cmd dbg led color");
        return;
      }
      int r = arg.substring(0, c1).toInt();
      int g = arg.substring(c1 + 1, c2).toInt();
      int b = arg.substring(c2 + 1).toInt();
      m->setAllLEDs(r, g, b);
    }
    return;
  }

  sendLine(String("err bad_cmd Invalid debug command: ") + command);
}

void Game::dumpIo() {
  for (int i = 0; i < laneCount; i++) {
    if (!lanes[i]) continue;
    int lane = i + 1;
    sendLine(String("evt io ") + lane + " home " + (lanes[i]->readHomeSwitch() == LOW ? 1 : 0));
    sendLine(String("evt io ") + lane + " win " + (lanes[i]->readWinSwitch() == LOW ? 1 : 0));
    sendLine(String("evt io ") + lane + " s1 " + (lanes[i]->readScore1Switch() == HIGH ? 1 : 0));
    sendLine(String("evt io ") + lane + " s2 " + (lanes[i]->readScore2Switch() == HIGH ? 1 : 0));
    sendLine(String("evt io ") + lane + " s3 " + (lanes[i]->readScore3Switch() == HIGH ? 1 : 0));
  }
}

void Game::streamIoEdges() {
  if (!ioStreamEnabled) return;
  for (int i = 0; i < laneCount; i++) {
    if (!lanes[i]) continue;
    int lane = i + 1;
    if (lanes[i]->homeRisingEdge()) {
      sendLine(String("evt io ") + lane + " home 1");
    }
    if (lanes[i]->winRisingEdge()) {
      sendLine(String("evt io ") + lane + " win 1");
    }
    if (lanes[i]->score1RisingEdge()) {
      sendLine(String("evt io ") + lane + " s1 1");
    }
    if (lanes[i]->score2RisingEdge()) {
      sendLine(String("evt io ") + lane + " s2 1");
    }
    if (lanes[i]->score3RisingEdge()) {
      sendLine(String("evt io ") + lane + " s3 1");
    }
  }
}

void Game::onInputsUpdated() {
  if (systemMode == MODE_DEBUG) {
    streamIoEdges();
  }
}

void Game::update() {
  unsigned long currentTime = millis();

  if (identifying && currentTime >= identifyUntil) {
    identifying = false;
    for (int i = 0; i < laneCount; i++) {
      if (lanes[i]) {
        lanes[i]->stopBlinking();
        lanes[i]->clearAllLEDs();
      }
    }
  }

  if (systemMode == MODE_DEBUG || systemMode == MODE_IDLE) {
    handleDebug(currentTime);
    return;
  }

  switch (currentState) {
    case STARTUP: handleStartup(currentTime); break;
    case IO_CHECK: handleIOCheck(currentTime); break;
    case HOMING: handleHoming(currentTime); break;
    case READY: handleReady(currentTime); break;
    case RACE: handleRace(currentTime); break;
    case STOP: handleStop(currentTime); break;
    case ERROR: handleError(currentTime); break;
    case DEBUG_STATE: handleDebug(currentTime); break;
  }
}

void Game::changeState(GameState newState) {
  currentState = newState;
  stateStartTime = millis();
  stateJustEntered = true;
}

void Game::handleStartup(unsigned long currentTime) {
  if (stateJustEntered) {
    setMouseLEDsRed();
    stateJustEntered = false;
  }
  if (currentTime - stateStartTime >= STARTUP_DURATION) {
    changeState(IO_CHECK);
  }
}

void Game::handleIOCheck(unsigned long currentTime) {
  (void)currentTime;
  String errorMessage = checkSwitchStates();
  if (errorMessage != "") {
    sendLine(String("err io_check ") + errorMessage);
    changeState(ERROR);
    sendLine("st error");
    return;
  }
  changeState(HOMING);
  sendLine("st homing");
}

void Game::handleHoming(unsigned long currentTime) {
  (void)currentTime;
  if (stateJustEntered) {
    startMouseBlinking();
    stateJustEntered = false;
  }

  bool allHome = true;
  for (int i = 0; i < laneCount; i++) {
    if (!lanes[i]) continue;
    if (lanes[i]->isHome()) {
      lanes[i]->motorStop();
    } else {
      lanes[i]->motorReverse(255);
      allHome = false;
    }
  }

  if (allHome) {
    for (int i = 0; i < laneCount; i++) {
      if (lanes[i]) lanes[i]->stopBlinking();
    }
    setMouseLEDsWhite();
    changeState(READY);
    sendLine("st ready");
  }
}

void Game::handleReady(unsigned long currentTime) {
  (void)currentTime;
  if (stateJustEntered) {
    sendLine("ready");
    stateJustEntered = false;
  }
}

void Game::handleRace(unsigned long currentTime) {
  if (stateJustEntered) {
    points[0] = 0;
    points[1] = 0;
    winner = 0;
    raceId++;
    raceStartMs = currentTime;
    raceDurationMs = 0;
    for (int i = 0; i < laneCount; i++) {
      if (!lanes[i]) continue;
      lanes[i]->stopBlinking();
      lanes[i]->startRunningLight();
    }
    stateJustEntered = false;
    sendLine("st racing");
  }

  // Keep the 2s score grace period (motor EMI protection)
  if (currentTime - stateStartTime < 2000) {
    return;
  }

  for (int i = 0; i < laneCount; i++) {
    if (!lanes[i]) continue;
    int lane = i + 1;

    if (lanes[i]->readWinSwitch() == LOW) {
      winner = lane;
      sendLine(String("evt win ") + lane);
      changeState(STOP);
      return;
    }

    if (lanes[i]->score1RisingEdge()) {
      points[i] += 1;
      lanes[i]->startScoreDisplay(COLOR_1PT_R, SCORE_DISPLAY_DURATION);
      lanes[i]->addMotorTime(SCORE_1PT_MOTOR_TIME);
      sendLine(String("evt score ") + lane + " 1");
    }
    if (lanes[i]->score2RisingEdge()) {
      points[i] += 2;
      lanes[i]->startScoreDisplay(COLOR_2PT_R, SCORE_DISPLAY_DURATION);
      lanes[i]->addMotorTime(SCORE_2PT_MOTOR_TIME);
      sendLine(String("evt score ") + lane + " 2");
    }
    if (lanes[i]->score3RisingEdge()) {
      points[i] += 3;
      lanes[i]->startScoreDisplay(COLOR_3PT_R, SCORE_DISPLAY_DURATION);
      lanes[i]->addMotorTime(SCORE_3PT_MOTOR_TIME);
      sendLine(String("evt score ") + lane + " 3");
    }
  }
}

void Game::handleStop(unsigned long currentTime) {
  if (stateJustEntered) {
    if (raceStartMs != 0) {
      raceDurationMs = currentTime - raceStartMs;
    }
    stopAllMotors();
    for (int i = 0; i < laneCount; i++) {
      if (!lanes[i]) continue;
      lanes[i]->stopRunningLight();
      if (winner == (i + 1)) {
        lanes[i]->startBlinking(0, 255, 0, WINNER_BLINK_INTERVAL);
      } else {
        lanes[i]->startBlinking(255, 0, 0, WINNER_BLINK_INTERVAL);
      }
    }
    stateJustEntered = false;
    sendLine("st stop");
  }

  // Close the loop on its own: winner screen, then back home so the next
  // group can log in without anyone touching the controller.
  if (currentTime - stateStartTime >= AUTO_RETURN_DELAY) {
    changeState(HOMING);
    sendLine("st homing");
  }
}

void Game::handleError(unsigned long currentTime) {
  (void)currentTime;
  if (stateJustEntered) {
    stopAllMotors();
    setMouseLEDsRed();
    stateJustEntered = false;
    sendLine("st error");
  }
}

void Game::handleDebug(unsigned long currentTime) {
  for (int i = 0; i < 2; i++) {
    if (dbgMotorUntil[i] != 0 && currentTime >= dbgMotorUntil[i]) {
      if (lanes[i]) lanes[i]->motorStop();
      dbgMotorUntil[i] = 0;
    }
  }
}

void Game::setMouseLEDsRed() {
  for (int i = 0; i < laneCount; i++) {
    if (lanes[i]) lanes[i]->setAllLEDs(COLOR_RED_R);
  }
}

void Game::setMouseLEDsWhite() {
  for (int i = 0; i < laneCount; i++) {
    if (lanes[i]) lanes[i]->setAllLEDs(COLOR_WHITE_R);
  }
}

void Game::turnOffAllLEDs() {
  for (int i = 0; i < laneCount; i++) {
    if (lanes[i]) lanes[i]->clearAllLEDs();
  }
}

void Game::startMouseBlinking() {
  for (int i = 0; i < laneCount; i++) {
    if (lanes[i]) lanes[i]->startBlinking(COLOR_WHITE_R, HOMING_BLINK_INTERVAL);
  }
}

void Game::stopAllMotors() {
  for (int i = 0; i < 2; i++) {
    if (lanes[i]) lanes[i]->motorStop();
    dbgMotorUntil[i] = 0;
  }
}

String Game::checkSwitchStates() {
  if (!lanes[0]) return "Mice not registered";

  if (laneCount == 2 && lanes[0] && lanes[1]) {
    if (lanes[0]->readWinSwitch() == LOW && lanes[1]->readWinSwitch() == LOW) {
      return "Both win switches pressed";
    }
  }
  return "";
}

const char* Game::apiState() const {
  if (systemMode != MODE_RUN) return "config";
  switch (currentState) {
    case STARTUP:
    case IO_CHECK:
    case HOMING:
      return "homing";
    case READY:
      return "ready";
    case RACE:
      return "race";
    case STOP:
      return "win";
    case ERROR:
      return "error";
    case DEBUG_STATE:
    default:
      return "config";
  }
}

int Game::getPoints(int idx) const {
  if (idx < 0 || idx > 1) return 0;
  return points[idx];
}

unsigned long Game::getRaceDurationMs() const {
  if (currentState == RACE && raceStartMs != 0) {
    return millis() - raceStartMs;
  }
  return raceDurationMs;
}
