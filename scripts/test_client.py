#!/usr/bin/env python3
"""
Test script for WebSocket client functionality.

This script provides easy testing of the mobile automation service
in client mode without requiring a backend server.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.utils.logger import get_logger
from src.websocket.client import WebSocketMobileClient, RetryConfig
from src.device_manager import device_manager

logger = get_logger(__name__)


class MockBackendServer:
    """Mock backend server for testing purposes."""
    
    def __init__(self):
        self.client = None
        self.commands_sent = []
        self.responses_received = []
    
    async def start(self, client: WebSocketMobileClient):
        """Start the mock server."""
        self.client = client
        # Simulate connection state
        client.connection_manager.is_connected = True
        logger.info("Mock backend server started")
        
        # Send initial status request
        await self.send_command("status_request", {})
        
        # Send test commands
        await self.run_test_sequence()
    
    async def send_command(self, action: str, params: dict = None):
        """Send a command to the client."""
        command = {
            "id": f"test-{len(self.commands_sent)}",
            "type": "automation_command",
            "action": action,
            "params": params or {},
            "timestamp": "2025-01-01T00:00:00Z"
        }
        
        self.commands_sent.append(command)
        logger.info(f"Mock server sending: {action}")
        
        # Simulate sending to client
        await self.client._handle_server_message(command)
    
    async def run_test_sequence(self):
        """Run a sequence of test commands."""
        test_commands = [
            ("mobile_list_available_devices", {}),
            ("mobile_use_default_device", {}),
            ("mobile_get_screen_size", {}),
            ("mobile_take_screenshot", {}),
            ("mobile_click_on_screen_at_coordinates", {"x": 100, "y": 200}),
            ("swipe_on_screen", {"direction": "up"}),
            ("mobile_type_keys", {"text": "Hello World"}),
            ("mobile_press_button", {"button": "home"}),
        ]
        
        for action, params in test_commands:
            try:
                await self.send_command(action, params)
                await asyncio.sleep(1)  # Wait between commands
            except Exception as e:
                logger.error(f"Error testing {action}: {e}")
        
        logger.info("Test sequence completed")


async def test_device_discovery():
    """Test device discovery functionality."""
    print("\n=== Testing Device Discovery ===")
    
    try:
        devices = await device_manager.list_all_devices()
        print(f"Found {len(devices)} devices:")
        
        for device in devices:
            print(f"  - {device.name} ({device.type.value}) - {device.status}")
        
        if not devices:
            print("⚠️  No devices found. Please ensure:")
            print("   - Android emulator is running (adb devices)")
            print("   - iOS simulator is booted (xcrun simctl list devices)")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Device discovery failed: {e}")
        return False


async def test_device_selection():
    """Test device selection functionality."""
    print("\n=== Testing Device Selection ===")
    
    try:
        device = await device_manager.select_default_device()
        print(f"✅ Selected device: {device.name} ({device.id})")
        
        robot = await device_manager.get_robot(device)
        print(f"✅ Robot created for device")
        
        return True
        
    except Exception as e:
        print(f"❌ Device selection failed: {e}")
        return False


async def test_screen_operations():
    """Test screen operations."""
    print("\n=== Testing Screen Operations ===")
    
    try:
        # Select device
        device = await device_manager.select_default_device()
        robot = await device_manager.get_robot(device)
        
        # Test screen size
        screen_size = await robot.get_screen_size()
        print(f"✅ Screen size: {screen_size.width}x{screen_size.height}")
        
        # Test screenshot
        screenshot = await robot.get_screenshot()
        print(f"✅ Screenshot captured: {len(screenshot)} bytes")
        
        # Test tap
        center_x = screen_size.width // 2
        center_y = screen_size.height // 2
        await robot.tap(center_x, center_y)
        print(f"✅ Tapped at center: ({center_x}, {center_y})")
        
        return True
        
    except Exception as e:
        print(f"❌ Screen operations failed: {e}")
        return False


async def test_websocket_client():
    """Test WebSocket client functionality."""
    print("\n=== Testing WebSocket Client ===")
    
    try:
        # Create mock server
        mock_server = MockBackendServer()
        
        # Create client with mock server URL
        retry_config = RetryConfig(max_retries=1, base_delay=0.1)
        client = WebSocketMobileClient("wss://mock-server.com/ws", retry_config)
        
        # Start mock server
        await mock_server.start(client)
        
        print("✅ WebSocket client test completed")
        return True
        
    except Exception as e:
        print(f"❌ WebSocket client test failed: {e}")
        return False


async def test_retry_mechanism():
    """Test retry mechanism."""
    print("\n=== Testing Retry Mechanism ===")
    
    try:
        from src.websocket.client import ConnectionManager, RetryConfig
        
        # Test retry configuration
        retry_config = RetryConfig(
            max_retries=3,
            base_delay=0.1,
            exponential_backoff=True,
            jitter=True
        )
        
        manager = ConnectionManager("wss://invalid-server.com/ws", retry_config)
        
        # Test delay calculations
        print("Testing delay calculations:")
        for i in range(1, 4):
            manager.retry_count = i
            delay = manager._calculate_delay()
            print(f"  Retry {i}: {delay:.3f} seconds")
        
        print("✅ Retry mechanism test completed")
        return True
        
    except Exception as e:
        print(f"❌ Retry mechanism test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests."""
    print("🚀 Starting Mobile Automation Service Tests")
    print("=" * 50)
    
    tests = [
        ("Device Discovery", test_device_discovery),
        ("Device Selection", test_device_selection),
        ("Screen Operations", test_screen_operations),
        ("WebSocket Client", test_websocket_client),
        ("Retry Mechanism", test_retry_mechanism),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False


async def interactive_test():
    """Interactive testing mode."""
    print("\n🔧 Interactive Testing Mode")
    print("Available commands:")
    print("  1. List devices")
    print("  2. Select device")
    print("  3. Take screenshot")
    print("  4. Tap screen")
    print("  5. Get screen size")
    print("  6. Swipe screen")
    print("  7. Type text")
    print("  8. Press button")
    print("  9. Exit")
    
    device = None
    robot = None
    
    while True:
        try:
            choice = input("\nEnter command (1-9): ").strip()
            
            if choice == "1":
                devices = await device_manager.list_all_devices()
                print(f"Found {len(devices)} devices:")
                for i, dev in enumerate(devices):
                    print(f"  {i}: {dev.name} ({dev.type.value})")
            
            elif choice == "2":
                devices = await device_manager.list_all_devices()
                if not devices:
                    print("No devices available")
                    continue
                
                device = await device_manager.select_default_device()
                robot = await device_manager.get_robot(device)
                print(f"Selected: {device.name}")
            
            elif choice == "3":
                if not robot:
                    print("Please select a device first (command 2)")
                    continue
                
                screenshot = await robot.get_screenshot()
                print(f"Screenshot captured: {len(screenshot)} bytes")
            
            elif choice == "4":
                if not robot:
                    print("Please select a device first (command 2)")
                    continue
                
                x = int(input("Enter X coordinate: "))
                y = int(input("Enter Y coordinate: "))
                await robot.tap(x, y)
                print(f"Tapped at ({x}, {y})")
            
            elif choice == "5":
                if not robot:
                    print("Please select a device first (command 2)")
                    continue
                
                screen_size = await robot.get_screen_size()
                print(f"Screen size: {screen_size.width}x{screen_size.height}")
            
            elif choice == "6":
                if not robot:
                    print("Please select a device first (command 2)")
                    continue
                
                direction = input("Enter direction (up/down/left/right): ")
                try:
                    from src.types import SwipeDirection
                    swipe_dir = SwipeDirection(direction)
                    await robot.swipe(swipe_dir)
                    print(f"Swiped {direction}")
                except ValueError:
                    print("Invalid direction")
            
            elif choice == "7":
                if not robot:
                    print("Please select a device first (command 2)")
                    continue
                
                text = input("Enter text to type: ")
                await robot.send_keys(text)
                print(f"Typed: {text}")
            
            elif choice == "8":
                if not robot:
                    print("Please select a device first (command 2)")
                    continue
                
                print("Available buttons: home, back, menu, volume_up, volume_down, power, recent_apps")
                button = input("Enter button name: ")
                try:
                    from src.types import Button
                    button_enum = Button(button)
                    await robot.press_button(button_enum)
                    print(f"Pressed {button}")
                except ValueError:
                    print("Invalid button")
            
            elif choice == "9":
                print("Exiting interactive mode")
                break
            
            else:
                print("Invalid choice")
        
        except KeyboardInterrupt:
            print("\nExiting interactive mode")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Mobile Automation Service")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in interactive mode")
    parser.add_argument("--test", "-t", choices=["all", "devices", "client", "retry"], 
                       default="all", help="Run specific test")
    
    args = parser.parse_args()
    
    if args.interactive:
        asyncio.run(interactive_test())
    else:
        if args.test == "all":
            success = asyncio.run(run_all_tests())
            sys.exit(0 if success else 1)
        elif args.test == "devices":
            asyncio.run(test_device_discovery())
        elif args.test == "client":
            asyncio.run(test_websocket_client())
        elif args.test == "retry":
            asyncio.run(test_retry_mechanism())


if __name__ == "__main__":
    main()
