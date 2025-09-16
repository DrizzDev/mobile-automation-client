# Mobile Automation Service

A production-ready, cross-platform mobile device automation service built in Python with WebSocket client architecture. This service connects to your backend server and provides comprehensive automation capabilities for Android devices and iOS simulators.

## 🚀 Features

- **Cross-Platform Support**: Android (via ADB) and iOS Simulators (via WebDriverAgent/simctl)
- **WebSocket Client**: Connects to your backend server for centralized control
- **Production Ready**: Docker support, health checks, logging, configuration management
- **Robust Connection**: Automatic retry, fallback mechanisms, and reconnection
- **Error Handling**: Actionable vs. technical error classification
- **Device Management**: Local device detection and robot instantiation
- **Image Processing**: Optional ImageMagick integration with PIL fallback
- **Comprehensive Testing**: Unit tests, integration tests, and interactive testing

## 📋 Prerequisites

### macOS Development
- Python 3.10+
- Android SDK Platform Tools (for `adb`)
- Xcode with Command Line Tools (for iOS simulators)
- WebDriverAgent (for iOS simulator interaction)

### Production Deployment
- Docker and Docker Compose
- Backend server with WebSocket support
- Access to Android devices/emulators and iOS simulators on the host system

## 🛠 Installation

### Development Setup
```bash
# Clone and navigate to the project
cd mobile-automation-py

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your backend server configuration
```

### Docker Deployment
```bash
# Build the Docker image
docker build -t mobile-automation .

# Run with Docker Compose (recommended)
docker-compose up -d
```

## 🏃‍♂️ Quick Start

### Configure Backend Server
```bash
# Set your backend server URL
export BACKEND_SERVER_URL="wss://your-backend-server.com/ws"
```

### Start the Client

```bash
# Development
python src/client_main.py

# Production with Docker
docker run mobile-automation
```

The client will connect to your backend server and wait for automation commands.

### Test the Service
```bash
# Run automated tests
python scripts/test_client.py

# Run interactive tests
python scripts/test_client.py --interactive

# Test specific functionality
python scripts/test_client.py --test devices
```

## 📡 WebSocket Protocol

### Message Format

**Command from Backend Server:**
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

**Result to Backend Server (Success):**
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

**Result to Backend Server (Error):**
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

### Available Actions

#### Device Management
- `mobile_list_available_devices` - List all connected devices and simulators
- `mobile_use_default_device` - Auto-select single available device
- `mobile_use_device` - Select specific device by ID

#### Application Management
- `mobile_list_apps` - List installed applications
- `mobile_launch_app` - Launch app by package name (Android) or bundle ID (iOS)
- `mobile_terminate_app` - Force-stop running application

#### Screen Interaction
- `mobile_click_on_screen_at_coordinates` - Tap at x,y coordinates
- `mobile_long_press_on_screen_at_coordinates` - Long press at coordinates
- `swipe_on_screen` - Swipe in direction (up/down/left/right)
- `mobile_type_keys` - Input text to focused element
- `mobile_press_button` - Press physical/virtual buttons
- `mobile_open_url` - Open URL in default browser

#### Screen State
- `mobile_take_screenshot` - Capture screen as base64 PNG
- `mobile_list_elements_on_screen` - Get UI element hierarchy
- `mobile_get_screen_size` - Get screen dimensions
- `mobile_set_orientation` - Change orientation (portrait/landscape)
- `mobile_get_orientation` - Get current orientation

#### Debugging
- `mobile_get_logs` - Retrieve device logs with filtering options

## 🏗 Architecture

The service follows a client-server architecture where the mobile automation service acts as a WebSocket client:

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

## 🧪 Testing

### Running Tests
```bash
# Unit tests
pytest tests/

# With coverage
pytest --cov=src tests/

# Integration tests (requires connected devices)
pytest tests/integration/
```

### Manual Testing
See [`docs/CLIENT_TESTING.md`](docs/CLIENT_TESTING.md) for comprehensive testing procedures and examples.

## 📝 Configuration

All configuration is handled via environment variables. Copy `.env.example` to `.env` and customize:

```bash
# Backend Server
BACKEND_SERVER_URL=wss://your-backend-server.com/ws
CONNECTION_RETRY_MAX=5
CONNECTION_RETRY_DELAY=1.0
HEALTH_CHECK_INTERVAL=30

# Device Paths
ADB_PATH=adb
SIMCTL_PATH=xcrun simctl

# Logging
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/mobile-automation.log
```

## 🚀 Deployment

### Docker Compose (Recommended)
```yaml
version: '3.8'
services:
  mobile-automation:
    build: .
    environment:
      - BACKEND_SERVER_URL=wss://your-backend-server.com/ws
      - LOG_LEVEL=INFO
      - CONNECTION_RETRY_MAX=5
    volumes:
      - ./logs:/app/logs
    command: ["python", "src/client_main.py"]
```

### Monitoring
- Connection health monitoring with automatic reconnection
- Structured logging with configurable levels
- Device availability tracking
- Performance metrics collection

## 🔒 Security Considerations

- Use secure WebSocket connections (wss://) in production
- Non-root user in Docker container
- Input validation via Pydantic models
- Secure device access patterns
- Centralized authentication via backend server

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow the coding standards:
   ```bash
   black . && isort . && mypy src/
   ```
4. Add tests for new functionality
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📚 Documentation

- [`docs/CLIENT_ARCHITECTURE.md`](docs/CLIENT_ARCHITECTURE.md) - Detailed architecture documentation
- [`docs/CLIENT_USAGE.md`](docs/CLIENT_USAGE.md) - Usage guide and configuration
- [`docs/CLIENT_TESTING.md`](docs/CLIENT_TESTING.md) - Comprehensive testing guide

## 🙏 Acknowledgments

- WebDriverAgent project for iOS automation
- Android SDK and ADB for Android automation
- Python asyncio and WebSocket communities

---

Built with ❤️ following SOLID principles and production-ready practices.

<citations>
<document>
<document_type>RULE</document_type>
<document_id>f4veUuNRGa4mOuco3vgDXn</document_id>
</document>
</citations>
