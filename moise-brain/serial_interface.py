#!/usr/bin/env python3
"""Hardened serial interface with bootlog filter and line classification."""
import serial
import time
import logging
from collections import deque


class BootlogFilter:
    """Detects ESP32 bootloader noise (ets / rst:0x / binary prefix)."""

    def __init__(self):
        self.skip = False
        self.blank_line_seen = False
        self.buffer = bytearray()

    def feed(self, data: bytes):
        """Return (clean_bytes, saw_boot_noise)."""
        output = bytearray()
        saw_boot = False

        for byte in data:
            if self.skip:
                if byte in (ord("\n"), ord("\r")):
                    self.blank_line_seen = True
                elif self.blank_line_seen:
                    self.skip = False
                    self.blank_line_seen = False
                    output.append(byte)
                continue

            self.buffer.append(byte)
            if len(self.buffer) > 100:
                self.buffer.pop(0)

            buf = bytes(self.buffer)
            if (
                b"ets " in buf
                or buf.startswith(b"\xff\xff")
                or buf.startswith(b"\x00\x00")
                or b"rst:0x" in buf
            ):
                self.skip = True
                self.blank_line_seen = False
                self.buffer.clear()
                saw_boot = True
                continue

            output.append(byte)

        return bytes(output), saw_boot


class SerialStats:
    def __init__(self):
        self.valid = 0
        self.discarded = 0
        self.decode_errors = 0
        self.reboots = 0
        self.last_valid_ts = None

    def as_dict(self):
        return {
            "valid": self.valid,
            "discarded": self.discarded,
            "decode_errors": self.decode_errors,
            "reboots": self.reboots,
            "last_valid_ts": self.last_valid_ts,
            "seconds_since_valid": (
                None if self.last_valid_ts is None else round(time.time() - self.last_valid_ts, 2)
            ),
        }


class SerialInterface:
    """Line-oriented serial I/O with noise hardening."""

    def __init__(self, logger, port, baud_rate=115200, timeout=0.01, log_size=200):
        self.ser = None
        self.logger = logger or logging.getLogger(__name__)
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.boot_filter = BootlogFilter()
        self.stats = SerialStats()
        self.log = deque(maxlen=log_size)
        self._rx_buffer = bytearray()
        self.waiting_for_rdy = False
        self.subscribers = []

    def open_connection(self):
        try:
            self.logger.info(f"Opening serial {self.port} @ {self.baud_rate}")
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
            )
            time.sleep(0.05)
            self.ser.reset_input_buffer()
            self.boot_filter = BootlogFilter()
            self._rx_buffer = bytearray()
            self.waiting_for_rdy = True
            return True
        except serial.SerialException as e:
            self.logger.error(f"Failed to open serial {self.port}: {e}")
            return False

    def close_connection(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.logger.info(f"Closed serial {self.port}")

    def _append_log(self, direction, text, classification):
        entry = {
            "ts": time.time(),
            "direction": direction,
            "text": text,
            "classification": classification,
            "port": self.port,
        }
        self.log.append(entry)
        for cb in list(self.subscribers):
            try:
                cb(entry)
            except Exception:
                pass

    def send_command(self, cmd):
        if self.ser and self.ser.is_open:
            full_cmd = f"{cmd}\n"
            self.ser.write(full_cmd.encode())
            self.ser.flush()
            self._append_log("tx", cmd, "tx")
            self.logger.debug(f"TX {self.port}: {cmd}")

    def send_data(self, data):
        self.send_command(data)

    def read_lines(self):
        """Read available bytes, return list of (text, classification).

        Classifications: valid, noise_no_hash, bootlog, discarded_pre_rdy, decode_error
        """
        results = []
        if not self.ser or not self.ser.is_open:
            return results
        if self.ser.in_waiting <= 0:
            return results

        try:
            raw = self.ser.read(self.ser.in_waiting)
        except Exception as e:
            self.logger.debug(f"Serial read error: {e}")
            return results

        clean, saw_boot = self.boot_filter.feed(raw)
        if saw_boot:
            self.stats.reboots += 1
            self.waiting_for_rdy = True
            self._append_log("rx", "<bootloader noise>", "bootlog")
            results.append(("<bootloader noise>", "bootlog"))

        if not clean:
            return results

        try:
            text = clean.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            self.stats.decode_errors += 1
            self.stats.discarded += 1
            self._append_log("rx", repr(clean[:64]), "decode_error")
            results.append((repr(clean[:64]), "decode_error"))
            # Keep what we can with replace for line splitting
            text = clean.decode("utf-8", errors="replace")

        self._rx_buffer.extend(text.encode("utf-8", errors="replace"))

        while True:
            try:
                nl = self._rx_buffer.index(ord("\n"))
            except ValueError:
                break
            line_bytes = bytes(self._rx_buffer[:nl])
            del self._rx_buffer[: nl + 1]
            line = line_bytes.decode("utf-8", errors="replace").strip("\r").strip()
            if not line:
                continue

            if self.waiting_for_rdy:
                if line.startswith("#rdy"):
                    self.waiting_for_rdy = False
                    self.stats.valid += 1
                    self.stats.last_valid_ts = time.time()
                    body = line[1:]
                    self._append_log("rx", line, "valid")
                    results.append((body, "valid"))
                else:
                    self.stats.discarded += 1
                    self._append_log("rx", line, "discarded_pre_rdy")
                    results.append((line, "discarded_pre_rdy"))
                continue

            if not line.startswith("#"):
                self.stats.discarded += 1
                self._append_log("rx", line, "noise_no_hash")
                results.append((line, "noise_no_hash"))
                continue

            body = line[1:]
            self.stats.valid += 1
            self.stats.last_valid_ts = time.time()
            self._append_log("rx", line, "valid")
            results.append((body, "valid"))

        return results

    def read_data(self):
        """Compatibility: return first valid line body or None."""
        for text, classification in self.read_lines():
            if classification == "valid":
                return text
        return None

    def get_log(self, limit=100):
        items = list(self.log)
        if limit:
            return items[-limit:]
        return items
