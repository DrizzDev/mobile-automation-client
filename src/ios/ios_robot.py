"""iOS robot implementation using WebDriverAgent and simctl."""

import asyncio
import subprocess
import json
import requests
import base64
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin

from robot import Robot, ActionableError
from enums import (
    InstalledApp,
    ScreenElement,
    ScreenSize,
    SwipeDirection,
    Button,
    Orientation,
    LogOptions,
    DeviceInfo,
    DeviceType,
)
from config import config
from utils.logger import get_logger

logger = get_logger(__name__)


class SimctlManager:
    """iOS Simulator management using xcrun simctl."""

    def __init__(self):
        self.simctl_path = config.simctl_path
        self.timeout = 30

    async def list_booted_simulators(self) -> List[DeviceInfo]:
        """Get list of booted iOS simulators."""
        try:
            result = await self._run_simctl_command(["list", "devices", "--json"])
            data = json.loads(result.stdout)
            
            devices = []
            for runtime, device_list in data.get("devices", {}).items():
                if "iOS" in runtime:
                    ios_version = runtime.split(".")[-1].replace("-", ".")
                    
                    for device in device_list:
                        if device.get("state") == "Booted":
                            devices.append(DeviceInfo(
                                id=device["udid"],
                                name=f"{device['name']} (iOS {ios_version})",
                                type=DeviceType.SIMULATOR,
                                platform_version=ios_version,
                                model=device["name"],
                                is_emulator=True,
                                status="booted"
                            ))
            
            return devices
            
        except Exception as e:
            logger.error(f"Failed to list simulators: {e}")
            return []

    async def get_simulator_info(self, udid: str) -> Optional[DeviceInfo]:
        """Get detailed information about a simulator."""
        try:
            result = await self._run_simctl_command(["list", "devices", "--json"])
            data = json.loads(result.stdout)
            
            for runtime, device_list in data.get("devices", {}).items():
                for device in device_list:
                    if device["udid"] == udid:
                        ios_version = runtime.split(".")[-1].replace("-", ".") if "iOS" in runtime else "Unknown"
                        
                        return DeviceInfo(
                            id=udid,
                            name=f"{device['name']} (iOS {ios_version})",
                            type=DeviceType.SIMULATOR,
                            platform_version=ios_version,
                            model=device["name"],
                            is_emulator=True,
                            status=device.get("state", "unknown").lower()
                        )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get simulator info for {udid}: {e}")
            return None

    async def _run_simctl_command(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run simctl command with timeout and error handling."""
        cmd = self.simctl_path.split() + args
        
        try:
            result = await asyncio.wait_for(
                asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                ),
                timeout=self.timeout
            )
            
            stdout, stderr = await result.communicate()
            
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=result.returncode,
                stdout=stdout.decode('utf-8', errors='ignore'),
                stderr=stderr.decode('utf-8', errors='ignore')
            )
            
        except asyncio.TimeoutError:
            raise ActionableError(f"Simctl command timed out after {self.timeout}s: {' '.join(cmd)}")
        except FileNotFoundError:
            raise ActionableError(f"Simctl not found. Please install Xcode and command line tools.")


class WebDriverAgent:
    """WebDriverAgent client for iOS automation."""

    def __init__(self, host: str = "localhost", port: int = None):
        self.host = host
        self.port = port or config.wda_port
        self.base_url = f"http://{host}:{self.port}"
        self.session_id: Optional[str] = None
        self.timeout = 30

    async def create_session(self) -> str:
        """Create a new WebDriverAgent session."""
        try:
            response = requests.post(
                urljoin(self.base_url, "/session"),
                json={"capabilities": {"alwaysMatch": {}}},
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            self.session_id = data["sessionId"]
            return self.session_id
            
        except Exception as e:
            raise ActionableError(f"Failed to create WebDriverAgent session: {e}")

    async def delete_session(self) -> None:
        """Delete the current session."""
        if self.session_id:
            try:
                response = requests.delete(
                    urljoin(self.base_url, f"/session/{self.session_id}"),
                    timeout=self.timeout
                )
                response.raise_for_status()
                
            except Exception as e:
                logger.warning(f"Failed to delete session: {e}")
            finally:
                self.session_id = None

    def _ensure_session(self) -> None:
        """Ensure we have an active session."""
        if not self.session_id:
            raise ActionableError("No active WebDriverAgent session. Call create_session() first.")

    async def get_screen_size(self) -> ScreenSize:
        """Get screen dimensions."""
        self._ensure_session()
        
        try:
            response = requests.get(
                urljoin(self.base_url, f"/session/{self.session_id}/wda/screen"),
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()["value"]
            return ScreenSize(
                width=int(data["statusBarSize"]["width"]),
                height=int(data["statusBarSize"]["height"])
            )
            
        except Exception as e:
            raise Exception(f"Failed to get screen size: {e}")

    async def get_screenshot(self) -> bytes:
        """Get screenshot as PNG bytes."""
        self._ensure_session()
        
        try:
            response = requests.get(
                urljoin(self.base_url, f"/session/{self.session_id}/screenshot"),
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            screenshot_b64 = data["value"]
            return base64.b64decode(screenshot_b64)
            
        except Exception as e:
            raise Exception(f"Failed to get screenshot: {e}")

    async def tap(self, x: int, y: int) -> None:
        """Tap at coordinates."""
        self._ensure_session()
        
        try:
            action = {
                "actions": [{
                    "type": "pointer",
                    "id": "finger1",
                    "actions": [
                        {"type": "pointerMove", "duration": 0, "x": x, "y": y},
                        {"type": "pointerDown", "button": 0},
                        {"type": "pointerUp", "button": 0}
                    ]
                }]
            }
            
            response = requests.post(
                urljoin(self.base_url, f"/session/{self.session_id}/actions"),
                json=action,
                timeout=self.timeout
            )
            response.raise_for_status()
            
        except Exception as e:
            raise Exception(f"Failed to tap at ({x}, {y}): {e}")

    async def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 300) -> None:
        """Swipe from start to end coordinates."""
        self._ensure_session()
        
        try:
            action = {
                "actions": [{
                    "type": "pointer",
                    "id": "finger1",
                    "actions": [
                        {"type": "pointerMove", "duration": 0, "x": start_x, "y": start_y},
                        {"type": "pointerDown", "button": 0},
                        {"type": "pointerMove", "duration": duration, "x": end_x, "y": end_y},
                        {"type": "pointerUp", "button": 0}
                    ]
                }]
            }
            
            response = requests.post(
                urljoin(self.base_url, f"/session/{self.session_id}/actions"),
                json=action,
                timeout=self.timeout
            )
            response.raise_for_status()
            
        except Exception as e:
            raise Exception(f"Failed to swipe from ({start_x}, {start_y}) to ({end_x}, {end_y}): {e}")


# IosManager class removed - only simulator support is needed


class IosRobot(Robot):
    """iOS device automation using WebDriverAgent."""

    def __init__(self, device_info: DeviceInfo):
        self.device_info = device_info
        self.wda = WebDriverAgent()
        self.session_active = False

    async def _ensure_session(self) -> None:
        """Ensure WebDriverAgent session is active."""
        if not self.session_active:
            await self.wda.create_session()
            self.session_active = True

    async def cleanup(self) -> None:
        """Clean up WebDriverAgent session."""
        if self.session_active:
            await self.wda.delete_session()
            self.session_active = False

    # Device lifecycle
    async def list_apps(self) -> List[InstalledApp]:
        """List installed applications."""
        await self._ensure_session()
        
        # This is a placeholder - WebDriverAgent doesn't provide app listing directly
        # In a full implementation, you'd use additional iOS tools
        return [
            InstalledApp(
                package_name="com.apple.mobilesafari",
                app_name="Safari",
                is_system_app=True
            ),
            InstalledApp(
                package_name="com.apple.mobilemail",
                app_name="Mail",
                is_system_app=True
            )
        ]

    async def launch_app(self, package_name: str) -> None:
        """Launch application by bundle ID."""
        await self._ensure_session()
        
        try:
            response = requests.post(
                urljoin(self.wda.base_url, f"/session/{self.wda.session_id}/wda/apps/launch"),
                json={"bundleId": package_name},
                timeout=self.wda.timeout
            )
            response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Failed to launch app {package_name}: {e}")
            raise

    async def get_installed_apps(self) -> List[dict]:
        """Get installed apps in dictionary format."""
        try:
            apps = await self.list_apps()
            return [
                {
                    "package_name": app.package_name,
                    "app_name": app.app_name,
                    "is_system_app": app.is_system_app
                }
                for app in apps
            ]
        except Exception as e:
            logger.error(f"Failed to get installed apps: {e}")
            raise

    async def terminate_app(self, package_name: str) -> None:
        """Terminate application."""
        await self._ensure_session()
        
        try:
            response = requests.post(
                urljoin(self.wda.base_url, f"/session/{self.wda.session_id}/wda/apps/terminate"),
                json={"bundleId": package_name},
                timeout=self.wda.timeout
            )
            response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Failed to terminate app {package_name}: {e}")
            raise
    
    async def is_app_running(self, package_name: str) -> bool:
        """Check if specific app is currently running."""
        await self._ensure_session()
        
        try:
            # Get current app state
            response = requests.get(
                urljoin(self.wda.base_url, f"/session/{self.wda.session_id}/wda/apps/state"),
                params={"bundleId": package_name},
                timeout=self.wda.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            # State values: 0=not installed, 1=not running, 2=running in background, 3=running in foreground, 4=running
            app_state = data.get("value", 0)
            return app_state >= 2  # Running in background or foreground
            
        except Exception as e:
            logger.error(f"Failed to check if app {package_name} is running: {e}")
            return False
    
    async def get_running_apps(self) -> List[dict]:
        """Get list of currently running apps."""
        await self._ensure_session()
        
        try:
            # This is a simplified implementation
            # iOS doesn't easily provide a list of all running apps due to security restrictions
            # In practice, you'd need to use private APIs or system tools
            
            # For now, return a placeholder with the current foreground app if available
            response = requests.get(
                urljoin(self.wda.base_url, f"/session/{self.wda.session_id}/wda/activeAppInfo"),
                timeout=self.wda.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            active_app = data.get("value", {})
            
            if active_app and active_app.get("bundleId"):
                return [{
                    "package_name": active_app["bundleId"],
                    "is_foreground": True,
                    "app_name": active_app.get("name", "Unknown")
                }]
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get running apps: {e}")
            return []

    # Screen interaction
    async def tap(self, x: int, y: int) -> None:
        """Tap at coordinates."""
        await self._ensure_session()
        await self.wda.tap(x, y)

    async def long_press(self, x: int, y: int) -> None:
        """Long press at coordinates."""
        await self._ensure_session()
        
        try:
            action = {
                "actions": [{
                    "type": "pointer",
                    "id": "finger1",
                    "actions": [
                        {"type": "pointerMove", "duration": 0, "x": x, "y": y},
                        {"type": "pointerDown", "button": 0},
                        {"type": "pause", "duration": 1000},
                        {"type": "pointerUp", "button": 0}
                    ]
                }]
            }
            
            response = requests.post(
                urljoin(self.wda.base_url, f"/session/{self.wda.session_id}/actions"),
                json=action,
                timeout=self.wda.timeout
            )
            response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Failed to long press at ({x}, {y}): {e}")
            raise

    async def swipe(self, direction: SwipeDirection) -> None:
        """Swipe in direction."""
        await self._ensure_session()
        
        try:
            screen_size = await self.get_screen_size()
            center_x = screen_size.width // 2
            center_y = screen_size.height // 2
            distance = min(screen_size.width, screen_size.height) // 3
            
            if direction == SwipeDirection.UP:
                start_x, start_y = center_x, center_y + distance
                end_x, end_y = center_x, center_y - distance
            elif direction == SwipeDirection.DOWN:
                start_x, start_y = center_x, center_y - distance
                end_x, end_y = center_x, center_y + distance
            elif direction == SwipeDirection.LEFT:
                start_x, start_y = center_x + distance, center_y
                end_x, end_y = center_x - distance, center_y
            elif direction == SwipeDirection.RIGHT:
                start_x, start_y = center_x - distance, center_y
                end_x, end_y = center_x + distance, center_y
            
            await self.wda.swipe(start_x, start_y, end_x, end_y)
            
        except Exception as e:
            logger.error(f"Failed to swipe {direction}: {e}")
            raise

    async def swipe_from_coordinate(
        self, x: int, y: int, direction: SwipeDirection, distance: Optional[int] = None
    ) -> None:
        """Swipe from specific coordinate."""
        await self._ensure_session()
        
        try:
            distance = distance or 200
            
            if direction == SwipeDirection.UP:
                end_x, end_y = x, y - distance
            elif direction == SwipeDirection.DOWN:
                end_x, end_y = x, y + distance
            elif direction == SwipeDirection.LEFT:
                end_x, end_y = x - distance, y
            elif direction == SwipeDirection.RIGHT:
                end_x, end_y = x + distance, y
            
            await self.wda.swipe(x, y, end_x, end_y)
            
        except Exception as e:
            logger.error(f"Failed to swipe from ({x}, {y}) {direction}: {e}")
            raise

    # Input
    async def send_keys(self, text: str) -> None:
        """Send text input."""
        await self._ensure_session()
        
        try:
            response = requests.post(
                urljoin(self.wda.base_url, f"/session/{self.wda.session_id}/wda/keys"),
                json={"value": list(text)},
                timeout=self.wda.timeout
            )
            response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Failed to send keys '{text}': {e}")
            raise

    async def press_button(self, button: Button) -> None:
        """Press physical button."""
        await self._ensure_session()
        
        try:
            button_map = {
                Button.HOME: "home",
                Button.VOLUME_UP: "volumeUp",
                Button.VOLUME_DOWN: "volumeDown",
            }
            
            if button not in button_map:
                raise ValueError(f"Unsupported button for iOS: {button}")
            
            response = requests.post(
                urljoin(self.wda.base_url, f"/session/{self.wda.session_id}/wda/pressButton"),
                json={"name": button_map[button]},
                timeout=self.wda.timeout
            )
            response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Failed to press button {button}: {e}")
            raise

    async def open_url(self, url: str) -> None:
        """Open URL in Safari."""
        await self._ensure_session()
        
        try:
            response = requests.post(
                urljoin(self.wda.base_url, f"/session/{self.wda.session_id}/url"),
                json={"url": url},
                timeout=self.wda.timeout
            )
            response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Failed to open URL {url}: {e}")
            raise

    # Screen state
    async def get_screenshot(self) -> bytes:
        """Get screenshot as PNG bytes."""
        await self._ensure_session()
        return await self.wda.get_screenshot()

    async def get_screen_size(self) -> ScreenSize:
        """Get screen dimensions."""
        await self._ensure_session()
        return await self.wda.get_screen_size()

    async def get_elements_on_screen(self) -> List[ScreenElement]:
        """Get UI element hierarchy."""
        await self._ensure_session()
        
        try:
            response = requests.get(
                urljoin(self.wda.base_url, f"/session/{self.wda.session_id}/source"),
                timeout=self.wda.timeout
            )
            response.raise_for_status()
            
            # This would need proper XML parsing similar to Android
            # For now, return empty list as placeholder
            return []
            
        except Exception as e:
            logger.error(f"Failed to get UI elements: {e}")
            return []
    
    async def get_elements(self) -> List[dict]:
        """Get screen elements in dictionary format for API compatibility."""
        await self._ensure_session()
        
        try:
            # Use WDA element tree endpoint for better iOS app info
            response = requests.get(
                urljoin(self.wda.base_url, f"/session/{self.wda.session_id}/wda/element/tree"),
                timeout=self.wda.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            tree_data = data.get("value", {})
            
            def parse_ios_element(element: dict) -> dict:
                """Convert iOS element tree to dictionary format."""
                bounds = element.get("rect", {})
                element_dict = {
                    "class_name": element.get("type"),
                    "text": element.get("value") or element.get("label"),
                    "content_desc": element.get("name"),
                    "resource_id": element.get("identifier"),
                    "bounds": {
                        "x": bounds.get("x", 0),
                        "y": bounds.get("y", 0),
                        "width": bounds.get("width", 0),
                        "height": bounds.get("height", 0)
                    },
                    "clickable": element.get("enabled", False),
                    "focusable": element.get("focused", False),
                    "enabled": element.get("enabled", True),
                    "visible": element.get("visible", True),
                    "children": []
                }
                
                # Try to extract package from bundle ID or class name
                package = None
                class_name = element.get("type", "")
                if "." in class_name:
                    parts = class_name.split(".")
                    if len(parts) >= 3:  # Typical iOS bundle format: com.company.app.Class
                        package = ".".join(parts[:3])  # Take first 3 parts
                
                if package:
                    element_dict["package"] = package
                
                # Parse children recursively
                for child in element.get("children", []):
                    element_dict["children"].append(parse_ios_element(child))
                
                return element_dict
            
            if tree_data:
                return [parse_ios_element(tree_data)]
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get elements: {e}")
            return []

    async def set_orientation(self, orientation: Orientation) -> None:
        """Set screen orientation."""
        await self._ensure_session()
        
        try:
            orientation_map = {
                Orientation.PORTRAIT: "PORTRAIT",
                Orientation.LANDSCAPE: "LANDSCAPE"
            }
            
            if orientation not in orientation_map:
                raise ValueError(f"Unsupported orientation: {orientation}")
            
            response = requests.post(
                urljoin(self.wda.base_url, f"/session/{self.wda.session_id}/orientation"),
                json={"orientation": orientation_map[orientation]},
                timeout=self.wda.timeout
            )
            response.raise_for_status()
            
        except Exception as e:
            logger.error(f"Failed to set orientation {orientation}: {e}")
            raise

    async def get_orientation(self) -> Orientation:
        """Get current orientation."""
        await self._ensure_session()
        
        try:
            response = requests.get(
                urljoin(self.wda.base_url, f"/session/{self.wda.session_id}/orientation"),
                timeout=self.wda.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            orientation_str = data["value"]
            
            if orientation_str == "LANDSCAPE":
                return Orientation.LANDSCAPE
            else:
                return Orientation.PORTRAIT
            
        except Exception as e:
            logger.error(f"Failed to get orientation: {e}")
            return Orientation.PORTRAIT

    # Debugging
    async def get_device_logs(self, options: Optional[LogOptions] = None) -> str:
        """Get device logs (placeholder for iOS)."""
        # iOS device logs are more complex to access
        # Would typically require additional tools like deviceconsole or ios-deploy
        return "iOS device logs not implemented yet"
