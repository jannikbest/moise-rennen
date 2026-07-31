#!/usr/bin/env python3
"""Game state machine for Moise-Brain."""
import logging
import time
from enum import Enum


class PlayState(Enum):
    STARTUP = "startup"
    WAIT_FOR_READY = "wait_for_ready"
    WAIT_FOR_CONTROLLER_RESPONSE = "wait_for_controller_response"
    READY = "ready"
    RACING = "racing"
    FINISHED = "finished"
    ERROR = "error"
    PAUSED = "paused"


class Game:
    def __init__(self, logger, game_data=None, start_button=None, config=None, error_store=None, system_mode=None):
        self.logger = logger
        self.current_state = PlayState.STARTUP
        self.controllers = []
        self.maeuse = []
        self.wait_start_time = None
        self.finished_start_time = None
        self.controller_response_start_time = None
        self.race_start_time = None
        self.last_go_time = None
        self.last_point_time = None
        self.game_data = game_data
        self.start_button = start_button
        self.config = config
        self.error_store = error_store
        self.system_mode = system_mode
        self.retry_count = 0
        self.max_retries = 5
        self._paused_from = None
        self.logger.info("Game state machine initialized")

    def add_controller(self, controller):
        self.controllers.append(controller)
        self.maeuse.extend(controller.maeuse)
        for maus in controller.maeuse:
            maus.game_ref = self
        self.logger.info(
            f"Controller {controller.controller_id} with {len(controller.maeuse)} mice"
        )

    def set_state(self, new_state):
        old = self.current_state
        self.current_state = new_state
        self.logger.info(f"Play state: {old.value} -> {new_state.value}")

    def get_current_state(self):
        return self.current_state

    def abort_to_paused(self):
        """Called when leaving RUN mode — stop motors, pause game."""
        for controller in self.controllers:
            controller.sendCommand("lose")
        self._paused_from = self.current_state
        self.set_state(PlayState.PAUSED)

    def resume_from_paused(self):
        """Called when returning to RUN — re-home."""
        self.wait_start_time = None
        self.controller_response_start_time = None
        self.finished_start_time = None
        self.retry_count = 0
        self.set_state(PlayState.WAIT_FOR_READY)

    def cycleUpdate(self):
        if self.system_mode and not self.system_mode.is_run():
            if self.current_state != PlayState.PAUSED:
                self.abort_to_paused()
            return

        if self.current_state == PlayState.PAUSED:
            self.resume_from_paused()
            return

        if self.current_state == PlayState.STARTUP:
            self._handle_startup()
        elif self.current_state == PlayState.WAIT_FOR_READY:
            self._handle_wait_for_ready()
        elif self.current_state == PlayState.WAIT_FOR_CONTROLLER_RESPONSE:
            self._handle_wait_for_controller_response()
        elif self.current_state == PlayState.READY:
            self._handle_ready()
        elif self.current_state == PlayState.RACING:
            self._handle_racing()
        elif self.current_state == PlayState.FINISHED:
            self._handle_finished()
        elif self.current_state == PlayState.ERROR:
            self._handle_error()

    def _handle_startup(self):
        self.retry_count = 0
        self.set_state(PlayState.WAIT_FOR_READY)

    def _handle_wait_for_ready(self):
        if self.wait_start_time is None:
            self.wait_start_time = time.time()
            self.logger.info(
                f"Waiting for controllers ready (try {self.retry_count + 1}/{self.max_retries})"
            )
            for controller in self.controllers:
                if controller.state.value != "isReady":
                    controller.sendCommand("home")

        if all(c.state.value == "isReady" for c in self.controllers):
            self.logger.info("All controllers ready")
            self.set_state(PlayState.READY)
            self.wait_start_time = None
            self.retry_count = 0
            if self.error_store:
                self.error_store.clear(code="homing_timeout")
        elif time.time() - self.wait_start_time > 10:
            self.set_state(PlayState.WAIT_FOR_CONTROLLER_RESPONSE)
            self.wait_start_time = None

    def _price(self):
        if self.config:
            return self.config.get_game_price_cent()
        return 100

    def _handle_ready(self):
        if self.start_button and self.start_button.get_rising_edge():
            price = self._price()
            if self.game_data.get_guthaben() >= price:
                self.game_data.add_ausgaben(price)
                self.race_start_time = time.time()
                self.last_go_time = time.time()
                for controller in self.controllers:
                    controller.sendCommand("go")
                self.set_state(PlayState.RACING)
            else:
                self.logger.info(f"Not enough credit (need {price})")

    def _handle_racing(self):
        winner = None
        for maus in self.maeuse:
            if maus.has_won_game():
                winner = maus
                break

        if winner:
            if self.race_start_time is not None:
                elapsed_ms = (time.time() - self.race_start_time) * 1000
                self.logger.info(f"Win time: {elapsed_ms:.2f} ms")
                self.game_data.set_gewonnen_info(f"Maus {winner.maus_id}", f"{elapsed_ms:.2f}")

            for controller in self.controllers:
                if winner not in controller.maeuse:
                    controller.sendCommand("lose")

            if self.game_data:
                self.game_data.increment_spiele()
            self.set_state(PlayState.FINISHED)

    def _handle_finished(self):
        if self.finished_start_time is None:
            self.finished_start_time = time.time()
            self.reset_game()
            if self.game_data:
                self.game_data.reset_maus_namen()

        if time.time() - self.finished_start_time > 6:
            self.set_state(PlayState.WAIT_FOR_READY)
            self.finished_start_time = None

    def _handle_error(self):
        # Recoverable: after 5s retry homing
        if self.wait_start_time is None:
            self.wait_start_time = time.time()
            if self.error_store:
                self.error_store.raise_error(
                    "homing_timeout",
                    f"Homing failed after {self.max_retries} retries",
                    source="game",
                )
        elif time.time() - self.wait_start_time > 5:
            self.logger.info("Retrying after ERROR")
            self.wait_start_time = None
            self.retry_count = 0
            self.set_state(PlayState.WAIT_FOR_READY)

    def reset_game(self):
        for maus in self.maeuse:
            maus.set_ready()

    def update_point_time(self):
        if self.current_state == PlayState.RACING:
            self.last_point_time = time.time()

    def _handle_wait_for_controller_response(self):
        if self.controller_response_start_time is None:
            self.controller_response_start_time = time.time()
            for controller in self.controllers:
                if controller.state.value != "isReady":
                    controller.checkState()

        if all(c.state.value == "isReady" for c in self.controllers):
            self.set_state(PlayState.READY)
            self.controller_response_start_time = None
            self.retry_count = 0
            if self.error_store:
                self.error_store.clear(code="homing_timeout")
        elif time.time() - self.controller_response_start_time > 2:
            self.retry_count += 1
            if self.retry_count >= self.max_retries:
                self.set_state(PlayState.ERROR)
                self.controller_response_start_time = None
                self.wait_start_time = None
            else:
                self.set_state(PlayState.WAIT_FOR_READY)
                self.controller_response_start_time = None
