#!/usr/bin/env python3
"""Moise-Brain entry point."""
import time
import threading
import logging
from logger import setup_logging
from config import Config
from moise_controller import MoiseController
from maus import Maus
from game import Game
from game_state import GameState
from game_data import GameData, GameError
from websocket_server import WebSocketServer
from controller_registry import ControllerRegistry
from system_mode import SystemModeManager, SystemMode
from errors import ErrorStore
from auth import AuthManager

try:
    from coin_counter import CoinCounter
except Exception:
    CoinCounter = None

try:
    from start_button import StartButton
except Exception:
    StartButton = None


def start_websocket_server(websocket_server):
    try:
        websocket_server.start()
    except Exception as e:
        print(f"WebSocket error: {e}")


def build_from_config(config, error_store):
    """Create mice and controllers from config (ports assigned later)."""
    mice = {}
    for lane in config.get_lanes_config():
        lid = int(lane["id"])
        mice[lid] = Maus(lid, lane.get("name"))

    controllers = []
    baud = config.get_serial_baud()
    timeout = config.get_serial_timeout()
    for cfg in config.get_controllers():
        lane_map = {}
        for local, global_id in cfg.get("lanes", {}).items():
            gid = int(global_id)
            if gid not in mice:
                raise ValueError(f"Unknown lane {gid} in controller {cfg.get('id')}")
            lane_map[int(local)] = mice[gid]
        ctrl = MoiseController(
            controller_id=int(cfg["id"]),
            name=cfg.get("name", f"Controller {cfg['id']}"),
            lane_map=lane_map,
            baud_rate=baud,
            timeout=timeout,
            error_store=error_store,
        )
        controllers.append(ctrl)
    return mice, controllers


def assign_ports(controllers, registry, error_store):
    discovered = registry.discover()
    by_id = {d["id"]: d for d in discovered if d.get("id")}
    for ctrl in controllers:
        disc = by_id.get(ctrl.controller_id)
        if disc:
            ctrl.set_port(disc["port"])
            error_store.clear(code="controller_missing", source=f"controller:{ctrl.controller_id}")
        else:
            error_store.raise_error(
                "controller_missing",
                f"Controller id={ctrl.controller_id} not found on USB",
                source=f"controller:{ctrl.controller_id}",
            )
    unmatched = [d for d in discovered if d.get("id") == 0]
    for d in unmatched:
        error_store.raise_error(
            "controller_no_id",
            f"Controller on {d['port']} has no ID",
            source=f"port:{d['port']}",
            severity="warning",
        )
    return discovered


def push_mode_to_controllers(controllers, mode_value):
    fw = "run" if mode_value == "run" else ("debug" if mode_value == "debug" else "idle")
    for ctrl in controllers:
        if ctrl.port:
            ctrl.sendCommand(f"mode {fw}")


