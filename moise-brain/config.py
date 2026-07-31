#!/usr/bin/env python3
"""Config loader/saver for Moise-Brain."""
import json
import logging
import os
from pathlib import Path


class Config:
    MAX_PRICE_CENT = 5000

    def __init__(self, config_file=None):
        self.logger = logging.getLogger(__name__)
        if config_file is None:
            config_file = os.environ.get("MOISE_CONFIG", "config.json")
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self):
        try:
            config_path = Path(self.config_file)
            if not config_path.exists():
                self.logger.error(f"Config {self.config_file} not found")
                return self._get_default_config()
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            self.logger.info(f"Loaded config from {self.config_file}")
            return config
        except Exception as e:
            self.logger.error(f"Config load error: {e}")
            return self._get_default_config()

    def _get_default_config(self):
        return {
            "lanes": [
                {"id": 1, "name": "Speedy", "speed": 255},
                {"id": 2, "name": "Pilzy", "speed": 255},
                {"id": 3, "name": "Emdy", "speed": 255},
                {"id": 4, "name": "Kety", "speed": 255},
                {"id": 5, "name": "Koky", "speed": 255},
            ],
            "controllers": [
                {"id": 1, "name": "Links", "lanes": {"1": 1, "2": 2}},
                {"id": 2, "name": "Mitte", "lanes": {"1": 3}},
                {"id": 3, "name": "Rechts", "lanes": {"1": 4, "2": 5}},
            ],
            "game": {"price_cent": 100},
            "serial": {"baud_rate": 115200, "timeout": 0.01},
            "start_button": {"enabled": True, "gpio_pin": 17},
            "coin_counter": {"enabled": True, "gpio_pin": 18, "pulse_timeout": 0.8},
            "websocket": {"enabled": True, "host": "localhost", "port": 8765},
        }

    def save(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
        self.logger.info(f"Config saved to {self.config_file}")

    def get_raw(self):
        return self.config

    def update_from_dict(self, data):
        self.config.update(data)
        self.save()

    def get_lanes_config(self):
        return self.config.get("lanes", [])

    def get_controllers_config(self):
        return self.config.get("controllers", [])

    def get_controllers(self):
        return self.get_controllers_config()

    def get_game_price_cent(self):
        price = int(self.config.get("game", {}).get("price_cent", 100))
        if price < 1:
            price = 1
        if price > self.MAX_PRICE_CENT:
            price = self.MAX_PRICE_CENT
        return price

    def set_game_price_cent(self, cent):
        cent = int(cent)
        if cent < 1 or cent > self.MAX_PRICE_CENT:
            raise ValueError(f"price_cent must be 1..{self.MAX_PRICE_CENT}")
        self.config.setdefault("game", {})["price_cent"] = cent
        self.save()

    def get_serial_baud(self):
        return int(self.config.get("serial", {}).get("baud_rate", 115200))

    def get_serial_timeout(self):
        return float(self.config.get("serial", {}).get("timeout", 0.01))

    def get_coin_counter_config(self):
        return self.config.get("coin_counter", {})

    def get_coin_counter_gpio(self):
        cfg = self.get_coin_counter_config()
        return cfg.get("gpio_pin") if cfg else None

    def get_start_button_config(self):
        return self.config.get("start_button", {})

    def is_start_button_enabled(self):
        return self.get_start_button_config().get("enabled", False)

    def get_start_button_gpio(self):
        return self.get_start_button_config().get("gpio_pin")

    def get_websocket_config(self):
        return self.config.get("websocket", {})

    def is_websocket_enabled(self):
        return self.get_websocket_config().get("enabled", False)

    def get_websocket_host(self):
        return self.get_websocket_config().get("host", "localhost")

    def get_websocket_port(self):
        return self.get_websocket_config().get("port", 8765)

    def validate_config(self):
        errors = []
        lanes = self.get_lanes_config()
        if not lanes:
            errors.append("At least one lane required")
        controllers = self.get_controllers()
        if not controllers:
            errors.append("At least one controller required")
        lane_ids = {l["id"] for l in lanes}
        for ctrl in controllers:
            for local, global_id in ctrl.get("lanes", {}).items():
                if int(global_id) not in lane_ids:
                    errors.append(f"Controller {ctrl.get('id')} maps to unknown lane {global_id}")
        try:
            self.get_game_price_cent()
        except Exception as e:
            errors.append(str(e))
        if errors:
            for e in errors:
                self.logger.error(f"Config error: {e}")
            return False
        return True
