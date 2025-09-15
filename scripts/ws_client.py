#!/usr/bin/env python3
"""
WebSocket client script for testing mobile automation service.

Usage:
    python scripts/ws_client.py --action mobile_list_available_devices
    python scripts/ws_client.py --action mobile_take_screenshot
    python scripts/ws_client.py --action mobile_click_on_screen_at_coordinates --params '{"x": 100, "y": 200}'
"""

import os
import sys
import json
import asyncio
import argparse
from typing import Dict, Any
from datetime import datetime
import uuid

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import websockets
except ImportError:
    print("Error: websockets package not installed. Please run: pip install websockets")
    sys.exit(1)

from src.config import config


async def send_message(action: str, params: Dict[str, Any] = None) -> None:
    """Send a message to the WebSocket server and print response."""
    
    params = params or {}
    message = {
        "id": str(uuid.uuid4()),
        "action": action,
        "params": params,
        "timestamp": datetime.now().isoformat() + "Z"
    }
    
    uri = f"ws://{config.websocket_host}:{config.websocket_port}"
    
    try:
        async with websockets.connect(uri) as websocket:
            # Send message
            message_json = json.dumps(message)
            print(f"Sending: {message_json}")
            await websocket.send(message_json)
            
            # Wait for response
            response = await websocket.recv()
            print(f"Received: {response}")
            
            # Parse and pretty print response
            try:
                response_data = json.loads(response)
                print("\n--- Parsed Response ---")
                print(json.dumps(response_data, indent=2))
                
                if response_data.get("success"):
                    print(f"\n✅ Action '{action}' completed successfully")
                else:
                    error = response_data.get("error", {})
                    print(f"\n❌ Action '{action}' failed:")
                    print(f"   Type: {error.get('type', 'Unknown')}")
                    print(f"   Code: {error.get('code', 'Unknown')}")
                    print(f"   Message: {error.get('message', 'Unknown error')}")
                    
            except json.JSONDecodeError:
                print("Response is not valid JSON")
                
    except ConnectionRefusedError:
        print(f"❌ Connection refused. Is the server running at {uri}?")
        print("Start the server with: python -m src.websocket.server")
    except Exception as e:
        print(f"❌ Error: {e}")


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(description="WebSocket client for mobile automation testing")
    parser.add_argument("--action", required=True, help="Action to perform")
    parser.add_argument("--params", help="JSON string of parameters", default="{}")
    
    args = parser.parse_args()
    
    try:
        params = json.loads(args.params)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in --params: {e}")
        return
    
    print(f"🔌 Connecting to ws://{config.websocket_host}:{config.websocket_port}")
    print(f"📤 Action: {args.action}")
    if params:
        print(f"📋 Params: {params}")
    print()
    
    asyncio.run(send_message(args.action, params))


if __name__ == "__main__":
    main()
