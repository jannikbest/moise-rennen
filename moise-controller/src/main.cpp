#include <Arduino.h>
#include "config.h"
#include "mouse.h"
#include "game.h"
#include "net.h"

Mouse mouse1(mouse1_pins, "M1");
Mouse mouse2(mouse2_pins, "M2");
Game game;

static char lineBuf[SERIAL_LINE_MAX];
static int lineLen = 0;
static bool lineOverflow = false;

static void pollSerial() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\r') continue;
    if (c == '\n') {
      if (!lineOverflow && lineLen > 0) {
        lineBuf[lineLen] = '\0';
        game.setCommand(String(lineBuf));
      }
      lineLen = 0;
      lineOverflow = false;
      continue;
    }
    if (lineLen >= SERIAL_LINE_MAX - 1) {
      lineOverflow = true;
      continue;
    }
    lineBuf[lineLen++] = c;
  }
}

void setup() {
  Serial.begin(SERIAL_BAUD_RATE);
  delay(SETUP_DELAY);

  mouse1.setup();
  mouse2.setup();
  game.begin(&mouse1, &mouse2);
  net::begin();
}

void loop() {
  pollSerial();

  mouse1.input();
  mouse2.input();
  game.onInputsUpdated();

  mouse1.update();
  mouse2.update();
  game.update();

  net::loop(game);

  delay(MAIN_LOOP_DELAY);
}
