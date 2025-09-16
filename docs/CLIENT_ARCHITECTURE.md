# Client Architecture - WebSocket Client Mode

This document describes the initial architecture of the mobile automation service as a WebSocket client that connects to your backend server.

## Overview

The service is designed as a **WebSocket Client** that connects to your backend server and executes automation commands locally on connected mobile devices.

## Key Components

### 1. WebSocket Client Implementation

**File**: `src/websocket/client.py`

- **ConnectionManager**: Handles WebSocket connection with retry/fallback mechanisms
- **WebSocketMobileClient**: Main client class that executes automation commands
- **RetryConfig**: Configuration for exponential backoff retry logic

**Key Features**:
- Exponential backoff with jitter
- Health check monitoring
- Automatic reconnection
- Connection timeout handling

### 2. Configuration

**File**: `src/config.py`

**Configuration Options**:
```python
# WebSocket Client Configuration
backend_server_url: str = "wss://your-backend-server.com/ws"
connection_retry_max: int = 5
connection_retry_delay: float = 1.0
connection_retry_max_delay: float = 60.0
health_check_interval: int = 30
connection_timeout: int = 10
```

**Environment Variables**:
- `BACKEND_SERVER_URL`: Backend server WebSocket URL
- `CONNECTION_RETRY_MAX`: Maximum retry attempts
- `CONNECTION_RETRY_DELAY`: Base delay between retries
- `HEALTH_CHECK_INTERVAL`: Health check interval
- `CONNECTION_TIMEOUT`: Connection timeout

### 3. Entry Point

**File**: `src/client_main.py`

- Main entry point for client mode
- Handles graceful shutdown
- Signal handling for clean exit

**Usage**:
```bash
python src/client_main.py
```

### 4. Message Protocol Changes

**Before (Server Mode)**:
```json
// Client sends request
{
  "id": "req-123",
  "action": "mobile_take_screenshot",
  "params": {},
  "timestamp": "2025-01-01T00:00:00Z"
}

// Server sends response
{
  "id": "req-123",
  "success": true,
  "data": {"screenshot": "base64..."},
  "timestamp": "2025-01-01T00:00:01Z"
}
```

**After (Client Mode)**:
```json
// Backend server sends command
{
  "id": "cmd-123",
  "type": "automation_command",
  "action": "mobile_take_screenshot",
  "params": {},
  "timestamp": "2025-01-01T00:00:00Z"
}

// Client sends result
{
  "id": "cmd-123",
  "type": "automation_result",
  "success": true,
  "data": {"screenshot": "base64..."},
  "timestamp": "2025-01-01T00:00:01Z"
}
```

### 5. Retry and Fallback Mechanisms

**Exponential Backoff**:
- Base delay: 1 second
- Multiplier: 2x each retry
- Max delay: 60 seconds
- Jitter: ±10% random variation

**Health Check**:
- Ping server every 30 seconds
- Automatic reconnection on failure
- Connection state monitoring

**Error Handling**:
- Graceful degradation
- Detailed error logging
- Actionable error responses

### 6. Testing Infrastructure

**Files**:
- `docs/CLIENT_TESTING.md`: Comprehensive testing guide
- `docs/CLIENT_USAGE.md`: Usage documentation
- `scripts/test_client.py`: Automated test suite

**Test Coverage**:
- Device discovery and selection
- Screen operations (screenshot, tap, swipe)
- WebSocket client functionality
- Retry mechanism validation
- Error handling scenarios

## Architecture 

### After (Client Mode)
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

## Benefits of Client Mode

### 1. **Centralized Control**
- All business logic in your backend server
- Centralized user session management
- Unified command and control

### 2. **Scalability**
- Multiple mobile automation services can connect
- Load balancing across multiple instances
- Horizontal scaling capabilities

### 3. **Reliability**
- Robust retry and fallback mechanisms
- Automatic reconnection
- Health monitoring

### 4. **Security**
- Centralized authentication
- Secure WebSocket connections (wss://)
- Controlled access to mobile devices

### 5. **Maintainability**
- Clear separation of concerns
- Easier to update and deploy
- Centralized logging and monitoring

## Getting Started

### 1. Set up Backend Server

First, implement a WebSocket server that can send automation commands:

```python
# Example backend server implementation
import asyncio
import websockets
import json

async def handle_client(websocket, path):
    # Send automation command
    command = {
        "id": "cmd-123",
        "type": "automation_command", 
        "action": "mobile_take_screenshot",
        "params": {},
        "timestamp": "2025-01-01T00:00:00Z"
    }
    
    await websocket.send(json.dumps(command))
    
    # Wait for result
    result = await websocket.recv()
    print(f"Received result: {result}")

# Start server
start_server = websockets.serve(handle_client, "localhost", 8765)
asyncio.get_event_loop().run_until_complete(start_server)
```

### 2. Configure Mobile Service

```bash
# Set backend server URL
export BACKEND_SERVER_URL="wss://your-backend-server.com/ws"

# Start the mobile automation client
python src/client_main.py
```

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
```

## Performance Characteristics

### Connection Management
- **Connection Time**: < 2 seconds
- **Retry Delay**: 1s, 2s, 4s, 8s, 16s (exponential backoff)
- **Health Check**: Every 30 seconds
- **Reconnection**: Automatic on failure

### Device Operations
- **Device Discovery**: < 1 second
- **Screenshot Capture**: < 3 seconds
- **Screen Tap**: < 0.5 seconds
- **Memory Usage**: < 100MB baseline

### Reliability
- **Retry Attempts**: 5 by default
- **Connection Timeout**: 10 seconds
- **Error Recovery**: Automatic
- **Graceful Shutdown**: Signal handling

## Security Considerations

1. **WebSocket Security**: Use `wss://` in production
2. **Authentication**: Implement token-based auth if needed
3. **Network Security**: Use VPN or secure networks
4. **Device Access**: Proper permissions for device access

## Monitoring and Observability

### Logging
- Structured logging with configurable levels
- Connection status tracking
- Command execution logging
- Error tracking and reporting

### Health Checks
- Connection health monitoring
- Device availability checks
- Performance metrics collection

### Alerting
- Connection failure alerts
- Device unavailability alerts
- Performance degradation alerts

This architecture change provides a more robust, scalable, and maintainable solution for mobile automation that integrates seamlessly with your backend infrastructure.
