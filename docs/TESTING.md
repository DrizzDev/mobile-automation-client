# Mobile Automation (Python) - WebSocket Service

This document explains how to set up, run, and test the WebSocket-based mobile automation service rewritten in Python.

Prerequisites
- macOS
- Python 3.10+
- Android SDK platform-tools (adb) installed and on PATH
- Xcode with Command Line Tools (for iOS simulators)
- WebDriverAgent running for iOS device/simulator interactions (see below)

Installation
1) Create and populate your .env
cp .env.example .env

2) Create a virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

3) (Optional) Format and type-check
black . && isort . && mypy src || true

Run the WebSocket Server
python -m src.websocket.server

Default server address: ws://localhost:8765

Test Matrix

A. Environment Sanity
- Android: Ensure `adb devices` shows at least one device/emulator
- iOS Simulator: Launch an iOS simulator in Xcode or `xcrun simctl boot <udid>`; verify `xcrun simctl list devices` shows Booted
- iOS Device (optional): Ensure go-ios is installed and `ios list` shows devices
- WebDriverAgent: Ensure WDA is running on the target iOS device/simulator and reachable at http://localhost:8100

B. Connect a Test Client
You can use the provided script or `wscat` (if installed via npm) to send messages.

Using Python (recommended):
python scripts/ws_client.py --action mobile_list_available_devices

Or wscat:
wscat -c ws://localhost:8765

Then send JSON messages like:
{"id":"1","action":"mobile_list_available_devices","params":{},"timestamp":"2025-01-01T00:00:00Z"}

C. Core Flows
1) List devices
Request:
{"id":"1","action":"mobile_list_available_devices","params":{}}

2) Auto-select default device
Request:
{"id":"2","action":"mobile_use_default_device","params":{}}

3) Select specific device
Request:
{"id":"3","action":"mobile_use_device","params":{"id":"<device_id>"}}

4) Screen interactions
- Tap:
{"id":"4","action":"mobile_click_on_screen_at_coordinates","params":{"x":100,"y":200}}
- Long press:
{"id":"5","action":"mobile_long_press_on_screen_at_coordinates","params":{"x":100,"y":200}}
- Swipe:
{"id":"6","action":"swipe_on_screen","params":{"direction":"up"}}
- Type text:
{"id":"7","action":"mobile_type_keys","params":{"text":"hello world"}}
- Press button:
{"id":"8","action":"mobile_press_button","params":{"button":"home"}}
- Open URL:
{"id":"9","action":"mobile_open_url","params":{"url":"https://example.com"}}

5) Screen state
- Screenshot (returns base64):
{"id":"10","action":"mobile_take_screenshot","params":{}}
- Elements:
{"id":"11","action":"mobile_list_elements_on_screen","params":{}}
- Screen size:
{"id":"12","action":"mobile_get_screen_size","params":{}}
- Set orientation:
{"id":"13","action":"mobile_set_orientation","params":{"orientation":"landscape"}}
- Get orientation:
{"id":"14","action":"mobile_get_orientation","params":{}}

6) App management
- List apps:
{"id":"15","action":"mobile_list_apps","params":{}}
- Launch app:
{"id":"16","action":"mobile_launch_app","params":{"packageName":"com.android.chrome"}}
- Terminate app:
{"id":"17","action":"mobile_terminate_app","params":{"packageName":"com.android.chrome"}}

D. Expected Responses
Responses follow this format:
{"id":"<same_as_request>","success":true,"data":{...},"error":null,"timestamp":"..."}
On error:
{"id":"<same_as_request>","success":false,"data":null,"error":{"type":"ActionableError|TechnicalError","message":"...","code":"..."}}

Troubleshooting
- No devices found: Make sure Android emulator is running or iOS simulator is Booted.
- ADB not found: Install Android platform-tools and ensure `adb` is in PATH.
- iOS WDA errors: Ensure WebDriverAgent is built and running. For simulators, use xcodebuild to run WDA for the simulator. For real devices, ensure proper signing and tunneling if required.
- Permissions: Some ADB commands require device to be authorized. Accept prompts on the device.

Security Notes
- If enabling WebSocket auth, set WEBSOCKET_AUTH_ENABLED=true and WEBSOCKET_AUTH_TOKEN in .env. The current server exposes only a basic structure; integrate your auth check before handling actions.

Next Steps
- Add rate limiting per connection.
- Add connection authentication and role-based access.
- Expand iOS element parsing and logs support.

