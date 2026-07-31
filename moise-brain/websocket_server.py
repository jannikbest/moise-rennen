#!/usr/bin/env python3
"""WebSocket server — game broadcast + admin API v2."""
import asyncio
import json
import logging
import time
import websockets
from websockets.server import serve


PROTECTED = {
    "get_config",
    "set_config",
    "discover_controllers",
    "set_controller_id",
    "set_controller_lanes",
    "identify_controller",
    "set_mode",
    "debug_motor",
    "debug_led",
    "debug_io_stream",
    "add_credit",
    "set_price",
    "reset_counters",
    "serial_log_subscribe",
    "serial_log_unsubscribe",
    "serial_send",
}


class WebSocketServer:
    def __init__(
        self,
        game_data,
        host="localhost",
        port=8765,
        auth=None,
        config=None,
        system_mode=None,
        app_context=None,
    ):
        self.logger = logging.getLogger(__name__)
        self.game_data = game_data
        self.host = host
        self.port = port
        self.auth = auth
        self.config = config
        self.system_mode = system_mode
        self.app = app_context  # dict with controllers, registry, etc.
        self.clients = set()
        self.last_game_summary = None
        self.serial_subscribers = set()
        self.logger.info(f"WebSocket server on {host}:{port}")

    async def register(self, websocket):
        self.clients.add(websocket)

    async def unregister(self, websocket):
        self.clients.discard(websocket)
        self.serial_subscribers.discard(websocket)

    async def send_game_data(self, websocket):
        try:
            await websocket.send(json.dumps(self.game_data.get_game_summary(), ensure_ascii=False))
        except Exception as e:
            self.logger.error(f"Send game data failed: {e}")

    async def broadcast_game_data(self):
        if not self.clients:
            return
        summary = self.game_data.get_game_summary()
        if summary != self.last_game_summary:
            message = json.dumps(summary, ensure_ascii=False)
            await asyncio.gather(
                *[c.send(message) for c in list(self.clients)],
                return_exceptions=True,
            )
            self.last_game_summary = summary

    async def broadcast_serial(self, entry):
        if not self.serial_subscribers:
            return
        msg = json.dumps({"type": "serial_log", "entry": entry}, ensure_ascii=False)
        await asyncio.gather(
            *[c.send(msg) for c in list(self.serial_subscribers)],
            return_exceptions=True,
        )

    def _require_token(self, data):
        if not self.auth:
            return True
        return self.auth.validate(data.get("token"))

    async def _reply(self, websocket, request_id, ok, payload=None, error=None):
        body = {"ok": ok, "request_id": request_id}
        if payload is not None:
            body["data"] = payload
        if error is not None:
            body["error"] = error
        await websocket.send(json.dumps(body, ensure_ascii=False))

    async def handle_action(self, websocket, data):
        action = data.get("action")
        request_id = data.get("request_id")

        if action in PROTECTED and not self._require_token(data):
            await self._reply(websocket, request_id, False, error="unauthorized")
            return

        if action == "get_game_data":
            await self.send_game_data(websocket)
        elif action == "ping":
            await websocket.send(json.dumps({"response": "pong", "request_id": request_id}))
        elif action == "login":
            result = self.auth.login(data.get("password", "")) if self.auth else None
            if result:
                await self._reply(websocket, request_id, True, payload=result)
            else:
                await self._reply(websocket, request_id, False, error="bad_password")
        elif action == "set_maus_name":
            maus_id = data.get("maus_id")
            name = data.get("name")
            if maus_id and name:
                self.game_data.set_maus_name(maus_id, name)
            await self._reply(websocket, request_id, True)
        elif action == "freispiel":
            betrag = data.get("betrag", 1)
            self.game_data.game_state_ref.add_freispiel(betrag)
            await self.send_game_data(websocket)
            await self._reply(websocket, request_id, True)
        elif action == "get_config":
            await self._reply(websocket, request_id, True, payload=self.config.get_raw())
        elif action == "set_config":
            cfg = data.get("config")
            if not isinstance(cfg, dict):
                await self._reply(websocket, request_id, False, error="invalid_config")
                return
            self.config.update_from_dict(cfg)
            await self._reply(websocket, request_id, True, payload=self.config.get_raw())
        elif action == "set_mode":
            mode = data.get("mode")
            try:
                self.system_mode.set(mode)
                if self.app and "on_mode_change" in self.app:
                    self.app["on_mode_change"](mode)
                await self._reply(websocket, request_id, True, payload={"mode": self.system_mode.get_value()})
            except Exception as e:
                await self._reply(websocket, request_id, False, error=str(e))
        elif action == "discover_controllers":
            registry = self.app.get("registry") if self.app else None
            if not registry:
                await self._reply(websocket, request_id, False, error="no_registry")
                return
            # Already-open controllers (ports may be busy for a fresh probe)
            open_now = []
            for c in (self.app or {}).get("controllers", []):
                if c.port:
                    open_now.append({
                        "port": c.port,
                        "id": c.controller_id,
                        "lanes": c.reported_lanes if c.reported_lanes is not None else len(c.lanes),
                        "bound": True,
                    })
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, registry.discover)
            # Merge: prefer live bound info, add unbound discoveries
            by_port = {r["port"]: r for r in results}
            for o in open_now:
                by_port[o["port"]] = o
            await self._reply(websocket, request_id, True, payload=list(by_port.values()))
        elif action == "set_controller_id":
            port = data.get("port")
            cid = data.get("id")
            ok = await self._serial_oneshot(port, f"id {cid}")
            await self._reply(websocket, request_id, ok, error=None if ok else "serial_failed")
        elif action == "set_controller_lanes":
            port = data.get("port")
            lanes = data.get("lanes")
            ok = await self._serial_oneshot(port, f"lanes {lanes}")
            await self._reply(websocket, request_id, ok, error=None if ok else "serial_failed")
        elif action == "identify_controller":
            ctrl = self._find_controller(data)
            if not ctrl:
                await self._reply(websocket, request_id, False, error="not_found")
                return
            ctrl.sendCommand("identify")
            await self._reply(websocket, request_id, True)
        elif action == "debug_motor":
            if not self.system_mode.is_debug():
                await self._reply(websocket, request_id, False, error="wrong_mode")
                return
            ctrl = self._find_controller(data)
            lane = data.get("lane", 1)
            direction = data.get("direction", "stop")
            ms = data.get("ms", 500)
            if not ctrl:
                await self._reply(websocket, request_id, False, error="not_found")
                return
            ctrl.sendCommand(f"dbg motor {lane} {direction} {ms}")
            await self._reply(websocket, request_id, True)
        elif action == "debug_led":
            if not self.system_mode.is_debug():
                await self._reply(websocket, request_id, False, error="wrong_mode")
                return
            ctrl = self._find_controller(data)
            lane = data.get("lane", 1)
            color = data.get("color", "on")
            if not ctrl:
                await self._reply(websocket, request_id, False, error="not_found")
                return
            ctrl.sendCommand(f"dbg led {lane} {color}")
            await self._reply(websocket, request_id, True)
        elif action == "debug_io_stream":
            if not self.system_mode.is_debug():
                await self._reply(websocket, request_id, False, error="wrong_mode")
                return
            enabled = data.get("enabled", True)
            cmd = "dbg stream on" if enabled else "dbg stream off"
            for ctrl in (self.app or {}).get("controllers", []):
                ctrl.sendCommand("mode debug")
                ctrl.sendCommand(cmd)
                if enabled:
                    ctrl.sendCommand("dbg io?")
            await self._reply(websocket, request_id, True)
        elif action == "add_credit":
            cent = int(data.get("cent", 0))
            if cent <= 0:
                await self._reply(websocket, request_id, False, error="invalid_amount")
                return
            self.game_data.game_state_ref.add_service_gutschrift(cent)
            self.logger.info(f"ADMIN add_credit {cent} cent at {time.time()}")
            await self._reply(websocket, request_id, True, payload={"guthaben": self.game_data.get_guthaben()})
        elif action == "set_price":
            try:
                self.config.set_game_price_cent(data.get("cent"))
                self.logger.info(f"ADMIN set_price {data.get('cent')} at {time.time()}")
                await self._reply(websocket, request_id, True, payload={"price_cent": self.config.get_game_price_cent()})
            except Exception as e:
                await self._reply(websocket, request_id, False, error=str(e))
        elif action == "reset_counters":
            self.game_data.game_state_ref.reset_counters()
            self.logger.info(f"ADMIN reset_counters at {time.time()}")
            await self._reply(websocket, request_id, True)
        elif action == "serial_log_subscribe":
            if not self.system_mode.is_debug():
                await self._reply(websocket, request_id, False, error="wrong_mode")
                return
            self.serial_subscribers.add(websocket)
            logs = []
            for ctrl in (self.app or {}).get("controllers", []):
                for entry in ctrl.get_serial_log(100):
                    logs.append(entry)
            logs.sort(key=lambda e: e.get("ts", 0))
            await self._reply(websocket, request_id, True, payload=logs)
        elif action == "serial_log_unsubscribe":
            self.serial_subscribers.discard(websocket)
            await self._reply(websocket, request_id, True)
        elif action == "serial_send":
            if not self.system_mode.is_debug():
                await self._reply(websocket, request_id, False, error="wrong_mode")
                return
            ctrl = self._find_controller(data)
            cmd = data.get("command", "")
            if not ctrl or not cmd:
                await self._reply(websocket, request_id, False, error="bad_args")
                return
            ctrl.sendCommand(cmd)
            await self._reply(websocket, request_id, True)
        else:
            await self._reply(websocket, request_id, False, error="unknown_action")

    def _find_controller(self, data):
        controllers = (self.app or {}).get("controllers", [])
        cid = data.get("controller_id")
        port = data.get("port")
        for c in controllers:
            if cid is not None and c.controller_id == int(cid):
                return c
            if port and c.port == port:
                return c
        return None

    async def _serial_oneshot(self, port, command):
        """Send a one-shot command on a port (for id/lanes before binding)."""
        if not port:
            return False
        # Prefer existing open controller
        for c in (self.app or {}).get("controllers", []):
            if c.port == port:
                c.sendCommand(command)
                return True
        # Temporary open
        def _do():
            import serial
            try:
                ser = serial.Serial(port, self.config.get_serial_baud(), timeout=0.2)
                time.sleep(0.05)
                ser.reset_input_buffer()
                ser.write((command + "\n").encode())
                ser.flush()
                time.sleep(0.2)
                ser.close()
                return True
            except Exception as e:
                self.logger.error(f"oneshot {port}: {e}")
                return False

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _do)

    async def handle_client(self, websocket, path=None):
        await self.register(websocket)
        try:
            await self.send_game_data(websocket)
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_action(websocket, data)
                except json.JSONDecodeError:
                    self.logger.warning("Invalid JSON")
                except Exception as e:
                    self.logger.error(f"Action error: {e}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister(websocket)

    async def start_server(self):
        self._pending_serial = []
        async with serve(self.handle_client, self.host, self.port):
            self.logger.info(f"WebSocket listening ws://{self.host}:{self.port}")
            while True:
                await self.broadcast_game_data()
                pending = getattr(self, "_pending_serial", [])
                if pending and self.serial_subscribers:
                    batch = pending[:]
                    self._pending_serial = []
                    for entry in batch:
                        await self.broadcast_serial(entry)
                elif pending and len(pending) > 200:
                    self._pending_serial = pending[-50:]
                state = self.game_data.get_game_state()
                await asyncio.sleep(0.25 if state == "racing" else 0.1)

    def start(self):
        asyncio.run(self.start_server())
