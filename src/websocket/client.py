"""WebSocket client for mobile automation service."""

import asyncio
import json
import uuid
import random
import time
from typing import Any, Dict, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass

import websockets
from websockets.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosedError, WebSocketException

from config import config
from utils.logger import get_logger
from robot import ActionableError
from enums import DeviceInfo, DeviceType, SwipeDirection, Button, Orientation, LogOptions
from device_manager import device_manager
from session_manager import get_session_manager, cleanup_session_manager

logger = get_logger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry and fallback mechanisms."""
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_backoff: bool = True
    jitter: bool = True
    health_check_interval: int = 30
    connection_timeout: int = 10


class ConnectionManager:
    """Manages WebSocket connection with retry and fallback mechanisms."""
    
    def __init__(self, server_url: str, retry_config: RetryConfig):
        self.server_url = server_url
        self.retry_config = retry_config
        self.websocket: Optional[WebSocketClientProtocol] = None
        self.is_connected = False
        self.last_heartbeat = None
        self.retry_count = 0
        self.health_check_task: Optional[asyncio.Task] = None
        
    async def connect_with_retry(self) -> bool:
        """Connect to server with exponential backoff retry."""
        while self.retry_count < self.retry_config.max_retries:
            try:
                logger.info(f"Attempting to connect to {self.server_url} (attempt {self.retry_count + 1})")
                
                self.websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.server_url,
                        max_size=None,
                        ping_interval=20,
                        ping_timeout=10,
                        close_timeout=10
                    ),
                    timeout=self.retry_config.connection_timeout
                )
                
                self.is_connected = True
                self.retry_count = 0
                self.last_heartbeat = time.time()
                
                # Health check is now handled in the message loop to avoid conflicts
                # self.health_check_task = asyncio.create_task(self._health_check_loop())
                
                logger.info(f"Successfully connected to {self.server_url}")
                return True
                
            except Exception as e:
                self.retry_count += 1
                logger.warning(f"Connection attempt {self.retry_count} failed: {e}")
                
                if self.retry_count < self.retry_config.max_retries:
                    delay = self._calculate_delay()
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Failed to connect after {self.retry_config.max_retries} attempts")
                    return False
        
        return False
    
    def _calculate_delay(self) -> float:
        """Calculate delay for next retry attempt."""
        if not self.retry_config.exponential_backoff:
            delay = self.retry_config.base_delay
        else:
            delay = min(
                self.retry_config.base_delay * (2 ** (self.retry_count - 1)),
                self.retry_config.max_delay
            )
        
        if self.retry_config.jitter:
            # Add random jitter to prevent thundering herd
            jitter = random.uniform(0, delay * 0.1)
            delay += jitter
            
        return delay
    
    async def _health_check_loop(self):
        """Periodic health check and reconnection."""
        while self.is_connected:
            try:
                await asyncio.sleep(self.retry_config.health_check_interval)
                
                # Check if websocket is still connected
                if self.websocket and not (hasattr(self.websocket, 'closed') and self.websocket.closed):
                    try:
                        # Send ping to check connection
                        await self.websocket.ping()
                        self.last_heartbeat = time.time()
                        logger.debug("Health check passed")
                    except Exception as ping_error:
                        logger.warning(f"Ping failed: {ping_error}")
                        await self._handle_connection_lost()
                else:
                    logger.warning("WebSocket connection lost, attempting reconnection...")
                    await self._handle_connection_lost()
                    
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                await self._handle_connection_lost()
    
    async def _handle_connection_lost(self):
        """Handle connection loss and attempt reconnection."""
        self.is_connected = False
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
            self.websocket = None
        
        # Reset retry count for reconnection
        self.retry_count = 0
        
        # Don't attempt immediate reconnection here - let the parent client handle it
        # This prevents infinite loops and allows for proper token refresh
    
    async def send_message(self, message: dict) -> bool:
        """Send message to server."""
        if not self.is_connected or not self.websocket:
            logger.error("Not connected to server")
            return False
        
        try:
            await self.websocket.send(json.dumps(message, default=str))
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            await self._handle_connection_lost()
            return False
    
    async def receive_message(self) -> Optional[dict]:
        """Receive message from server."""
        if not self.is_connected or not self.websocket:
            return None
        
        try:
            message = await self.websocket.recv()
            return json.loads(message)
        except ConnectionClosedError:
            logger.warning("Connection closed by server")
            await self._handle_connection_lost()
            return None
        except Exception as e:
            logger.error(f"Failed to receive message: {e}")
            return None
    
    async def close(self):
        """Close connection and cleanup."""
        self.is_connected = False
        
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket:
            try:
                await self.websocket.close()
            except:
                pass
            self.websocket = None


class WebSocketMobileClient:
    """WebSocket client that connects to backend server and executes automation commands."""
    
    def __init__(self, server_url: Optional[str] = None, retry_config: Optional[RetryConfig] = None):
        # Use session manager for authentication and URL management
        self.session_manager = get_session_manager()
        self.base_server_url = server_url or config.backend_server_url
        self.retry_config = retry_config or RetryConfig()
        
        # Initialize with placeholder URL - will be updated after session creation
        self.connection_manager = ConnectionManager(self.base_server_url, self.retry_config)
        self.device_manager = device_manager
        self.pending_requests: Dict[str, dict] = {}
        self.selected_device: Optional[DeviceInfo] = None
        self.robot = None
        self.current_session = None
        
    async def start(self) -> bool:
        """Start the WebSocket client and connect to server."""
        logger.info(f"Starting WebSocket client with session management")
        
        try:
            # Create session with S-Enricher to get authenticated WebSocket URL
            logger.info("Creating session with S-Enricher...")
            self.current_session = self.session_manager.create_session(
                provider="LOCAL_CLIENT", 
                platform="ANDROID"  # Could be made configurable
            )
            
            # Update connection manager with authenticated URL
            authenticated_url = self.current_session.websocket_url
            logger.info(f"Got authenticated WebSocket URL: {authenticated_url}")
            
            # Create new connection manager with authenticated URL
            self.connection_manager = ConnectionManager(authenticated_url, self.retry_config)
            
            # Connect to server using authenticated URL
            success = await self.connection_manager.connect_with_retry()
            if not success:
                logger.error("Failed to connect with authenticated WebSocket URL")
                return False
            
            # Start message handling loop
            asyncio.create_task(self._message_loop())
            
            # Auto-select default device for automation
            try:
                logger.info("Auto-selecting default device for automation...")
                device = await self.device_manager.select_default_device()
                self.selected_device = device
                self.robot = await self.device_manager.get_robot(device)
                logger.info(f"Auto-selected device: {device.id} ({device.model})")
            except Exception as e:
                logger.warning(f"Failed to auto-select device: {e}. Commands requiring device will fail.")
            
            # Send initial status message
            await self._send_status_update()
            
            logger.info(f"WebSocket client started successfully with session {self.current_session.session_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to start WebSocket client: {e}")
            return False
    
    async def _handle_reconnection(self):
        """Handle reconnection with token refresh."""
        logger.info("Handling reconnection with token refresh...")
        
        try:
            # Create a new session to get a fresh token
            logger.info("Creating new session for reconnection...")
            self.current_session = self.session_manager.create_session(
                provider="LOCAL_CLIENT",
                platform="ANDROID"
            )
            
            # Update connection manager with new authenticated URL
            authenticated_url = self.current_session.websocket_url
            logger.info(f"Got new authenticated WebSocket URL for reconnection")
            
            # Create new connection manager with new authenticated URL
            self.connection_manager = ConnectionManager(authenticated_url, self.retry_config)
            
            # Attempt to connect with new token
            success = await self.connection_manager.connect_with_retry()
            if success:
                logger.info(f"Successfully reconnected with new session {self.current_session.session_id}")
                # Send status update after reconnection
                await self._send_status_update()
            else:
                logger.error("Failed to reconnect even with new token")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to handle reconnection: {e}")
            return False
    
    async def _message_loop(self):
        """Main message handling loop."""
        while True:
            try:
                if not self.connection_manager.is_connected:
                    logger.warning("Connection lost, attempting reconnection with token refresh...")
                    success = await self._handle_reconnection()
                    if not success:
                        logger.error("Reconnection failed, waiting before retry...")
                        await asyncio.sleep(10)  # Wait 10 seconds before trying again
                        continue
                
                message = await self.connection_manager.receive_message()
                if message:
                    await self._handle_server_message(message)
                elif not self.connection_manager.is_connected:
                    # Connection was lost during receive
                    logger.warning("Connection lost during message receive")
                    continue
                    
            except Exception as e:
                logger.error(f"Error in message loop: {e}")
                await asyncio.sleep(1)
    
    async def _handle_server_message(self, message: dict):
        """Handle incoming commands from server."""
        try:
            message_type = message.get("type")
            message_id = message.get("id")
            
            # Check if this is a farm-wrap RPC message (has 'action' and 'correlation_id')
            if "action" in message and "correlation_id" in message:
                logger.info(f"Received farm-wrap RPC message: {message['action']}")
                await self._execute_farmwrap_rpc_command(message)
                return
            
            # Enhanced debugging for other message types
            logger.debug(f"Received message type: {message_type}, id: {message_id}")
            logger.debug(f"Full message received: {message}")
            
            if message_type == "automation_command":
                await self._execute_automation_command(message_id, message)
            elif message_type == "rpc_call":  # Add RPC call handling
                await self._execute_rpc_command(message_id, message)
            elif message_type == "ping":
                await self._handle_ping(message_id)
            elif message_type == "status_request":
                await self._send_status_update()
            else:
                logger.warning(f"Unknown message type: {message_type}")
                logger.warning(f"Full message content: {message}")
                logger.warning(f"Message keys: {list(message.keys()) if isinstance(message, dict) else 'Not a dict'}")
                
        except Exception as e:
            logger.error(f"Error handling server message: {e}")
            await self._send_error_response(message.get("id"), str(e))
    
    async def _execute_automation_command(self, command_id: str, command: dict):
        """Execute mobile automation command locally."""
        try:
            action = command.get("action")
            params = command.get("params", {})
            
            logger.info(f"Executing command: {action}")
            
            # Route to appropriate handler
            handler_name = f"_handle_{action}"
            if hasattr(self, handler_name):
                handler = getattr(self, handler_name)
                result = await handler(params)
                await self._send_success_response(command_id, result)
            else:
                await self._send_error_response(command_id, f"Unknown action: {action}", "UNKNOWN_ACTION")
                
        except ActionableError as ae:
            await self._send_error_response(command_id, str(ae), "ACTIONABLE_ERROR")
        except Exception as e:
            logger.error(f"Error executing command {command_id}: {e}")
            await self._send_error_response(command_id, str(e), "INTERNAL_ERROR")
    
    async def _execute_rpc_command(self, command_id: str, command: dict):
        """Execute RPC command received via WebSocket from S-Enricher."""
        try:
            method = command.get("method")
            params = command.get("params", {})
            
            logger.info(f"Executing RPC command: {method}")
            logger.debug(f"RPC params: {params}")
            
            # Route to appropriate handler - same as automation commands
            handler_name = f"_handle_{method}"
            if hasattr(self, handler_name):
                handler = getattr(self, handler_name)
                result = await handler(params)
                await self._send_rpc_response(command_id, result)
            else:
                await self._send_rpc_error_response(command_id, f"Unknown method: {method}")
                
        except ActionableError as ae:
            await self._send_rpc_error_response(command_id, str(ae))
        except Exception as e:
            logger.error(f"Error executing RPC command {command_id}: {e}")
            await self._send_rpc_error_response(command_id, str(e))
    
    async def _execute_farmwrap_rpc_command(self, message: dict):
        """Execute farm-wrap RPC command received via WebSocket."""
        try:
            action = message.get("action")
            payload = message.get("payload", [])
            correlation_id = message.get("correlation_id")
            execution_id = message.get("execution_id")
            
            logger.info(f"Executing farm-wrap RPC command: {action}")
            logger.debug(f"RPC payload: {payload}")
            
            # Convert payload to params (payload is usually a list with params as first item)
            params = payload[0] if payload else {}
            
            # Route to appropriate handler - same pattern as automation commands
            handler_name = f"_handle_{action}"
            if hasattr(self, handler_name):
                handler = getattr(self, handler_name)
                result = await handler(params)
                logger.info(f"Successfully executed {action}, result: {result}")
                await self._send_farmwrap_rpc_response(correlation_id, True, result)
            else:
                error_msg = f"Unknown action: {action}"
                logger.error(error_msg)
                await self._send_farmwrap_rpc_response(correlation_id, False, error_msg)
                raise Exception(error_msg)
                
        except ActionableError as ae:
            logger.error(f"ActionableError in farm-wrap RPC: {ae}")
            await self._send_farmwrap_rpc_response(correlation_id, False, str(ae))
        except Exception as e:
            logger.error(f"Error executing farm-wrap RPC command: {e}")
            await self._send_farmwrap_rpc_response(correlation_id, False, str(e))
    
    async def _handle_ping(self, ping_id: str):
        """Handle ping from server."""
        await self._send_success_response(ping_id, {"status": "pong"})
    
    async def _send_success_response(self, request_id: str, data: Any):
        """Send success response to server."""
        response = {
            "id": request_id,
            "type": "automation_result",
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat() + "Z"
        }
        await self.connection_manager.send_message(response)
    
    async def _send_error_response(self, request_id: str, message: str, code: str = "ERROR"):
        """Send error response to server."""
        response = {
            "id": request_id,
            "type": "automation_result",
            "success": False,
            "error": {
                "type": "ActionableError",
                "message": message,
                "code": code
            },
            "timestamp": datetime.now().isoformat() + "Z"
        }
        await self.connection_manager.send_message(response)
    
    async def _send_rpc_response(self, request_id: str, data: Any):
        """Send RPC success response to S-Enricher."""
        response = {
            "id": request_id,
            "type": "rpc_response",
            "success": True,
            "result": data,
            "timestamp": datetime.now().isoformat() + "Z"
        }
        await self.connection_manager.send_message(response)
        logger.debug(f"Sent RPC success response for {request_id}")
    
    async def _send_rpc_error_response(self, request_id: str, message: str):
        """Send RPC error response to S-Enricher."""
        response = {
            "id": request_id,
            "type": "rpc_response", 
            "success": False,
            "error": message,
            "timestamp": datetime.now().isoformat() + "Z"
        }
        await self.connection_manager.send_message(response)
        logger.debug(f"Sent RPC error response for {request_id}: {message}")
    
    async def _send_farmwrap_rpc_response(self, correlation_id: str, success: bool, data: Any):
        """Send farm-wrap RPC response back to S-Enricher via WebSocket Gateway."""
        try:
            # Farm-wrap expects ClientEventPayload format with 'event' field
            response = {
                "event": "result" if success else "error",
                "correlation_id": correlation_id,
                "data": data,
                "timestamp": datetime.now().isoformat() + "Z"
            }
            
            await self.connection_manager.send_message(response)
            logger.info(f"Sent farm-wrap RPC response: success={success}, correlation_id={correlation_id}")
            
        except Exception as e:
            logger.error(f"Failed to send farm-wrap RPC response: {e}")
    
    async def _send_status_update(self):
        """Send status update to server."""
        try:
            devices = await self.device_manager.list_all_devices()
            status = {
                "event": "ready",  # Use 'ready' event as expected by S-Enricher
                "session_id": self.current_session.session_id if self.current_session else None,
                "execution_id": None,  # No specific execution for status updates
                "data": {
                    "connected_devices": [device.model_dump() for device in devices],
                    "selected_device": self.selected_device.model_dump() if self.selected_device else None,
                    "service_status": "running",
                    "timestamp": datetime.now().isoformat() + "Z"
                }
            }
            await self.connection_manager.send_message(status)
            logger.info(f"Sent status update with {len(devices)} devices")
        except Exception as e:
            logger.error(f"Failed to send status update: {e}")
    
    # Device Management Handlers
    async def _handle_mobile_list_available_devices(self, params: dict) -> dict:
        """List all available devices."""
        devices = await self.device_manager.list_all_devices()
        return {"devices": [device.model_dump() for device in devices]}
    
    async def _handle_mobile_use_default_device(self, params: dict) -> dict:
        """Auto-select single available device."""
        device = await self.device_manager.select_default_device()
        self.selected_device = device
        self.robot = await self.device_manager.get_robot(device)
        return {"selected_device": device.model_dump()}
    
    async def _handle_mobile_use_device(self, params: dict) -> dict:
        """Select specific device by ID."""
        device_id = params.get("device_id")
        if not device_id:
            raise ActionableError("device_id parameter is required")
        
        device_info = await self.device_manager.get_device_info(device_id)
        if not device_info:
            raise ActionableError(f"Device {device_id} not found")
        
        self.selected_device = device_info
        self.robot = await self.device_manager.get_robot(device_info)
        return {"selected_device": device_info.model_dump()}
    
    # Screen Interaction Handlers
    async def _handle_mobile_click_on_screen_at_coordinates(self, params: dict) -> dict:
        """Tap at coordinates."""
        if not self.robot:
            raise ActionableError("No device selected")
        
        x = params.get("x")
        y = params.get("y")
        if x is None or y is None:
            raise ActionableError("x and y coordinates are required")
        
        await self.robot.tap(x, y)
        return {"message": f"Tapped at ({x}, {y})"}
    
    async def _handle_mobile_take_screenshot(self, params: dict) -> dict:
        """Take screenshot."""
        if not self.robot:
            raise ActionableError("No device selected")
        
        screenshot = await self.robot.get_screenshot()
        import base64
        screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
        return {"screenshot": screenshot_b64}
    
    async def _handle_swipe_on_screen(self, params: dict) -> dict:
        """Swipe in direction."""
        if not self.robot:
            raise ActionableError("No device selected")
        
        direction = params.get("direction")
        if not direction:
            raise ActionableError("direction parameter is required")
        
        try:
            swipe_dir = SwipeDirection(direction)
        except ValueError:
            raise ActionableError(f"Invalid direction: {direction}")
        
        await self.robot.swipe(swipe_dir)
        return {"message": f"Swiped {direction}"}
    
    async def _handle_mobile_type_keys(self, params: dict) -> dict:
        """Type text."""
        if not self.robot:
            raise ActionableError("No device selected")
        
        text = params.get("text", "")
        await self.robot.send_keys(text)
        return {"message": f"Typed: {text}"}
    
    async def _handle_mobile_press_button(self, params: dict) -> dict:
        """Press physical button."""
        if not self.robot:
            raise ActionableError("No device selected")
        
        button = params.get("button")
        if not button:
            raise ActionableError("button parameter is required")
        
        try:
            button_enum = Button(button)
        except ValueError:
            raise ActionableError(f"Invalid button: {button}")
        
        await self.robot.press_button(button_enum)
        return {"message": f"Pressed {button}"}
    
    async def _handle_mobile_get_screen_size(self, params: dict) -> dict:
        """Get screen dimensions."""
        if not self.robot:
            raise ActionableError("No device selected")
        
        screen_size = await self.robot.get_screen_size()
        return {"screen_size": screen_size.model_dump()}
    
    # App Management Handlers
    async def _handle_mobile_launch_app(self, params: dict) -> dict:
        """Launch app by package name."""
        if not self.robot:
            raise ActionableError("No device selected")
        
        package_name = params.get("package_name")
        if not package_name:
            raise ActionableError("package_name parameter is required")
        
        await self.robot.launch_app(package_name)
        return {"message": f"Launched app: {package_name}"}
    
    async def _handle_mobile_terminate_app(self, params: dict) -> dict:
        """Terminate app by package name."""
        if not self.robot:
            raise ActionableError("No device selected")
        
        package_name = params.get("package_name")
        if not package_name:
            raise ActionableError("package_name parameter is required")
        
        await self.robot.terminate_app(package_name)
        return {"message": f"Terminated app: {package_name}"}
    
    async def _handle_mobile_list_elements_on_screen(self, params: dict) -> dict:
        """Get screen hierarchy/elements."""
        if not self.robot:
            raise ActionableError("No device selected")
        
        # Get screen elements from robot
        elements = await self.robot.get_elements()
        return {"elements": elements}
    
    async def _handle_mobile_list_apps(self, params: dict) -> dict:
        """List installed apps."""
        if not self.robot:
            raise ActionableError("No device selected")
        
        # Get installed apps from robot
        apps = await self.robot.get_installed_apps()
        return {"apps": apps}
    
    async def _handle_mobile_check_app_running(self, params: dict) -> dict:
        """Check if specific app is running."""
        if not self.robot:
            raise ActionableError("No device selected")
        
        package_name = params.get("package_name")
        if not package_name:
            raise ActionableError("package_name parameter is required")
        
        # Check if app is running
        is_running = await self.robot.is_app_running(package_name)
        return {"is_running": is_running}
    
    async def _handle_mobile_get_running_apps(self, params: dict) -> dict:
        """Get list of currently running apps."""
        if not self.robot:
            raise ActionableError("No device selected")
        
        # Get running apps from robot
        running_apps = await self.robot.get_running_apps()
        return {"apps": running_apps}
    
    async def stop(self):
        """Stop the WebSocket client."""
        logger.info("Stopping WebSocket client")
        
        # Close WebSocket connection
        await self.connection_manager.close()
        
        # Cleanup robot
        if self.robot and hasattr(self.robot, 'cleanup'):
            try:
                await self.robot.cleanup()
            except Exception as e:
                logger.warning(f"Failed to cleanup robot: {e}")
        
        # Delete session from S-Enricher
        if self.current_session:
            try:
                success = self.session_manager.delete_session()
                if success:
                    logger.info(f"Session {self.current_session.session_id} deleted successfully")
                else:
                    logger.warning("Failed to delete session from S-Enricher")
            except Exception as e:
                logger.error(f"Error deleting session: {e}")
            finally:
                self.current_session = None


# Global client instance
client: Optional[WebSocketMobileClient] = None


async def start_client(server_url: str, retry_config: Optional[RetryConfig] = None) -> bool:
    """Start the WebSocket client."""
    global client
    client = WebSocketMobileClient(server_url, retry_config)
    return await client.start()


async def stop_client():
    """Stop the WebSocket client."""
    global client
    if client:
        await client.stop()
        client = None
    
    # Cleanup global session manager
    cleanup_session_manager()
