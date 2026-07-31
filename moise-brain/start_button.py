#!/usr/bin/env python3
"""Start button with debounce. Requires RPi.GPIO on the Pi."""
import time
import logging

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None


class StartButton:
    def __init__(self, gpio_pin, min_press_time=0.25):
        if GPIO is None:
            raise RuntimeError("RPi.GPIO not available")
        self.gpio_pin = gpio_pin
        self.min_press_time = min_press_time
        self.logger = logging.getLogger(__name__)

        self.is_pressed = False
        self.is_pressed_filtered = False
        self.is_pressed_filtered_old = False
        self.press_start_time = None
        self.last_signal_time = 0

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.gpio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def input(self):
        try:
            button_state = GPIO.input(self.gpio_pin)
            self.is_pressed_filtered_old = self.is_pressed_filtered

            if button_state == GPIO.LOW:
                if not self.is_pressed:
                    self.is_pressed = True
                    self.press_start_time = time.time()
                elif self.press_start_time and (time.time() - self.press_start_time) >= self.min_press_time:
                    self.is_pressed_filtered = True
            else:
                self.is_pressed = False
                self.is_pressed_filtered = False
                self.press_start_time = None
        except Exception as e:
            self.logger.error(f"Start button read error: {e}")

    def get_rising_edge(self):
        return self.is_pressed_filtered and not self.is_pressed_filtered_old

    def cleanup(self):
        try:
            GPIO.cleanup(self.gpio_pin)
        except Exception:
            pass
