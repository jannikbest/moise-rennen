#include "net.h"

#include <WiFi.h>
#include <WiFiUdp.h>
#include <WebSocketsServer.h>
#include <stdio.h>
#include <string.h>

#include "config.h"
#include "wifi_secrets.h"

namespace net {

static const uint16_t WS_PORT = 81;
static const uint16_t DISCOVER_PORT = 4210;
static const unsigned long HEARTBEAT_MS = 1000;
static const unsigned long WIFI_RETRY_MS = 5000;
static const char* DISCOVER_PROBE = "MOISE?";

static WebSocketsServer server(WS_PORT);
static WiFiUDP udp;
static bool udpReady = false;
static uint32_t seq = 0;
static unsigned long lastPushMs = 0;
static unsigned long lastWifiAttemptMs = 0;

static char lastState[16] = "";
static int lastPoints[MAX_LANES];
static int lastWinner = -1;
static int lastLaneCount = -1;
static uint32_t lastRaceId = 0;
static unsigned long lastDurationMs = 0;
static bool lastPointsInit = false;

static void onEvent(uint8_t num, WStype_t type, uint8_t* payload, size_t length) {
  (void)payload;
  (void)length;
  if (type == WStype_CONNECTED) {
    // Force a fresh push on next loop so the new client gets state immediately.
    lastState[0] = '\0';
    lastPointsInit = false;
    lastWinner = -1;
    lastLaneCount = -1;
    lastRaceId = 0;
    lastDurationMs = 0;
    (void)num;
  }
}

static void ensureWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }
  const unsigned long now = millis();
  if (lastWifiAttemptMs != 0 && (now - lastWifiAttemptMs) < WIFI_RETRY_MS) {
    return;
  }
  lastWifiAttemptMs = now;
  Serial.printf("WiFi connecting to %s…\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

static void ensureUdp() {
  if (udpReady || WiFi.status() != WL_CONNECTED) {
    return;
  }
  if (udp.begin(DISCOVER_PORT)) {
    udpReady = true;
    Serial.printf("UDP discovery on :%u  IP %s\n", DISCOVER_PORT, WiFi.localIP().toString().c_str());
  }
}

static void pollDiscover() {
  if (!udpReady) {
    return;
  }
  const int packetSize = udp.parsePacket();
  if (packetSize <= 0) {
    return;
  }

  char buf[32];
  const int n = udp.read(buf, sizeof(buf) - 1);
  if (n <= 0) {
    return;
  }
  buf[n] = '\0';
  // Accept "MOISE?" with optional trailing whitespace/newline
  if (strncmp(buf, DISCOVER_PROBE, strlen(DISCOVER_PROBE)) != 0) {
    return;
  }

  IPAddress ip = WiFi.localIP();
  char reply[64];
  snprintf(
    reply, sizeof(reply),
    "MOISE 1 %u.%u.%u.%u %u",
    ip[0], ip[1], ip[2], ip[3],
    (unsigned)WS_PORT
  );

  udp.beginPacket(udp.remoteIP(), udp.remotePort());
  udp.write(reinterpret_cast<const uint8_t*>(reply), strlen(reply));
  udp.endPacket();
}

void begin() {
  WiFi.mode(WIFI_STA);
  WiFi.setHostname("moise-rennen");
  ensureWifi();

  server.begin();
  server.onEvent(onEvent);
}

static void buildAndBroadcast(Game& game) {
  const char* state = game.apiState();
  const int lanes = game.getLaneCount();
  const int winner = game.getWinner();
  const uint32_t raceId = game.getRaceId();
  const unsigned long durationMs = game.getRaceDurationMs();
  const int nLanes = (lanes < 1) ? 1 : ((lanes > MAX_LANES) ? MAX_LANES : lanes);

  int pts[MAX_LANES];
  for (int i = 0; i < nLanes; i++) {
    pts[i] = game.getPoints(i);
  }

  seq++;

  // Enough for 5 lanes + metadata
  char buf[512];
  int n = snprintf(
    buf, sizeof(buf),
    "{\"seq\":%lu,\"state\":\"%s\",\"maxPoints\":%d,\"winner\":%d,"
    "\"raceId\":%lu,\"durationMs\":%lu,\"lanes\":[",
    (unsigned long)seq, state, MAX_POINTS, winner,
    (unsigned long)raceId, durationMs
  );

  for (int i = 0; i < nLanes && n > 0 && n < (int)sizeof(buf); i++) {
    n += snprintf(
      buf + n, sizeof(buf) - (size_t)n,
      "%s{\"id\":%d,\"points\":%d}",
      (i == 0) ? "" : ",",
      i + 1, pts[i]
    );
  }
  if (n > 0 && n < (int)sizeof(buf) - 2) {
    n += snprintf(buf + n, sizeof(buf) - (size_t)n, "]}");
  }

  if (n > 0 && n < (int)sizeof(buf)) {
    server.broadcastTXT(buf);
  }

  strncpy(lastState, state, sizeof(lastState) - 1);
  lastState[sizeof(lastState) - 1] = '\0';
  for (int i = 0; i < nLanes; i++) lastPoints[i] = pts[i];
  for (int i = nLanes; i < MAX_LANES; i++) lastPoints[i] = -1;
  lastPointsInit = true;
  lastWinner = winner;
  lastLaneCount = lanes;
  lastRaceId = raceId;
  lastDurationMs = durationMs;
  lastPushMs = millis();
}

void loop(Game& game) {
  ensureWifi();
  if (WiFi.status() != WL_CONNECTED) {
    if (udpReady) {
      udp.stop();
      udpReady = false;
    }
    return;
  }
  ensureUdp();
  pollDiscover();

  server.loop();

  const char* state = game.apiState();
  const int lanes = game.getLaneCount();
  const int winner = game.getWinner();
  const uint32_t raceId = game.getRaceId();
  const unsigned long durationMs = game.getRaceDurationMs();
  const int nLanes = (lanes < 1) ? 1 : ((lanes > MAX_LANES) ? MAX_LANES : lanes);

  bool pointsChanged = !lastPointsInit;
  for (int i = 0; i < nLanes && !pointsChanged; i++) {
    if (game.getPoints(i) != lastPoints[i]) pointsChanged = true;
  }

  // durationMs changes every loop during a race — do not treat it as a
  // push trigger (heartbeat still refreshes the clock ~1 Hz).
  const bool changed =
    strcmp(state, lastState) != 0 ||
    pointsChanged ||
    winner != lastWinner ||
    lanes != lastLaneCount ||
    raceId != lastRaceId;

  const bool heartbeat = (millis() - lastPushMs) >= HEARTBEAT_MS;

  if (changed || heartbeat) {
    buildAndBroadcast(game);
  }
}

}  // namespace net
