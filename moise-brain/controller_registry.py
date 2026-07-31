#!/usr/bin/env python3
"""Discover ESP32 controllers on USB serial ports via id?."""
import glob
import logging
import time
import serial
from serial_interface import SerialInterface, BootlogFilter


def list_candidate_ports():
    patterns = [
        "/dev/ttyUSB*",
        "/dev/ttyACM*",
        "/dev/cu.usbserial*",
        "/dev/cu.usbmodem*",
        "/dev/cu.SLAB*",
        "/dev/cu.wchusbserial*",
    ]
    ports = []
    for pattern in patterns:
        ports.extend(glob.glob(pattern))
    return sorted(set(ports))


class ControllerRegistry:
    def __init__(self, baud_rate=115200, timeout=0.05):
        self.logger = logging.getLogger(__name__)
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.last_discovery = []

    def discover(self, settle_s=1.5):
        """Scan ports, query id?, return list of {port, id, lanes, raw}."""
        results = []
        for port in list_candidate_ports():
            info = self._probe(port, settle_s=settle_s)
            if info:
                results.append(info)
        self.last_discovery = results
        self.logger.info(f"Discovery found {len(results)} controller(s)")
        return results

    def _probe(self, port, settle_s=1.5):
        ser = None
        try:
            ser = serial.Serial(port, self.baud_rate, timeout=self.timeout)
            time.sleep(0.1)
            ser.reset_input_buffer()
            # Wait briefly for possible #rdy after open (ESP may reset on open)
            deadline = time.time() + settle_s
            boot = BootlogFilter()
            buf = bytearray()
            found_id = None
            found_lanes = None
            got_rdy = False

            while time.time() < deadline:
                if ser.in_waiting:
                    raw = ser.read(ser.in_waiting)
                    clean, _ = boot.feed(raw)
                    if clean:
                        buf.extend(clean)
                # Try to parse lines
                while b"\n" in buf:
                    line, _, buf = buf.partition(b"\n")
                    try:
                        text = line.decode("utf-8", errors="ignore").strip("\r").strip()
                    except Exception:
                        continue
                    if not text:
                        continue
                    if text.startswith("#rdy"):
                        got_rdy = True
                        for part in text[1:].split()[1:]:
                            if part.startswith("id="):
                                try:
                                    found_id = int(part.split("=", 1)[1])
                                except ValueError:
                                    pass
                            elif part.startswith("lanes="):
                                try:
                                    found_lanes = int(part.split("=", 1)[1])
                                except ValueError:
                                    pass
                    elif text.startswith("#id "):
                        try:
                            found_id = int(text.split()[1])
                        except (IndexError, ValueError):
                            pass
                    elif text.startswith("#lanes "):
                        try:
                            found_lanes = int(text.split()[1])
                        except (IndexError, ValueError):
                            pass

                if got_rdy and found_id is not None:
                    break
                time.sleep(0.05)

            # Explicit query if still unknown
            if found_id is None:
                ser.write(b"id?\n")
                ser.flush()
                time.sleep(0.3)
                if ser.in_waiting:
                    raw = ser.read(ser.in_waiting)
                    clean, _ = boot.feed(raw)
                    for line in clean.decode("utf-8", errors="ignore").splitlines():
                        line = line.strip()
                        if line.startswith("#id "):
                            try:
                                found_id = int(line.split()[1])
                            except (IndexError, ValueError):
                                pass

            if found_lanes is None:
                ser.write(b"lanes?\n")
                ser.flush()
                time.sleep(0.2)
                if ser.in_waiting:
                    raw = ser.read(ser.in_waiting)
                    clean, _ = boot.feed(raw)
                    for line in clean.decode("utf-8", errors="ignore").splitlines():
                        line = line.strip()
                        if line.startswith("#lanes "):
                            try:
                                found_lanes = int(line.split()[1])
                            except (IndexError, ValueError):
                                pass

            return {
                "port": port,
                "id": found_id if found_id is not None else 0,
                "lanes": found_lanes if found_lanes is not None else None,
            }
        except Exception as e:
            self.logger.debug(f"Probe {port} failed: {e}")
            return None
        finally:
            if ser and ser.is_open:
                try:
                    ser.close()
                except Exception:
                    pass

    def match_controllers(self, configured, discovered):
        """
        configured: list of {id, name, lanes}
        discovered: list from discover()
        Returns list of (config_entry, port or None).
        """
        by_id = {d["id"]: d for d in discovered if d.get("id")}
        matched = []
        for cfg in configured:
            cid = cfg.get("id")
            disc = by_id.get(cid)
            matched.append((cfg, disc["port"] if disc else None))
        return matched
