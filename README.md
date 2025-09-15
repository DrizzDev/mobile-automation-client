# Mobile Automation Service

A production-ready, cross-platform mobile device automation service built in Python with WebSocket communication. This service provides comprehensive automation capabilities for Android devices and iOS simulators.

## 🚀 Features

- **Cross-Platform Support**: Android (via ADB) and iOS Simulators (via WebDriverAgent/simctl)
- **WebSocket API**: Real-time communication with JSON message protocol
- **Production Ready**: Docker support, health checks, logging, configuration management
- **Extensible Architecture**: SOLID principles with clear separation of concerns
- **Error Handling**: Actionable vs. technical error classification
- **Session Management**: Per-connection device selection and state
- **Image Processing**: Optional ImageMagick integration with PIL fallback
- **Testing Suite**: Unit tests and integration test framework

## 📋 Prerequisites

### macOS Development
- Python 3.10+
- Android SDK Platform Tools (for `adb`)
- Xcode with Command Line Tools (for iOS simulators)
- WebDriverAgent (for iOS simulator interaction)

### Production Deployment
- Docker and Docker Compose
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
# Edit .env with your configuration
```

### Docker Deployment
```bash
# Build the Docker image
docker build -t mobile-automation .

# Run with Docker Compose (recommended)
docker-compose up -d
```

## 🏃‍♂️ Quick Start

### Start the Server
```bash
# Development
python -m src.websocket.server

# Production with Docker
docker run -p 8765:8765 mobile-automation
```

The server will start at `ws://localhost:8765` by default.

### Test the Service
```bash
# List available devices
python scripts/ws_client.py --action mobile_list_available_devices

# Auto-select a device
python scripts/ws_client.py --action mobile_use_default_device

# Take a screenshot
python scripts/ws_client.py --action mobile_take_screenshot
```

## 📡 WebSocket API

### Message Format

**Request:**
```json
{
  "id": "unique_request_id",
  "action": "mobile_take_screenshot",
  "params": {
    "x": 100,
    "y": 200
  },
  "timestamp": "2025-01-01T00:00:00Z"
}
```

**Response (Success):**
```json
{
  "id": "unique_request_id",
  "success": true,
  "data": {
    "image_base64": "iVBORw0KGgoAAAANSU..."
  },
  "error": null,
  "timestamp": "2025-01-01T00:00:01Z"
}
```

**Response (Error):**
```json
{
  "id": "unique_request_id",
  "success": false,
  "data": null,
  "error": {
    "type": "ActionableError",
    "message": "No device selected. Use mobile_use_default_device first.",
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

The service follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                WebSocket Communication Layer                │
│  - Connection management and session handling              │
│  - Message routing and error handling                      │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                    Device Manager                          │
│  - Multi-platform device discovery                        │
│  - Robot instantiation and lifecycle                      │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                   Robot Abstraction                        │
│  - Common interface for all device operations             │
│  - Error handling and response normalization              │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│              Platform Implementations                       │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │   Android ADB   │  │  iOS WDA/simctl │                  │
│  │   Integration   │  │   Integration   │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     Utility Layer                          │
│  - Logging, Configuration, Image Processing               │
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
See [`docs/TESTING.md`](docs/TESTING.md) for comprehensive testing procedures and examples.

## 📝 Configuration

All configuration is handled via environment variables. Copy `.env.example` to `.env` and customize:

```bash
# WebSocket Server
WEBSOCKET_HOST=localhost
WEBSOCKET_PORT=8765

# Device Paths
ADB_PATH=adb
SIMCTL_PATH=xcrun simctl

# Security
WEBSOCKET_AUTH_ENABLED=false
WEBSOCKET_AUTH_TOKEN=your-secret-token

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
    ports:
      - "8765:8765"
    environment:
      - LOG_LEVEL=INFO
      - WEBSOCKET_HOST=0.0.0.0
    volumes:
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "python", "scripts/health_check.py"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Monitoring
- Health check endpoint available via `scripts/health_check.py`
- Structured logging with configurable levels
- Optional telemetry and metrics collection

## 🔒 Security Considerations

- WebSocket authentication disabled by default (enable with `WEBSOCKET_AUTH_ENABLED=true`)
- Non-root user in Docker container
- Input validation via Pydantic models
- Configurable rate limiting (planned)
- Secure device access patterns

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

## 🙏 Acknowledgments

- Original TypeScript implementation architecture
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
