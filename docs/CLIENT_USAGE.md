# Mobile Automation Service - Client Mode Usage Guide

This guide explains how to use the mobile automation service in client mode, where it connects to your backend server and executes automation commands.

## Quick Start

### 1. Configuration

Set up your environment variables:

```bash
# Required: Backend server URL
export BACKEND_SERVER_URL="wss://your-backend-server.com/ws"

# Optional: Retry configuration
export CONNECTION_RETRY_MAX="5"
export CONNECTION_RETRY_DELAY="1.0"
export HEALTH_CHECK_INTERVAL="30"
export LOG_LEVEL="INFO"
```

### 2. Start the Client

```bash
# Start the WebSocket client
python src/client_main.py
```

### 3. Test the Setup

```bash
# Run automated tests
python scripts/test_client.py

# Run interactive tests
python scripts/test_client.py --interactive
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Backend Server                      │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              WebSocket Server                           │ │
│  │  - Handles business logic                              │ │
│  │  - Manages user sessions                               │ │
│  │  - Sends automation commands                           │ │
│  │  - Receives results                                   │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ WebSocket Connection
                              │ (with retry/fallback)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Mobile Automation Service                      │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │            WebSocket Client                             │ │
│  │  - Connects to backend server                          │ │
│  │  - Handles connection retry/fallback                   │ │
│  │  - Receives automation commands                        │ │
│  │  - Executes local device operations                    │ │
│  │  - Sends results back                                  │ │
│  └─────────────────────────────────────────────────────────┘ │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │            Device Manager                               │ │
│  │  - Android/iOS device detection                        │ │
│  │  - Robot instantiation                                 │ │
│  │  - Local automation execution                          │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Message Protocol

### Commands from Backend Server

```json
{
  "id": "cmd-123",
  "type": "automation_command",
  "action": "mobile_take_screenshot",
  "params": {
    "device_id": "emulator-5554"
  },
  "timestamp": "2025-01-01T00:00:00Z"
}
```

### Responses to Backend Server

```json
{
  "id": "cmd-123",
  "type": "automation_result",
  "success": true,
  "data": {
    "screenshot": "iVBORw0KGgoAAAANSU..."
  },
  "timestamp": "2025-01-01T00:00:01Z"
}
```

### Error Responses

```json
{
  "id": "cmd-123",
  "type": "automation_result",
  "success": false,
  "error": {
    "type": "ActionableError",
    "message": "No device selected",
    "code": "NO_DEVICE_SELECTED"
  },
  "timestamp": "2025-01-01T00:00:01Z"
}
```

## Supported Actions

### Device Management

| Action | Description | Parameters |
|--------|-------------|------------|
| `mobile_list_available_devices` | List all connected devices | None |
| `mobile_use_default_device` | Auto-select single device | None |
| `mobile_use_device` | Select specific device | `device_id` |

### Screen Interaction

| Action | Description | Parameters |
|--------|-------------|------------|
| `mobile_click_on_screen_at_coordinates` | Tap at coordinates | `x`, `y` |
| `mobile_long_press_on_screen_at_coordinates` | Long press at coordinates | `x`, `y` |
| `swipe_on_screen` | Swipe in direction | `direction` (up/down/left/right) |
| `mobile_type_keys` | Input text | `text` |
| `mobile_press_button` | Press physical button | `button` (home/back/menu/etc.) |
| `mobile_open_url` | Open URL in browser | `url` |

### Screen State

| Action | Description | Parameters |
|--------|-------------|------------|
| `mobile_take_screenshot` | Capture screen | None |
| `mobile_get_screen_size` | Get screen dimensions | None |
| `mobile_set_orientation` | Change orientation | `orientation` (portrait/landscape) |
| `mobile_get_orientation` | Get current orientation | None |

### Application Management

| Action | Description | Parameters |
|--------|-------------|------------|
| `mobile_list_apps` | List installed apps | None |
| `mobile_launch_app` | Launch app | `package_name` or `bundle_id` |
| `mobile_terminate_app` | Force-stop app | `package_name` or `bundle_id` |

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_SERVER_URL` | `wss://your-backend-server.com/ws` | Backend server WebSocket URL |
| `CONNECTION_RETRY_MAX` | `5` | Maximum retry attempts |
| `CONNECTION_RETRY_DELAY` | `1.0` | Base delay between retries (seconds) |
| `CONNECTION_RETRY_MAX_DELAY` | `60.0` | Maximum delay between retries (seconds) |
| `HEALTH_CHECK_INTERVAL` | `30` | Health check interval (seconds) |
| `CONNECTION_TIMEOUT` | `10` | Connection timeout (seconds) |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |

