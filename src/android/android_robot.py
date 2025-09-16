"""Android robot implementation using ADB."""

import asyncio
import subprocess
import xml.etree.ElementTree as ET
from typing import List, Optional, Dict, Any
import re
import json
from pathlib import Path

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


class AndroidDeviceManager:
    """Android device discovery and management."""

    def __init__(self):
        self.adb_path = config.adb_path
        self.timeout = config.adb_timeout
        self.max_buffer_size = config.adb_max_buffer_size

    async def get_connected_devices(self) -> List[DeviceInfo]:
        """Get list of connected Android devices."""
        try:
            result = await self._run_adb_command(["devices", "-l"])
            devices = []
            
            for line in result.stdout.splitlines():
                if "device" in line and not line.startswith("List of devices"):
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == "device":
                        device_id = parts[0]
                        
                        # Extract device info from additional parameters
                        model = "Unknown"
                        for part in parts[2:]:
                            if part.startswith("model:"):
                                model = part.split(":", 1)[1]
                                break
                        
                        # Check if it's an emulator
                        is_emulator = device_id.startswith("emulator-")
                        
                        devices.append(DeviceInfo(
                            id=device_id,
                            name=f"Android Device ({model})",
                            type=DeviceType.ANDROID,
                            model=model,
                            is_emulator=is_emulator,
                            status="connected"
                        ))
            
            return devices
            
        except Exception as e:
            logger.error(f"Failed to get connected devices: {e}")
            return []

    async def get_device_info(self, device_id: str) -> Optional[DeviceInfo]:
        """Get detailed information about a specific device."""
        try:
            # Get device properties
            result = await self._run_adb_command(["-s", device_id, "shell", "getprop"])
            props = {}
            
            for line in result.stdout.splitlines():
                match = re.match(r'\[(.+?)\]: \[(.+?)\]', line)
                if match:
                    key, value = match.groups()
                    props[key] = value
            
            model = props.get("ro.product.model", "Unknown")
            version = props.get("ro.build.version.release", "Unknown")
            is_emulator = "goldfish" in props.get("ro.hardware", "")
            
            return DeviceInfo(
                id=device_id,
                name=f"Android {version} ({model})",
                type=DeviceType.ANDROID,
                platform_version=version,
                model=model,
                is_emulator=is_emulator,
                status="connected"
            )
            
        except Exception as e:
            logger.error(f"Failed to get device info for {device_id}: {e}")
            return None

    async def _run_adb_command(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run ADB command with timeout and error handling."""
        cmd = [self.adb_path] + args
        
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
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace')
            )
            
        except asyncio.TimeoutError:
            raise ActionableError(f"ADB command timed out after {self.timeout}s: {' '.join(cmd)}")
        except FileNotFoundError:
            raise ActionableError(f"ADB not found at {self.adb_path}. Please install Android SDK.")


class AndroidRobot(Robot):
    """Android device automation using ADB."""

    def __init__(self, device_info: DeviceInfo):
        self.device_info = device_info
        self.device_id = device_info.id
        self.adb_manager = AndroidDeviceManager()

    async def _run_shell_command(self, command: str) -> str:
        """Run shell command on Android device."""
        result = await self.adb_manager._run_adb_command([
            "-s", self.device_id, "shell", command
        ])
        
        if result.returncode != 0:
            raise Exception(f"Shell command failed: {result.stderr}")
        
        return result.stdout.strip()

    # Device lifecycle
    async def list_apps(self) -> List[InstalledApp]:
        """List installed applications."""
        try:
            # Get all packages
            packages_output = await self._run_shell_command("pm list packages -f")
            apps = []
            
            for line in packages_output.splitlines():
                if line.startswith("package:"):
                    # Extract package info: package:/path/to/apk=com.example.app
                    match = re.match(r'package:(.+?)=(.+)', line)
                    if match:
                        apk_path, package_name = match.groups()
                        
                        # Get app label
                        try:
                            label_output = await self._run_shell_command(
                                f"pm list packages -f {package_name} | head -1"
                            )
                            # For now, use package name as app name
                            app_name = package_name.split('.')[-1].title()
                            
                            is_system = "/system/" in apk_path
                            
                            apps.append(InstalledApp(
                                package_name=package_name,
                                app_name=app_name,
                                is_system_app=is_system
                            ))
                            
                        except Exception:
                            # Skip apps we can't get info for
                            continue
            
            return apps
            
        except Exception as e:
            logger.error(f"Failed to list apps: {e}")
            raise

    async def launch_app(self, package_name: str) -> None:
        """Launch application by package name."""
        try:
            await self._run_shell_command(
                f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
            )
            
            # Wait a bit for app to start
            await asyncio.sleep(2)
            
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
        try:
            await self._run_shell_command(f"am force-stop {package_name}")
        except Exception as e:
            logger.error(f"Failed to terminate app {package_name}: {e}")
            raise
    
    async def is_app_running(self, package_name: str) -> bool:
        """Check if specific app is currently running."""
        try:
            # Get running apps and check if our package is in the list
            running_apps = await self.get_running_apps()
            
            for app in running_apps:
                if isinstance(app, dict) and app.get("package_name") == package_name:
                    return True
                elif isinstance(app, str) and app == package_name:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check if app {package_name} is running: {e}")
            return False
    
    async def get_running_apps(self) -> List[dict]:
        """Get list of currently running apps."""
        try:
            # Use dumpsys to get running processes
            output = await self._run_shell_command("dumpsys activity activities | grep 'ResumedActivity'")
            running_apps = []
            
            for line in output.splitlines():
                # Look for pattern like: ResumedActivity: ActivityRecord{...} u0 com.example.app/.MainActivity t123}
                match = re.search(r'\s+([a-zA-Z0-9_.]+)/[a-zA-Z0-9_.]+', line)
                if match:
                    package_name = match.group(1)
                    running_apps.append({
                        "package_name": package_name,
                        "is_foreground": True
                    })
            
            # If no resumed activity found, try a different approach
            if not running_apps:
                # Get all running processes and filter for app packages
                ps_output = await self._run_shell_command("ps | grep -v 'root\|system\|shell\|radio'")
                for line in ps_output.splitlines():
                    parts = line.split()
                    if len(parts) > 8:  # Make sure we have enough columns
                        process_name = parts[-1]  # Last column is usually the process name
                        # Filter for app-like package names (contain dots)
                        if '.' in process_name and not process_name.startswith('/') and ':' not in process_name:
                            running_apps.append({
                                "package_name": process_name,
                                "is_foreground": False
                            })
            
            return running_apps
            
        except Exception as e:
            logger.error(f"Failed to get running apps: {e}")
            return []

    # Screen interaction
    async def tap(self, x: int, y: int) -> None:
        """Tap at coordinates."""
        try:
            await self._run_shell_command(f"input tap {x} {y}")
        except Exception as e:
            logger.error(f"Failed to tap at ({x}, {y}): {e}")
            raise

    async def long_press(self, x: int, y: int) -> None:
        """Long press at coordinates."""
        try:
            # Use swipe with same start/end coordinates and duration for long press
            await self._run_shell_command(f"input swipe {x} {y} {x} {y} 1000")
        except Exception as e:
            logger.error(f"Failed to long press at ({x}, {y}): {e}")
            raise

    async def swipe(self, direction: SwipeDirection) -> None:
        """Swipe in direction."""
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
            
            await self._run_shell_command(
                f"input swipe {start_x} {start_y} {end_x} {end_y} 300"
            )
            
        except Exception as e:
            logger.error(f"Failed to swipe {direction}: {e}")
            raise

    async def swipe_from_coordinate(
        self, x: int, y: int, direction: SwipeDirection, distance: Optional[int] = None
    ) -> None:
        """Swipe from specific coordinate."""
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
            
            await self._run_shell_command(f"input swipe {x} {y} {end_x} {end_y} 300")
            
        except Exception as e:
            logger.error(f"Failed to swipe from ({x}, {y}) {direction}: {e}")
            raise

    # Input
    async def send_keys(self, text: str) -> None:
        """Send text input."""
        try:
            # Escape special characters
            escaped_text = text.replace(' ', '%s').replace("'", "\\'")
            await self._run_shell_command(f"input text '{escaped_text}'")
        except Exception as e:
            logger.error(f"Failed to send keys '{text}': {e}")
            raise

    async def press_button(self, button: Button) -> None:
        """Press physical/virtual button."""
        try:
            key_codes = {
                Button.HOME: "KEYCODE_HOME",
                Button.BACK: "KEYCODE_BACK",
                Button.MENU: "KEYCODE_MENU",
                Button.VOLUME_UP: "KEYCODE_VOLUME_UP",
                Button.VOLUME_DOWN: "KEYCODE_VOLUME_DOWN",
                Button.POWER: "KEYCODE_POWER",
                Button.RECENT_APPS: "KEYCODE_APP_SWITCH",
            }
            
            if button not in key_codes:
                raise ValueError(f"Unsupported button: {button}")
            
            await self._run_shell_command(f"input keyevent {key_codes[button]}")
            
        except Exception as e:
            logger.error(f"Failed to press button {button}: {e}")
            raise

    async def open_url(self, url: str) -> None:
        """Open URL in default browser."""
        try:
            await self._run_shell_command(f"am start -a android.intent.action.VIEW -d '{url}'")
        except Exception as e:
            logger.error(f"Failed to open URL {url}: {e}")
            raise

    # Screen state
    async def get_screenshot(self) -> bytes:
        """Get screenshot as PNG bytes."""
        try:
            # Use raw subprocess to get binary data directly
            import subprocess
            cmd = [self.adb_manager.adb_path, "-s", self.device_id, "exec-out", "screencap", "-p"]
            
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                raise Exception(f"Screenshot failed: {stderr.decode('utf-8', errors='replace')}")
            
            return stdout  # Return raw binary data
            
        except Exception as e:
            logger.error(f"Failed to get screenshot: {e}")
            raise

    async def get_screen_size(self) -> ScreenSize:
        """Get screen dimensions."""
        try:
            output = await self._run_shell_command("wm size")
            # Output: "Physical size: 1080x1920"
            match = re.search(r'(\d+)x(\d+)', output)
            if match:
                width, height = map(int, match.groups())
                return ScreenSize(width=width, height=height)
            else:
                raise Exception("Could not parse screen size")
                
        except Exception as e:
            logger.error(f"Failed to get screen size: {e}")
            raise

    async def get_elements_on_screen(self) -> List[ScreenElement]:
        """Get UI element hierarchy."""
        try:
            # Get UI hierarchy XML
            await self._run_shell_command("uiautomator dump /sdcard/ui_dump.xml")
            xml_output = await self._run_shell_command("cat /sdcard/ui_dump.xml")
            
            # Parse XML
            root = ET.fromstring(xml_output)
            elements = []
            
            def parse_node(node: ET.Element) -> ScreenElement:
                bounds_str = node.get('bounds', '')
                bounds = {}
                
                # Parse bounds: "[0,0][1080,1920]"
                bounds_match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds_str)
                if bounds_match:
                    x1, y1, x2, y2 = map(int, bounds_match.groups())
                    bounds = {
                        'x': x1,
                        'y': y1,
                        'width': x2 - x1,
                        'height': y2 - y1
                    }
                
                element = ScreenElement(
                    class_name=node.get('class'),
                    text=node.get('text'),
                    content_desc=node.get('content-desc'),
                    resource_id=node.get('resource-id'),
                    bounds=bounds,
                    clickable=node.get('clickable', 'false').lower() == 'true',
                    focusable=node.get('focusable', 'false').lower() == 'true',
                    enabled=node.get('enabled', 'true').lower() == 'true',
                    visible=node.get('visible-to-user', 'true').lower() == 'true'
                )
                
                # Parse children recursively
                for child in node:
                    element.children.append(parse_node(child))
                
                return element
            
            # Parse all nodes
            for node in root.iter():
                if node.tag == 'node':
                    elements.append(parse_node(node))
                    break  # Usually there's one root node
            
            return elements
            
        except Exception as e:
            logger.error(f"Failed to get UI elements: {e}")
            return []
    
    async def get_elements(self) -> List[dict]:
        """Get screen elements in dictionary format for API compatibility."""
        try:
            elements = await self.get_elements_on_screen()
            
            def convert_element(element: ScreenElement) -> dict:
                """Convert ScreenElement to dictionary format."""
                element_dict = {
                    "class_name": element.class_name,
                    "text": element.text,
                    "content_desc": element.content_desc,
                    "resource_id": element.resource_id,
                    "bounds": element.bounds,
                    "clickable": element.clickable,
                    "focusable": element.focusable,
                    "enabled": element.enabled,
                    "visible": element.visible,
                    "children": []
                }
                
                # Try to extract package name from resource_id or class_name
                package = None
                if element.resource_id and ':' in element.resource_id:
                    package = element.resource_id.split(':')[0]
                elif element.class_name and '.' in element.class_name:
                    parts = element.class_name.split('.')
                    if len(parts) >= 2:
                        package = '.'.join(parts[:-1])  # Everything except the last part
                
                if package:
                    element_dict["package"] = package
                
                # Convert children recursively
                for child in element.children:
                    element_dict["children"].append(convert_element(child))
                
                return element_dict
            
            result = []
            for element in elements:
                result.append(convert_element(element))
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get elements: {e}")
            return []

    async def set_orientation(self, orientation: Orientation) -> None:
        """Set screen orientation."""
        try:
            if orientation == Orientation.PORTRAIT:
                await self._run_shell_command("settings put system user_rotation 0")
            elif orientation == Orientation.LANDSCAPE:
                await self._run_shell_command("settings put system user_rotation 1")
            elif orientation == Orientation.PORTRAIT_UPSIDE_DOWN:
                await self._run_shell_command("settings put system user_rotation 2")
            elif orientation == Orientation.LANDSCAPE_LEFT:
                await self._run_shell_command("settings put system user_rotation 3")
            else:
                raise ValueError(f"Unsupported orientation: {orientation}")
                
        except Exception as e:
            logger.error(f"Failed to set orientation {orientation}: {e}")
            raise

    async def get_orientation(self) -> Orientation:
        """Get current orientation."""
        try:
            output = await self._run_shell_command("settings get system user_rotation")
            rotation = int(output.strip())
            
            orientations = {
                0: Orientation.PORTRAIT,
                1: Orientation.LANDSCAPE,
                2: Orientation.PORTRAIT_UPSIDE_DOWN,
                3: Orientation.LANDSCAPE_LEFT
            }
            
            return orientations.get(rotation, Orientation.PORTRAIT)
            
        except Exception as e:
            logger.error(f"Failed to get orientation: {e}")
            return Orientation.PORTRAIT

    # Debugging
    async def get_device_logs(self, options: Optional[LogOptions] = None) -> str:
        """Get device logs."""
        try:
            cmd_parts = ["logcat", "-d"]  # -d for dump mode
            
            if options:
                if options.max_lines:
                    cmd_parts.extend(["-t", str(options.max_lines)])
                
                if options.level:
                    level_map = {
                        "debug": "D",
                        "info": "I", 
                        "warning": "W",
                        "error": "E"
                    }
                    if options.level.value in level_map:
                        cmd_parts.append(f"*:{level_map[options.level.value]}")
                
                if options.tag_filter:
                    cmd_parts.append(f"{options.tag_filter}:*")
            
            cmd = " ".join(cmd_parts)
            output = await self._run_shell_command(cmd)
            
            return output
            
        except Exception as e:
            logger.error(f"Failed to get device logs: {e}")
            raise
