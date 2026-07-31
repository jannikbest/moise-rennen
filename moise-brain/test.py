#!/usr/bin/env python3
"""Manual serial debug terminal (uses production bootlog filter)."""
import serial
import threading
import sys
from serial_interface import BootlogFilter


def hexdump(data):
    hex_str = " ".join(f"{b:02X}" for b in data)
    ascii_str = "".join(chr(b) if 32 <= b < 127 else "." for b in data)
    return f"{hex_str:<48} | {ascii_str}"


def read_from_port(ser):
    boot = BootlogFilter()
    try:
        while True:
            data = ser.read(64)
            if data:
                clean, saw = boot.feed(data)
                if saw:
                    print("[bootlog filtered]")
                if clean:
                    print(hexdump(clean))
    except serial.SerialException:
        print("Serial connection lost.")
    except KeyboardInterrupt:
        pass


def write_to_port(ser):
    try:
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            ser.write(line.encode())
    except serial.SerialException:
        print("Send failed.")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
    baud = 115200
    try:
        ser = serial.Serial(port, baud, timeout=0.1)
        print(f"Connected {port} @ {baud}\n")
        threading.Thread(target=read_from_port, args=(ser,), daemon=True).start()
        write_to_port(ser)
    except serial.SerialException as e:
        print(f"Open failed: {e}")
