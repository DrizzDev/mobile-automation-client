"""Device manager for mobile automation service."""

from typing import List, Optional, Dict, Any, Union
from src.robot import Robot, ActionableError
from src.types import DeviceInfo, DeviceType
from src.android.android_robot import AndroidDeviceManager, AndroidRobot
from src.ios.ios_robot import SimctlManager, IosRobot
from src.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DeviceManager:
    """Manages device discovery and robot instantiation."""

    def __init__(self):
        self.android_manager = AndroidDeviceManager()
        self.simctl_manager = SimctlManager()
        
        # Track active robots for cleanup
        self.active_robots: Dict[str, Robot] = {}

    async def list_all_devices(self) -> List[DeviceInfo]:
        """List all available devices from all platforms."""
        all_devices = []
        
        try:
            # Get Android devices
            android_devices = await self.android_manager.get_connected_devices()
            all_devices.extend(android_devices)
            
            # Get iOS simulators
            simulators = await self.simctl_manager.list_booted_simulators()
            all_devices.extend(simulators)
            
            logger.info(f"Found {len(all_devices)} total devices")
            return all_devices
            
        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            return []

    async def get_device_info(self, device_id: str) -> Optional[DeviceInfo]:
        """Get detailed information about a specific device."""
        try:
            # Try Android first
            android_info = await self.android_manager.get_device_info(device_id)
            if android_info:
                return android_info
            
            # Try iOS simulators
            simulator_info = await self.simctl_manager.get_simulator_info(device_id)
            if simulator_info:
                return simulator_info
            
            # Could add iOS device info lookup here
            return None
            
        except Exception as e:
            logger.error(f"Failed to get device info for {device_id}: {e}")
            return None

    async def select_default_device(self) -> DeviceInfo:
        """Auto-select a single available device or raise error."""
        devices = await self.list_all_devices()
        
        if not devices:
            raise ActionableError(
                "No devices found. Please connect an Android device/emulator or start an iOS simulator.",
                "NO_DEVICES"
            )
        
        if len(devices) == 1:
            logger.info(f"Auto-selected device: {devices[0].name}")
            return devices[0]
        
        if not config.auto_select_single_device:
            raise ActionableError(
                f"Multiple devices found ({len(devices)}). Please specify which device to use.",
                "MULTIPLE_DEVICES"
            )
        
        # Auto-select first available device
        selected = devices[0]
        logger.info(f"Auto-selected first available device: {selected.name}")
        return selected

    async def get_robot(self, device_info: DeviceInfo) -> Robot:
        """Get or create a robot instance for the device."""
        device_id = device_info.id
        
        # Return existing robot if available
        if device_id in self.active_robots:
            return self.active_robots[device_id]
        
        # Create new robot based on device type
        if device_info.type == DeviceType.ANDROID:
            robot = AndroidRobot(device_info)
        elif device_info.type == DeviceType.IOS:
            robot = IosRobot(device_info)
        elif device_info.type == DeviceType.SIMULATOR:
            robot = IosRobot(device_info)
        else:
            raise ActionableError(f"Unsupported device type: {device_info.type}")
        
        # Store for future use
        self.active_robots[device_id] = robot
        logger.info(f"Created robot for device: {device_info.name}")
        
        return robot

    async def cleanup_robot(self, device_id: str) -> None:
        """Clean up robot resources."""
        if device_id in self.active_robots:
            robot = self.active_robots[device_id]
            
            # Call cleanup if available (for iOS robots)
            if hasattr(robot, 'cleanup'):
                try:
                    await robot.cleanup()
                except Exception as e:
                    logger.warning(f"Failed to cleanup robot for {device_id}: {e}")
            
            del self.active_robots[device_id]
            logger.info(f"Cleaned up robot for device: {device_id}")

    async def cleanup_all_robots(self) -> None:
        """Clean up all active robots."""
        for device_id in list(self.active_robots.keys()):
            await self.cleanup_robot(device_id)


# Global device manager instance
device_manager = DeviceManager()
