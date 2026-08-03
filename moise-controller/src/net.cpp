#include "net.h"

#include <WiFi.h>
#include <WebSocketsServer.h>
#include <stdio.h>
#include <string.h>

#include "config.h"

namespace net {

static const char* AP_SSID = "moise-rennen";
static const uint16_t WS_PORT = 81;
static const unsigned long HEARTBEAT_MS = 1000;
static const int MAX_POINTS = 15;

static WebSocketsServer server(WS_PORT);
static uint32_t seq = 0;
static unsigned long lastPushMs = 0;

static char lastState[16] = "";
static int lastPoints[2] = {-1, -1};
static int lastWinner = -1;
static int lastLaneCount = -1;
static uint32_t lastRaceId = 0;
static unsigned long lastDurationMs = 0;

static void onEvent(uint8_t num, WStype_t type, uint8_t* payload, size_t length) {
  (void)payload;
  (void)length;
  if (type == WStype_CONNECTED) {
    // Force a fresh push on next loop so the new client gets state immediately.
    lastState[0] = '\0';
    lastPoints[0] = -1;
    lastPoints[1] = -1;
    lastWinner = -1;
    lastLaneCount = -1;
    lastRaceId = 0;
    lastDurationMs = 0;
    (void)num;
  }
}

void begin() {
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID);  // open SoftAP, fixed IP 192.168.4.1
  server.begin();
  server.onEvent(onEvent);
}

static void buildAndBroadcast(Game& game) {
  const char* state = game.apiState();
  const int lanes = game.getLaneCount();
  const int winner = game.getWinner();
  const int p0 = game.getPoints(0);
  const int p1 = (lanes > 1) ? game.getPoints(1) : 0;
  const uint32_t raceId = game.getRaceId();
  const unsigned long durationMs = game.getRaceDurationMs();

  seq++;

  char buf[256];
  int n;
  if (lanes >= 2) {
    n = snprintf(
      buf, sizeof(buf),
      "{\"seq\":%lu,\"state\":\"%s\",\"maxPoints\":%d,\"winner\":%d,"
      "\"raceId\":%lu,\"durationMs\":%lu,"
      "\"lanes\":[{\"id\":1,\"points\":%d},{\"id\":2,\"points\":%d}]}",
      (unsigned long)seq, state, MAX_POINTS, winner,
      (unsigned long)raceId, durationMs, p0, p1
    );
  } else {
    n = snprintf(
      buf, sizeof(buf),
      "{\"seq\":%lu,\"state\":\"%s\",\"maxPoints\":%d,\"winner\":%d,"
      "\"raceId\":%lu,\"durationMs\":%lu,"
      "\"lanes\":[{\"id\":1,\"points\":%d}]}",
      (unsigned long)seq, state, MAX_POINTS, winner,
      (unsigned long)raceId, durationMs, p0
    );
  }

  if (n > 0 && n < (int)sizeof(buf)) {
    server.broadcastTXT(buf);
  }

  strncpy(lastState, state, sizeof(lastState) - 1);
  lastState[sizeof(lastState) - 1] = '\0';
  lastPoints[0] = p0;
  lastPoints[1] = p1;
  lastWinner = winner;
  lastLaneCount = lanes;
  lastRaceId = raceId;
  lastDurationMs = durationMs;
  lastPushMs = millis();
}

void loop(Game& game) {
  server.loop();

  const char* state = game.apiState();
  const int lanes = game.getLaneCount();
  const int winner = game.getWinner();
  const int p0 = game.getPoints(0);
  const int p1 = (lanes > 1) ? game.getPoints(1) : 0;
  const uint32_t raceId = game.getRaceId();
  const unsigned long durationMs = game.getRaceDurationMs();

  const bool changed =
    strcmp(state, lastState) != 0 ||
    p0 != lastPoints[0] ||
    p1 != lastPoints[1] ||
    winner != lastWinner ||
    lanes != lastLaneCount ||
    raceId != lastRaceId ||
    durationMs != lastDurationMs;

  const bool heartbeat = (millis() - lastPushMs) >= HEARTBEAT_MS;

  if (changed || heartbeat) {
    buildAndBroadcast(game);
  }
}

}  // namespace net
