import serial
import threading
import sys

def hexdump(data):
    hex_str = ' '.join(f'{b:02X}' for b in data)
    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)
    return f'{hex_str:<48} | {ascii_str}'

def bootlog_filter(data, state):
    """
    Filtert den Bootloader-Logblock aus, der mit 'ets ' oder typischem Müll beginnt.
    """
    output = bytearray()

    for byte in data:
        if state['skip']:
            if byte in (ord('\n'), ord('\r')):
                state['blank_line_seen'] = True
            elif state['blank_line_seen']:
                # Nach leerer Zeile: Ende des Logs → wieder ausgeben
                state['skip'] = False
                state['blank_line_seen'] = False
                output.append(byte)
            continue

        # Buffer füllen zur Erkennung von Mustern
        state['buffer'].append(byte)
        if len(state['buffer']) > 100:
            state['buffer'].pop(0)

        buf = bytes(state['buffer'])
        if b'ets ' in buf or buf.startswith(b'\xFF\xFF') or buf.startswith(b'\x00\x00') or b'rst:0x' in buf:
            state['skip'] = True
            state['blank_line_seen'] = False
            state['buffer'].clear()
            continue

        output.append(byte)

    return bytes(output)

def read_from_port(ser):
    state = {'skip': False, 'blank_line_seen': False, 'buffer': bytearray()}
    try:
        while True:
            data = ser.read(64)
            if data:
                clean = bootlog_filter(data, state)
                if clean:
                    print(hexdump(clean))
    except serial.SerialException:
        print("❌ Serielle Verbindung verloren.")
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
        print("❌ Senden fehlgeschlagen.")
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    port = '/dev/tty.usbserial-0001'  # z.B. COM4 unter Windows
    baud = 9600

    try:
        ser = serial.Serial(port, baud, timeout=0.1)
        print(f'✅ Verbunden mit {port} @ {baud} Baud\n')

        reader_thread = threading.Thread(target=read_from_port, args=(ser,), daemon=True)
        reader_thread.start()

        write_to_port(ser)

    except serial.SerialException as e:
        print(f'❌ Fehler beim Öffnen von {port}: {e}')