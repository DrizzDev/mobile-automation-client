"""Unit tests for device manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.device_manager import DeviceManager
from src.types import DeviceInfo, DeviceType
from src.robot import ActionableError


class TestDeviceManager:
    """Test device manager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.device_manager = DeviceManager()

    @pytest.mark.asyncio
    async def test_list_all_devices_empty(self):
        """Test listing devices when none are available."""
        # Mock all device managers to return empty lists
        self.device_manager.android_manager.get_connected_devices = AsyncMock(return_value=[])
        self.device_manager.simctl_manager.list_booted_simulators = AsyncMock(return_value=[])
        self.device_manager.ios_manager.list_devices = AsyncMock(return_value=[])
        
        devices = await self.device_manager.list_all_devices()
        
        assert devices == []

    @pytest.mark.asyncio
    async def test_list_all_devices_mixed(self):
        """Test listing devices with mixed platform devices."""
        android_device = DeviceInfo(
            id="emulator-5554",
            name="Android Emulator",
            type=DeviceType.ANDROID,
            is_emulator=True
        )
        
        ios_sim = DeviceInfo(
            id="12345678-1234-1234-1234-123456789ABC",
            name="iPhone 15 Pro",
            type=DeviceType.SIMULATOR,
            is_emulator=True
        )
        
        # Mock managers
        self.device_manager.android_manager.get_connected_devices = AsyncMock(return_value=[android_device])
        self.device_manager.simctl_manager.list_booted_simulators = AsyncMock(return_value=[ios_sim])
        self.device_manager.ios_manager.list_devices = AsyncMock(return_value=[])
        
        devices = await self.device_manager.list_all_devices()
        
        assert len(devices) == 2
        assert android_device in devices
        assert ios_sim in devices

    @pytest.mark.asyncio
    async def test_select_default_device_no_devices(self):
        """Test selecting default device when none are available."""
        self.device_manager.list_all_devices = AsyncMock(return_value=[])
        
        with pytest.raises(ActionableError) as exc_info:
            await self.device_manager.select_default_device()
        
        assert "No devices found" in str(exc_info.value)
        assert exc_info.value.code == "NO_DEVICES"

    @pytest.mark.asyncio
    async def test_select_default_device_single(self):
        """Test selecting default device when only one is available."""
        device = DeviceInfo(
            id="test-device",
            name="Test Device",
            type=DeviceType.ANDROID
        )
        
        self.device_manager.list_all_devices = AsyncMock(return_value=[device])
        
        selected = await self.device_manager.select_default_device()
        
        assert selected == device

    @pytest.mark.asyncio
    async def test_select_default_device_multiple_auto_select(self):
        """Test auto-selecting first device when multiple are available."""
        device1 = DeviceInfo(id="device1", name="Device 1", type=DeviceType.ANDROID)
        device2 = DeviceInfo(id="device2", name="Device 2", type=DeviceType.SIMULATOR)
        
        self.device_manager.list_all_devices = AsyncMock(return_value=[device1, device2])
        
        # Mock config to enable auto-selection
        import src.config
        original_config = src.config.config.auto_select_single_device
        src.config.config.auto_select_single_device = True
        
        try:
            selected = await self.device_manager.select_default_device()
            assert selected == device1
        finally:
            src.config.config.auto_select_single_device = original_config

    @pytest.mark.asyncio
    async def test_get_robot_android(self):
        """Test getting Android robot."""
        device = DeviceInfo(
            id="android-device",
            name="Android Device",
            type=DeviceType.ANDROID
        )
        
        robot = await self.device_manager.get_robot(device)
        
        assert robot is not None
        assert device.id in self.device_manager.active_robots
        
        # Second call should return same robot
        robot2 = await self.device_manager.get_robot(device)
        assert robot is robot2

    @pytest.mark.asyncio
    async def test_cleanup_robot(self):
        """Test cleaning up robot resources."""
        device = DeviceInfo(
            id="test-device",
            name="Test Device",
            type=DeviceType.ANDROID
        )
        
        # Create robot
        robot = await self.device_manager.get_robot(device)
        assert device.id in self.device_manager.active_robots
        
        # Cleanup
        await self.device_manager.cleanup_robot(device.id)
        assert device.id not in self.device_manager.active_robots
