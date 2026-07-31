#!/usr/bin/env python3
"""Moise controller — serial bridge for one ESP32 (1–2 local lanes)."""
import logging
import time
from enum import Enum
from serial_interface import SerialInterface


class ControllerState(Enum):
    NOTREADY = "notReady"
    PENDING = "pending"
    ISREADY = "isReady"
    UNKNOWN = "unknown"
    ERROR = "error"
    BOOTING = "booting"


class MoiseController:
    NOISE_WARN_THRESHOLD = 20

    def __init__(self, controller_id, name, lane_map, baud_rate=115200, timeout=0.01, error_store=None):
        """
        lane_map: dict local_lane_str_or_int -> Maus instance
        e.g. {"1": maus1, "2": maus2} or {1: maus1}
        """
        self.controller_id = controller_id
        self.name = name
        self.port_name = None
        self.port = None
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.serial_interface = None
        self.state = ControllerState.NOTREADY
        self.error_store = error_store
        self.logger = logging.getLogger(__name__)
        self.firmware_mode = None
        self.reported_lanes = None
        self.io_states = {}
        self._noise_window = []

        self.lanes = {}
        for k, maus in lane_map.items():
            self.lanes[int(k)] = maus

        # Back-compat list of mice in local-lane order
        self.maeuse = [self.lanes[k] for k in sorted(self.lanes.keys())]

    def set_port(self, port):
        self.port = port
        self.port_name = port

    def init(self):
        if not self.port:
            return False
        self.serial_interface = SerialInterface(
            self.logger, self.port, self.baud_rate, self.timeout
        )
        ok = self.serial_interface.open_connection()
        if ok:
            self.state = ControllerState.BOOTING
            if self.error_store:
                self.error_store.clear(source=f"controller:{self.controller_id}")
        return ok

    def close(self):
        if self.serial_interface:
            self.serial_interface.close_connection()

    def sendCommand(self, command):
        if self.serial_interface:
            self.serial_interface.send_command(command)
            return True
        return False

    def checkState(self):
        if self.serial_interface:
            self.serial_interface.send_command("ready?")
            self.state = ControllerState.PENDING

    def input(self):
        if not self.serial_interface:
            return None

        lines = self.serial_interface.read_lines()
        for text, classification in lines:
            if classification == "bootlog":
                self.state = ControllerState.BOOTING
                if self.error_store:
                    self.error_store.raise_error(
                        "controller_reboot",
                        f"Controller {self.controller_id} rebooted",
                        source=f"controller:{self.controller_id}",
                        severity="warning",
                    )
                continue

            if classification != "valid":
                self._record_noise()
                continue

            self._handle_valid(text)
        return None

    def _record_noise(self):
        now = time.time()
        self._noise_window.append(now)
        self._noise_window = [t for t in self._noise_window if now - t < 10]
        if len(self._noise_window) >= self.NOISE_WARN_THRESHOLD and self.error_store:
            self.error_store.raise_error(
                "serial_noise",
                f"High noise on controller {self.controller_id} ({len(self._noise_window)} discarded/10s)",
                source=f"controller:{self.controller_id}",
                severity="warning",
            )

    def _handle_valid(self, data):
        if data.startswith("rdy "):
            # Boot banner: rdy id=1 lanes=2 fw=2.0.0
            self.state = ControllerState.NOTREADY
            parts = data.split()
            for p in parts[1:]:
                if p.startswith("id="):
                    pass  # identity already known from discovery
                elif p.startswith("lanes="):
                    try:
                        self.reported_lanes = int(p.split("=", 1)[1])
                    except ValueError:
                        pass
            if self.error_store:
                self.error_store.clear(code="controller_reboot", source=f"controller:{self.controller_id}")
            return

        if data == "ready":
            self.state = ControllerState.ISREADY
            for maus in self.maeuse:
                maus.set_ready()
            return

        if data == "no":
            self.state = ControllerState.NOTREADY
            return

        if data == "error" or data.startswith("err "):
            self.state = ControllerState.ERROR
            self.logger.error(f"Controller {self.controller_id}: {data}")
            if self.error_store:
                self.error_store.raise_error(
                    "controller_error",
                    data,
                    source=f"controller:{self.controller_id}",
                )
            return

        if data.startswith("st "):
            st = data[3:].strip()
            if st == "ready":
                self.state = ControllerState.ISREADY
            elif st in ("homing", "startup", "racing", "stop"):
                if st != "ready":
                    # don't force NOTREADY on every state — only leave ISREADY when leaving ready
                    if self.state == ControllerState.ISREADY and st != "ready":
                        self.state = ControllerState.NOTREADY
            elif st == "error":
                self.state = ControllerState.ERROR
            return

        if data.startswith("mode "):
            self.firmware_mode = data[5:].strip()
            return

        if data.startswith("id "):
            return

        if data.startswith("lanes "):
            try:
                self.reported_lanes = int(data.split()[1])
            except (IndexError, ValueError):
                pass
            return

        if data.startswith("evt score "):
            parts = data.split()
            if len(parts) >= 4:
                local = int(parts[2])
                points = int(parts[3])
                maus = self.lanes.get(local)
                if maus:
                    maus.add_points(points)
            return

        if data.startswith("evt win "):
            parts = data.split()
            if len(parts) >= 3:
                local = int(parts[2])
                maus = self.lanes.get(local)
                if maus:
                    maus.set_winning()
            return

        if data.startswith("evt io "):
            # evt io <lane> <name> <0|1>
            parts = data.split()
            if len(parts) >= 5:
                local = parts[2]
                name = parts[3]
                val = int(parts[4])
                key = f"{local}:{name}"
                self.io_states[key] = val
            return

        # Unknown valid-looking line: log only, do NOT change controller state
        self.logger.info(f"Controller {self.controller_id} unknown message: {data}")

    def cycleUpdate(self):
        pass

    def get_status(self):
        stats = self.serial_interface.stats.as_dict() if self.serial_interface else {}
        return {
            "id": self.controller_id,
            "name": self.name,
            "port": self.port,
            "state": self.state.value,
            "firmware_mode": self.firmware_mode,
            "reported_lanes": self.reported_lanes,
            "lanes": {str(k): v.maus_id for k, v in self.lanes.items()},
            "serial_stats": stats,
            "io_states": self.io_states.copy(),
        }

    def get_serial_log(self, limit=100):
        if self.serial_interface:
            return self.serial_interface.get_log(limit)
        return []
