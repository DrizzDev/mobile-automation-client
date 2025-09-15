#!/usr/bin/env python3
"""
Health check script for mobile automation service.

Used by Docker health checks and monitoring systems.
"""

import os
import sys
import asyncio
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import websockets
except ImportError:
    print("Health check failed: websockets not available")
    sys.exit(1)

from src.config import config


async def health_check() -> bool:
    """
    Perform health check by connecting to WebSocket server.
    
    Returns:
        bool: True if healthy, False otherwise
    """
    try:
        uri = f"ws://{config.websocket_host}:{config.websocket_port}"
        
        # Try to connect with a short timeout
        async with websockets.connect(uri, timeout=5) as websocket:
            # Send a simple ping message
            ping_message = {
                "id": "health-check",
                "action": "mobile_list_available_devices",
                "params": {},
                "timestamp": datetime.now().isoformat() + "Z"
            }
            
            await websocket.send(json.dumps(ping_message))
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            
            # Parse response
            response_data = json.loads(response)
            
            # Check if we got a valid response
            if "success" in response_data and "id" in response_data:
                return True
            else:
                print(f"Health check failed: Invalid response format")
                return False
                
    except asyncio.TimeoutError:
        print("Health check failed: Timeout")
        return False
    except ConnectionRefusedError:
        print("Health check failed: Connection refused")
        return False
    except Exception as e:
        print(f"Health check failed: {e}")
        return False


def main():
    """Main health check function."""
    try:
        is_healthy = asyncio.run(health_check())
        
        if is_healthy:
            print("✅ Service is healthy")
            sys.exit(0)
        else:
            print("❌ Service is unhealthy")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