### Retry Configuration

The client uses exponential backoff with jitter for retry attempts:

- **Base Delay**: 1 second
- **Exponential Backoff**: 1s, 2s, 4s, 8s, 16s, 32s...
- **Max Delay**: 60 seconds
- **Jitter**: ±10% random variation to prevent thundering herd

## Testing

### Automated Tests

```bash
# Run all tests
python scripts/test_client.py

# Run specific tests
python scripts/test_client.py --test devices
python scripts/test_client.py --test client
python scripts/test_client.py --test retry

# Interactive testing
python scripts/test_client.py --interactive
```

### Manual Testing

```bash
# Test device discovery
python -c "
import asyncio
from src.device_manager import device_manager
async def test():
    devices = await device_manager.list_all_devices()
    print(f'Found {len(devices)} devices')
asyncio.run(test())
"

# Test screenshot
python -c "
import asyncio
from src.device_manager import device_manager
async def test():
    device = await device_manager.select_default_device()
    robot = await device_manager.get_robot(device)
    screenshot = await robot.get_screenshot()
    print(f'Screenshot: {len(screenshot)} bytes')
asyncio.run(test())
"
```

## Troubleshooting

### Common Issues

1. **Connection Failed**
   ```
   ERROR - Failed to connect after 5 attempts
   ```
   - Check if backend server is running
   - Verify URL format (wss:// not ws://)
   - Check firewall/network settings

2. **No Devices Found**
   ```
   Found 0 devices
   ```
   - For Android: `adb devices` should show connected devices
   - For iOS: `xcrun simctl list devices` should show booted simulators
   - Ensure devices are properly connected

3. **Permission Denied**
   ```
   ERROR - Permission denied
   ```
   - Check USB debugging is enabled (Android)
   - Verify Xcode command line tools installed (iOS)
   - Check device permissions

4. **Memory Issues**
   ```
   ERROR - Out of memory
   ```
   - Monitor memory usage
   - Consider reducing screenshot quality
   - Check for memory leaks

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL="DEBUG"
python src/client_main.py
```

### Log Analysis

```bash
# Monitor logs
tail -f logs/mobile-automation.log

# Filter specific events
grep -E "(ERROR|WARNING)" logs/mobile-automation.log
grep -E "(connection|retry)" logs/mobile-automation.log
```

## Performance

### Expected Performance

- **Connection Time**: < 2 seconds
- **Device Discovery**: < 1 second  
- **Screenshot Capture**: < 3 seconds
- **Screen Tap**: < 0.5 seconds
- **Memory Usage**: < 100MB baseline

### Optimization Tips

1. **Reduce Screenshot Quality** (if needed)
2. **Use Specific Device Selection** instead of auto-selection
3. **Monitor Memory Usage** during long operations
4. **Implement Command Queuing** for high-frequency operations

## Security Considerations

1. **WebSocket Security**: Use `wss://` (secure WebSocket) in production
2. **Authentication**: Implement authentication tokens if needed
3. **Device Access**: Ensure proper permissions for device access
4. **Network Security**: Use VPN or secure networks for device communication

## Production Deployment

### Docker Deployment

```dockerfile
# Add to Dockerfile
COPY src/client_main.py /app/src/
CMD ["python", "src/client_main.py"]
```

### Environment Configuration

```bash
# Production environment
export BACKEND_SERVER_URL="wss://prod-backend.company.com/ws"
export CONNECTION_RETRY_MAX="10"
export HEALTH_CHECK_INTERVAL="60"
export LOG_LEVEL="INFO"
```

### Monitoring

- Monitor connection status
- Track retry attempts
- Monitor device availability
- Log performance metrics

This client mode provides a robust, production-ready solution for mobile automation that can scale with your backend infrastructure.