def main():
    logger = setup_logging()
    logger.info("Moise-Brain starting")

    config = Config()
    if not config.validate_config():
        logger.error("Invalid configuration")
        return

    error_store = ErrorStore()
    system_mode = SystemModeManager()
    auth = AuthManager()
    game_state = GameState()
    game_data = GameData(game_state, config=config, error_store=error_store, system_mode=system_mode)

    mice, controllers = build_from_config(config, error_store)
    registry = ControllerRegistry(baud_rate=config.get_serial_baud())

    app_context = {
        "controllers": controllers,
        "registry": registry,
        "config": config,
        "on_mode_change": lambda mode: push_mode_to_controllers(controllers, mode),
    }

    websocket_server = None
    if config.is_websocket_enabled():
        websocket_server = WebSocketServer(
            game_data,
            config.get_websocket_host(),
            config.get_websocket_port(),
            auth=auth,
            config=config,
            system_mode=system_mode,
            app_context=app_context,
        )
        threading.Thread(target=start_websocket_server, args=(websocket_server,), daemon=True).start()

        # Forward serial log entries to WS when subscribed
        def make_serial_cb(loop_holder):
            def cb(entry):
                if websocket_server and websocket_server.serial_subscribers:
                    # Schedule from sync context — use call_soon_threadsafe if loop known
                    try:
                        # Store pending; broadcast loop will pick up via get_log on subscribe.
                        # Direct push: try to get running loop from ws thread via shared queue.
                        websocket_server._pending_serial = getattr(websocket_server, "_pending_serial", [])
                        websocket_server._pending_serial.append(entry)
                    except Exception:
                        pass
            return cb

        # Attach subscriber hooks after ports open
    else:
        logger.info("WebSocket disabled")

    coin_counter = None
    coin_config = config.get_coin_counter_config()
    if coin_config and coin_config.get("enabled") and CoinCounter:
        try:
            coin_counter = CoinCounter(coin_config)
        except Exception as e:
            error_store.raise_error("coin_gpio", str(e), source="coin")
            game_data.set_game_error(GameError.HARDWARE_ERROR, str(e))

    start_button = None
    if config.is_start_button_enabled() and StartButton:
        try:
            gpio = config.get_start_button_gpio() or 17
            start_button = StartButton(gpio)
        except Exception as e:
            logger.warning(f"Start button unavailable (ok on Mac/dev): {e}")

    game = Game(
        logger,
        game_data=game_data,
        start_button=start_button,
        config=config,
        error_store=error_store,
        system_mode=system_mode,
    )

    assign_ports(controllers, registry, error_store)

    controller_ok = {}
    reconnect_at = {}
    for ctrl in controllers:
        game.add_controller(ctrl)
        controller_ok[ctrl.controller_id] = False
        reconnect_at[ctrl.controller_id] = 0
        if ctrl.port:
            try:
                ok = ctrl.init()
                controller_ok[ctrl.controller_id] = ok
                if ok and websocket_server:
                    def _hook(entry, _ws=websocket_server):
                        pending = getattr(_ws, "_pending_serial", None)
                        if pending is None:
                            _ws._pending_serial = []
                            pending = _ws._pending_serial
                        pending.append(entry)

                    ctrl.serial_interface.subscribers.append(_hook)
                if not ok:
                    error_store.raise_error(
                        "serial_open",
                        f"Could not open {ctrl.port}",
                        source=f"controller:{ctrl.controller_id}",
                    )
            except Exception as e:
                error_store.raise_error(
                    "serial_open",
                    str(e),
                    source=f"controller:{ctrl.controller_id}",
                )

    push_mode_to_controllers(controllers, system_mode.get_value())

    next_discover_at = time.time() + 15

    def attach_serial_hook(ctrl):
        if not websocket_server or not ctrl.serial_interface:
            return

        def _hook(entry, _ws=websocket_server):
            pending = getattr(_ws, "_pending_serial", None)
            if pending is None:
                _ws._pending_serial = []
                pending = _ws._pending_serial
            pending.append(entry)

        ctrl.serial_interface.subscribers.append(_hook)

    logger.info("Main loop starting")
    try:
        while True:
            now = time.time()

            # Drain pending serial to WS subscribers (best-effort from main thread via flag)
            if websocket_server and getattr(websocket_server, "_pending_serial", None):
                # Entries stay in per-controller ring buffers; live push is handled
                # when clients are subscribed — keep queue bounded
                if len(websocket_server._pending_serial) > 500:
                    websocket_server._pending_serial = websocket_server._pending_serial[-100:]

            # One global rediscovery when any controller still has no port
            if any(not c.port for c in controllers) and now >= next_discover_at:
                assign_ports(controllers, registry, error_store)
                next_discover_at = now + 15
                for ctrl in controllers:
                    if ctrl.port and not controller_ok.get(ctrl.controller_id):
                        reconnect_at[ctrl.controller_id] = now

            for ctrl in controllers:
                cid = ctrl.controller_id
                if controller_ok.get(cid):
                    try:
                        ctrl.input()
                    except Exception as e:
                        logger.error(f"Controller {cid} input: {e}")
                        error_store.raise_error(
                            "communication_error",
                            str(e),
                            source=f"controller:{cid}",
                        )
                        game_data.set_game_error(GameError.COMMUNICATION_ERROR, str(e))
                        controller_ok[cid] = False
                        reconnect_at[cid] = now + 2
                elif ctrl.port and now >= reconnect_at.get(cid, 0):
                    try:
                        if ctrl.init():
                            controller_ok[cid] = True
                            attach_serial_hook(ctrl)
                            push_mode_to_controllers([ctrl], system_mode.get_value())
                            error_store.clear(source=f"controller:{cid}")
                            logger.info(f"Controller {cid} reconnected")
                        else:
                            reconnect_at[cid] = now + 2
                    except Exception as e:
                        logger.error(f"Reconnect {cid}: {e}")
                        reconnect_at[cid] = now + 2

            if start_button and system_mode.is_run() and config.is_start_button_enabled():
                start_button.input()

            try:
                game.cycleUpdate()
                game_data.set_game_state(game.get_current_state().value)
                for maus in game.maeuse:
                    game_data.set_maus_punktzahl(maus.maus_id, maus.punktzahl)
            except Exception as e:
                logger.error(f"Game cycle: {e}")
                game_data.set_game_error(GameError.HARDWARE_ERROR, str(e))

            # Status snapshot for UI
            game_data.set_controllers_status([c.get_status() for c in controllers])
            io = {}
            for c in controllers:
                for k, v in c.io_states.items():
                    io[f"{c.controller_id}:{k}"] = v
            game_data.set_io_states(io)

            if coin_counter and system_mode.is_run():
                try:
                    coin_value = coin_counter.cycle_update()
                    if coin_value:
                        game_state.add_einzahlung(coin_value)
                        logger.info(f"Coin {coin_value} cent, balance {game_state.get_guthaben()}")
                except Exception as e:
                    error_store.raise_error("coin", str(e), source="coin")

            time.sleep(0.01)

    except KeyboardInterrupt:
        logger.info("Interrupted")
    finally:
        for ctrl in controllers:
            try:
                ctrl.close()
            except Exception:
                pass
        if start_button:
            try:
                start_button.cleanup()
            except Exception:
                pass
        logger.info("Stopped")


if __name__ == "__main__":
    main()
