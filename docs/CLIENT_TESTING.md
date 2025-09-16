# Mobile Automation Service - Client Mode Testing Guide

This document provides comprehensive testing procedures for the WebSocket client mode of the mobile automation service.

## Table of Contents

1. [Setup and Prerequisites](#setup-and-prerequisites)
2. [Configuration Testing](#configuration-testing)
3. [Connection Testing](#connection-testing)
4. [Device Management Testing](#device-management-testing)
5. [Screen Interaction Testing](#screen-interaction-testing)
6. [Error Handling Testing](#error-handling-testing)
7. [Retry and Fallback Testing](#retry-and-fallback-testing)
8. [Performance Testing](#performance-testing)
9. [Integration Testing](#integration-testing)

## Setup and Prerequisites

### 1. Environment Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export BACKEND_SERVER_URL="wss://your-backend-server.com/ws"
export CONNECTION_RETRY_MAX="5"
export CONNECTION_RETRY_DELAY="1.0"
export HEALTH_CHECK_INTERVAL="30"
export LOG_LEVEL="DEBUG"
```

### 2. Device Preparation

**Android:**
```bash
# Start Android emulator
emulator -avd Pixel_7_API_34

# Verify device is connected
adb devices -l
# Should show: emulator-5554          device product:sdk_gphone64_arm64 model:sdk_gphone64_arm64
```

**iOS Simulator:**
```bash
# List available simulators
xcrun simctl list devices

# Boot a simulator
xcrun simctl boot "iPhone 15 Pro"

# Verify simulator is running
xcrun simctl list devices | grep Booted
```

## Configuration Testing

### Test 1: Configuration Loading

```bash
# Test configuration loading
python -c "
from src.config import config
print(f'Backend URL: {config.backend_server_url}')
print(f'Retry Max: {config.connection_retry_max}')
print(f'Retry Delay: {config.connection_retry_delay}')
print(f'Health Check Interval: {config.health_check_interval}')
"
```

**Expected Output:**
```
Backend URL: wss://your-backend-server.com/ws
Retry Max: 5
Retry Delay: 1.0
Health Check Interval: 30
```

### Test 2: Environment Variable Override

```bash
# Test environment variable override
export BACKEND_SERVER_URL="wss://test-server.com/ws"
export CONNECTION_RETRY_MAX="10"

python -c "
from src.config import config
print(f'Backend URL: {config.backend_server_url}')
print(f'Retry Max: {config.connection_retry_max}')
"
```

**Expected Output:**
```
Backend URL: wss://test-server.com/ws
Retry Max: 10
```

## Connection Testing

### create sessiong token

```bash
curl -X POST http://localhost:8003/v1/sessions \
-H "Content-Type: application/json" \
-d '{
  "device_id": "mobile-client-test",
  "session_id": "test-session-001",
  "provider": "LOCAL_CLIENT",
  "configuration": {
    "platform": "ANDROID"
  }
}'
```

### Test 3: Successful Connection


```bash
# Start the client (replace with your actual backend URL)
export BACKEND_SERVER_URL="wss://echo.websocket.org"
python src/client_main.py
```


**Expected Output:**
```
2025-01-01 12:00:00,000 - src.websocket.client - INFO - Starting WebSocket client for wss://echo.websocket.org
2025-01-01 12:00:00,100 - src.websocket.client - INFO - Attempting to connect to wss://echo.websocket.org (attempt 1)
2025-01-01 12:00:00,200 - src.websocket.client - INFO - Successfully connected to wss://echo.websocket.org
2025-01-01 12:00:00,300 - src.websocket.client - INFO - WebSocket client started successfully
```

### Test 4: Connection Failure and Retry

```bash
# Test with invalid URL to trigger retry mechanism
export BACKEND_SERVER_URL="wss://invalid-server.com/ws"
export CONNECTION_RETRY_MAX="3"
export CONNECTION_RETRY_DELAY="0.5"

python src/client_main.py
```

**Expected Output:**
```
2025-01-01 12:00:00,000 - src.websocket.client - INFO - Starting WebSocket client for wss://invalid-server.com/ws
2025-01-01 12:00:00,100 - src.websocket.client - INFO - Attempting to connect to wss://invalid-server.com/ws (attempt 1)
2025-01-01 12:00:00,200 - src.websocket.client - WARNING - Connection attempt 1 failed: [Errno 8] nodename nor servname provided, or not known
2025-01-01 12:00:00,300 - src.websocket.client - INFO - Retrying in 0.50 seconds...
2025-01-01 12:00:00,800 - src.websocket.client - INFO - Attempting to connect to wss://invalid-server.com/ws (attempt 2)
...
2025-01-01 12:00:05,000 - src.websocket.client - ERROR - Failed to connect after 3 attempts
```

## Device Management Testing

### Test 5: Device Discovery

```python
# Test device discovery directly
python -c "
import asyncio
from src.device_manager import device_manager

async def test_devices():
    devices = await device_manager.list_all_devices()
    print(f'Found {len(devices)} devices:')
    for device in devices:
        print(f'  - {device.name} ({device.type.value}) - {device.status}')

asyncio.run(test_devices())
"
```

**Expected Output:**
```
Found 1 devices:
  - Android Device (sdk_gphone64_arm64) (android) - connected
```

### Test 6: Device Selection

```python
# Test device selection
python -c "
import asyncio
from src.device_manager import device_manager

async def test_selection():
    try:
        device = await device_manager.select_default_device()
        print(f'Selected device: {device.name} ({device.id})')
    except Exception as e:
        print(f'Error: {e}')

asyncio.run(test_selection())
"
```

**Expected Output:**
```
Selected device: Android Device (sdk_gphone64_arm64) (emulator-5554)
```

## Screen Interaction Testing

### Test 7: Screenshot Capture

```python
# Test screenshot functionality
python -c "
import asyncio
import base64
from src.device_manager import device_manager

async def test_screenshot():
    try:
        # Select device
        device = await device_manager.select_default_device()
        robot = await device_manager.get_robot(device)
        
        # Take screenshot
        screenshot = await robot.get_screenshot()
        screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
        
        print(f'Screenshot captured: {len(screenshot)} bytes')
        print(f'Base64 length: {len(screenshot_b64)} characters')
        print(f'First 50 chars: {screenshot_b64[:50]}...')
        
    except Exception as e:
        print(f'Error: {e}')

asyncio.run(test_screenshot())
"
```

**Expected Output:**
```
Screenshot captured: 123456 bytes
Base64 length: 164608 characters
First 50 chars: iVBORw0KGgoAAAANSUhEUgAAASwAAAEsCAYAAAB5fY51...
```

### Test 8: Screen Interaction

```python
# Test screen tap
python -c "
import asyncio
from src.device_manager import device_manager

async def test_tap():
    try:
        device = await device_manager.select_default_device()
        robot = await device_manager.get_robot(device)
        
        # Get screen size
        screen_size = await robot.get_screen_size()
        print(f'Screen size: {screen_size.width}x{screen_size.height}')
        
        # Tap at center
        center_x = screen_size.width // 2
        center_y = screen_size.height // 2
        await robot.tap(center_x, center_y)
        print(f'Tapped at center: ({center_x}, {center_y})')
        
    except Exception as e:
        print(f'Error: {e}')

asyncio.run(test_tap())
"
```

**Expected Output:**
```
Screen size: 1080x2400
Tapped at center: (540, 1200)
```

## Error Handling Testing

### Test 9: Invalid Commands

```python
# Test invalid command handling
python -c "
import asyncio
from src.websocket.client import WebSocketMobileClient

async def test_invalid_command():
    client = WebSocketMobileClient('wss://echo.websocket.org')
    
    # Test invalid action
    command = {
        'id': 'test-123',
        'type': 'automation_command',
        'action': 'invalid_action',
        'params': {}
    }
    
    await client._handle_server_message(command)

asyncio.run(test_invalid_command())
"
```

**Expected Output:**
```
2025-01-01 12:00:00,000 - src.websocket.client - INFO - Executing command: invalid_action
2025-01-01 12:00:00,100 - src.websocket.client - WARNING - Unknown message type: automation_command
```

### Test 10: Missing Device Selection

```python
# Test operations without device selection
python -c "
import asyncio
from src.websocket.client import WebSocketMobileClient

async def test_no_device():
    client = WebSocketMobileClient('wss://echo.websocket.org')
    
    # Try to take screenshot without selecting device
    command = {
        'id': 'test-123',
        'type': 'automation_command',
        'action': 'mobile_take_screenshot',
        'params': {}
    }
    
    await client._handle_server_message(command)

asyncio.run(test_no_device())
"
```

**Expected Output:**
```
2025-01-01 12:00:00,000 - src.websocket.client - INFO - Executing command: mobile_take_screenshot
2025-01-01 12:00:00,100 - src.websocket.client - ERROR - Error executing command test-123: No device selected
```

## Retry and Fallback Testing

### Test 11: Connection Loss Recovery

```bash
# Test connection loss and recovery
# 1. Start client
export BACKEND_SERVER_URL="wss://echo.websocket.org"
python src/client_main.py &

# 2. Kill the connection (simulate network issue)
# Wait for reconnection attempts

# 3. Check logs for retry behavior
tail -f logs/mobile-automation.log | grep -E "(retry|reconnect|connection)"
```

**Expected Output:**
```
2025-01-01 12:00:00,000 - src.websocket.client - WARNING - WebSocket connection lost, attempting reconnection...
2025-01-01 12:00:00,100 - src.websocket.client - INFO - Attempting to connect to wss://echo.websocket.org (attempt 1)
2025-01-01 12:00:00,200 - src.websocket.client - INFO - Successfully connected to wss://echo.websocket.org
```

### Test 12: Exponential Backoff

```python
# Test exponential backoff calculation
python -c "
from src.websocket.client import ConnectionManager, RetryConfig

config = RetryConfig(max_retries=5, base_delay=1.0, exponential_backoff=True)
manager = ConnectionManager('wss://test.com', config)

# Test delay calculations
for i in range(1, 6):
    manager.retry_count = i
    delay = manager._calculate_delay()
    print(f'Retry {i}: {delay:.2f} seconds')

# Test with jitter
config.jitter = True
manager = ConnectionManager('wss://test.com', config)
for i in range(1, 4):
    manager.retry_count = i
    delays = [manager._calculate_delay() for _ in range(5)]
    print(f'Retry {i} with jitter: {delays}')
"
```

**Expected Output:**
```
Retry 1: 1.00 seconds
Retry 2: 2.00 seconds
Retry 3: 4.00 seconds
Retry 4: 8.00 seconds
Retry 5: 16.00 seconds
Retry 1 with jitter: [1.05, 1.08, 1.02, 1.07, 1.03]
Retry 2 with jitter: [2.12, 2.05, 2.18, 2.03, 2.09]
Retry 3 with jitter: [4.23, 4.15, 4.31, 4.08, 4.19]
```

## Performance Testing

### Test 13: Concurrent Command Handling

```python
# Test handling multiple concurrent commands
python -c "
import asyncio
import time
from src.websocket.client import WebSocketMobileClient

async def test_concurrent_commands():
    client = WebSocketMobileClient('wss://echo.websocket.org')
    
    # Simulate multiple concurrent commands
    commands = [
        {'id': f'cmd-{i}', 'type': 'automation_command', 'action': 'mobile_get_screen_size', 'params': {}}
        for i in range(10)
    ]
    
    start_time = time.time()
    
    # Execute commands concurrently
    tasks = [client._handle_server_message(cmd) for cmd in commands]
    await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    print(f'Executed {len(commands)} commands in {end_time - start_time:.2f} seconds')

asyncio.run(test_concurrent_commands())
"
```

### Test 14: Memory Usage

```bash
# Monitor memory usage during operation
python -c "
import psutil
import os
import time

# Start monitoring
process = psutil.Process(os.getpid())
initial_memory = process.memory_info().rss / 1024 / 1024  # MB

print(f'Initial memory usage: {initial_memory:.2f} MB')

# Run client for 5 minutes and monitor
# (This would be run in a separate terminal)
"
```

## Integration Testing

### Test 15: End-to-End Workflow

```python
# Complete workflow test
python -c "
import asyncio
from src.websocket.client import WebSocketMobileClient

async def test_complete_workflow():
    client = WebSocketMobileClient('wss://echo.websocket.org')
    
    # 1. List devices
    devices_cmd = {
        'id': 'list-devices',
        'type': 'automation_command',
        'action': 'mobile_list_available_devices',
        'params': {}
    }
    await client._handle_server_message(devices_cmd)
    
    # 2. Select device
    select_cmd = {
        'id': 'select-device',
        'type': 'automation_command',
        'action': 'mobile_use_default_device',
        'params': {}
    }
    await client._handle_server_message(select_cmd)
    
    # 3. Take screenshot
    screenshot_cmd = {
        'id': 'take-screenshot',
        'type': 'automation_command',
        'action': 'mobile_take_screenshot',
        'params': {}
    }
    await client._handle_server_message(screenshot_cmd)
    
    print('Complete workflow executed successfully')

asyncio.run(test_complete_workflow())
"
```

## Test Automation Scripts

### Test 16: Automated Test Suite

```bash
#!/bin/bash
# run_tests.sh - Automated test suite

echo "Starting Mobile Automation Service Tests..."

# Test 1: Configuration
echo "Test 1: Configuration Loading"
python -c "from src.config import config; print('✓ Config loaded')"

# Test 2: Device Discovery
echo "Test 2: Device Discovery"
python -c "
import asyncio
from src.device_manager import device_manager
async def test(): 
    devices = await device_manager.list_all_devices()
    print(f'✓ Found {len(devices)} devices')
asyncio.run(test())
"

# Test 3: Connection (if backend available)
echo "Test 3: Connection Test"
if [ -n \"$BACKEND_SERVER_URL\" ]; then
    timeout 10s python src/client_main.py &
    CLIENT_PID=$!
    sleep 5
    kill $CLIENT_PID 2>/dev/null
    echo "✓ Connection test completed"
else
    echo "⚠ Skipping connection test (no BACKEND_SERVER_URL set)"
fi

echo "All tests completed!"
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check if backend server is running
   - Verify URL format (wss:// not ws://)
   - Check firewall settings

2. **Device Not Found**
   - Ensure Android emulator is running
   - Check ADB connection: `adb devices`
   - For iOS: Check simulator status: `xcrun simctl list devices`

3. **Permission Errors**
   - Ensure proper permissions for device access
   - Check USB debugging is enabled (Android)
   - Verify Xcode command line tools installed (iOS)

4. **Memory Issues**
   - Monitor memory usage during long operations
   - Consider reducing screenshot quality
   - Check for memory leaks in robot cleanup

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL="DEBUG"
python src/client_main.py
```

### Log Analysis

```bash
# Monitor logs in real-time
tail -f logs/mobile-automation.log

# Filter for specific events
grep -E "(ERROR|WARNING)" logs/mobile-automation.log
grep -E "(connection|retry)" logs/mobile-automation.log
```

## Performance Benchmarks

### Expected Performance

- **Connection Time**: < 2 seconds
- **Device Discovery**: < 1 second
- **Screenshot Capture**: < 3 seconds
- **Screen Tap**: < 0.5 seconds
- **Memory Usage**: < 100MB baseline
- **Retry Delay**: 1s, 2s, 4s, 8s, 16s (exponential backoff)

### Load Testing

```python
# Load test script
import asyncio
import time
from src.websocket.client import WebSocketMobileClient

async def load_test():
    client = WebSocketMobileClient('wss://your-backend.com/ws')
    
    # Simulate 100 commands
    start_time = time.time()
    tasks = []
    
    for i in range(100):
        task = asyncio.create_task(
            client._handle_server_message({
                'id': f'load-test-{i}',
                'type': 'automation_command',
                'action': 'mobile_get_screen_size',
                'params': {}
            })
        )
        tasks.append(task)
    
    await asyncio.gather(*tasks)
    end_time = time.time()
    
    print(f'Processed 100 commands in {end_time - start_time:.2f} seconds')
    print(f'Average: {(end_time - start_time) / 100:.3f} seconds per command')

asyncio.run(load_test())
```

This comprehensive testing guide covers all aspects of the mobile automation service in client mode, from basic functionality to advanced performance testing and troubleshooting.
