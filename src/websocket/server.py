"""WebSocket server for mobile automation service."""

import asyncio
import json
import uuid
from typing import Any, Callable, Dict, Optional

import websockets
from websockets.server import WebSocketServerProtocol

from src.config import config
from src.utils.logger import get_logger
from src.robot import ActionableError
from src.types import WebSocketRequest, WebSocketResponse, ErrorInfo, DeviceInfo, DeviceType, SwipeDirection, Button, Orientation, LogOptions
from src.device_manager import device_manager

logger = get_logger(__name__)


class SessionContext:
    """Per-connection session context for device selection and state."""

    def __init__(self):
        self.selected_device: Optional[DeviceInfo] = None


class WebSocketMobileServer:
    """WebSocket server handling mobile automation requests."""

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.connections: Dict[WebSocketServerProtocol, SessionContext] = {}

    async def start(self) -> None:
        """Start the WebSocket server."""
        logger.info(f"Starting WebSocket server at ws://{self.host}:{self.port}")
        async with websockets.serve(self.handle_connection, self.host, self.port, max_size=None):
            await asyncio.Future()  # Run forever

    async def handle_connection(self, websocket: WebSocketServerProtocol) -> None:
        """Handle a new client connection."""
        ctx = SessionContext()
        self.connections[websocket] = ctx
        logger.info(f"Client connected: {websocket.remote_address}")

        try:
            async for message in websocket:
                await self.route_message(websocket, message)
        except websockets.exceptions.ConnectionClosedError as e:
            logger.info(f"Client disconnected with error: {e}")
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            # Cleanup on disconnection
            if ctx.selected_device:
                await device_manager.cleanup_robot(ctx.selected_device.id)
            self.connections.pop(websocket, None)
            logger.info(f"Client disconnected: {websocket.remote_address}")

    async def route_message(self, websocket: WebSocketServerProtocol, message: str) -> None:
        """Route incoming messages to appropriate handlers."""
        try:
            data = json.loads(message)
            request = WebSocketRequest(**data)
        except Exception as e:
            logger.error(f"Invalid message format: {e}")
            await self._send_error(websocket, "invalid_request", "Invalid message format", code="INVALID_REQUEST")
            return

        logger.debug(f"Received action: {request.action}")
        ctx = self.connections.get(websocket)

        try:
            # Dispatch based on action
            handler_name = f"handle_{request.action}"
            if hasattr(self, handler_name):
                handler = getattr(self, handler_name)
                response_data = await handler(ctx, request.params)
                await self._send_success(websocket, request.id, response_data)
            else:
                await self._send_error(websocket, request.id, f"Unknown action: {request.action}", code="UNKNOWN_ACTION")

        except ActionableError as ae:
            await self._send_error(websocket, request.id, str(ae), code=getattr(ae, 'code', 'ACTIONABLE_ERROR'), error_type="ActionableError")
        except Exception as e:
            logger.error(f"Action handler error for {request.action}: {e}")
            await self._send_error(websocket, request.id, str(e), code="INTERNAL_ERROR", error_type="TechnicalError")

    async def _send_success(self, websocket: WebSocketServerProtocol, id: str, data: Any) -> None:
        response = WebSocketResponse(id=id, success=True, data=data).model_dump()
        await websocket.send(json.dumps(response, default=str))

    async def _send_error(self, websocket: WebSocketServerProtocol, id: str, message: str, *, code: str, error_type: str = "TechnicalError") -> None:
        error = ErrorInfo(type=error_type, message=message, code=code)
        response = WebSocketResponse(id=id, success=False, error=error.model_dump()).model_dump()
        await websocket.send(json.dumps(response, default=str))

    # Device Management Actions
    async def handle_mobile_list_available_devices(self, ctx: SessionContext, params: Dict[str, Any]) -> Any:
        devices = await device_manager.list_all_devices()
        return [d.model_dump() for d in devices]

    async def handle_mobile_use_default_device(self, ctx: SessionContext, params: Dict[str, Any]) -> Any:
        device = await device_manager.select_default_device()
        ctx.selected_device = device
        return device.model_dump()

    async def handle_mobile_use_device(self, ctx: SessionContext, params: Dict[str, Any]) -> Any:
        device_id = params.get("id")
        if not device_id:
            raise ActionableError("'id' is required to select a device", code="MISSING_ID")
        device = await device_manager.get_device_info(device_id)
        if not device:
            raise ActionableError(f"Device not found: {device_id}", code="DEVICE_NOT_FOUND")
        ctx.selected_device = device
        return device.model_dump()

    def _require_robot(func: Callable) -> Callable:
        async def wrapper(self, ctx: SessionContext, params: Dict[str, Any]):
            if not ctx.selected_device:
                raise ActionableError("No device selected. Use mobile_use_default_device or mobile_use_device first.", code="NO_DEVICE_SELECTED")
            robot = await device_manager.get_robot(ctx.selected_device)
            return await func(self, robot, params)
        return wrapper

    # Application Management
    @_require_robot
    async def handle_mobile_list_apps(self, robot, params):
        apps = await robot.list_apps()
        return [a.model_dump() for a in apps]

    @_require_robot
    async def handle_mobile_launch_app(self, robot, params):
        package_name = params.get("packageName") or params.get("bundleId")
        if not package_name:
            raise ActionableError("'packageName' (Android) or 'bundleId' (iOS) is required", code="MISSING_PACKAGE")
        await robot.launch_app(package_name)
        return {"launched": True}

    @_require_robot
    async def handle_mobile_terminate_app(self, robot, params):
        package_name = params.get("packageName") or params.get("bundleId")
        if not package_name:
            raise ActionableError("'packageName' (Android) or 'bundleId' (iOS) is required", code="MISSING_PACKAGE")
        await robot.terminate_app(package_name)
        return {"terminated": True}

    # Screen Interaction
    @_require_robot
    async def handle_mobile_click_on_screen_at_coordinates(self, robot, params):
        x = int(params.get("x"))
        y = int(params.get("y"))
        await robot.tap(x, y)
        return {"tapped": True}

    @_require_robot
    async def handle_mobile_long_press_on_screen_at_coordinates(self, robot, params):
        x = int(params.get("x"))
        y = int(params.get("y"))
        await robot.long_press(x, y)
        return {"longPressed": True}

    @_require_robot
    async def handle_swipe_on_screen(self, robot, params):
        direction = SwipeDirection(params.get("direction"))
        await robot.swipe(direction)
        return {"swiped": direction.value}

    @_require_robot
    async def handle_mobile_type_keys(self, robot, params):
        text = params.get("text")
        await robot.send_keys(text)
        return {"typed": True}

    @_require_robot
    async def handle_mobile_press_button(self, robot, params):
        button = Button(params.get("button"))
        await robot.press_button(button)
        return {"pressed": button.value}

    @_require_robot
    async def handle_mobile_open_url(self, robot, params):
        url = params.get("url")
        await robot.open_url(url)
        return {"opened": url}

    # Screen State
    @_require_robot
    async def handle_mobile_take_screenshot(self, robot, params):
        data = await robot.get_screenshot()
        # Return as base64 to fit JSON transport
        import base64
        return {"image_base64": base64.b64encode(data).decode("ascii")}

    @_require_robot
    async def handle_mobile_list_elements_on_screen(self, robot, params):
        elements = await robot.get_elements_on_screen()
        return [e.model_dump() for e in elements]

    @_require_robot
    async def handle_mobile_get_screen_size(self, robot, params):
        size = await robot.get_screen_size()
        return size.model_dump()

    @_require_robot
    async def handle_mobile_set_orientation(self, robot, params):
        orientation = Orientation(params.get("orientation"))
        await robot.set_orientation(orientation)
        return {"orientation": orientation.value}

    @_require_robot
    async def handle_mobile_get_orientation(self, robot, params):
        orientation = await robot.get_orientation()
        return {"orientation": orientation.value}

    # Debugging
    @_require_robot
    async def handle_mobile_get_logs(self, robot, params):
        options = LogOptions(**params) if params else None
        logs = await robot.get_device_logs(options)
        return {"logs": logs}


async def main():
    server = WebSocketMobileServer(config.websocket_host, config.websocket_port)
    await server.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

