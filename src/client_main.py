#!/usr/bin/env python3
"""
Main entry point for WebSocket client mode.

This script starts the mobile automation service as a WebSocket client
that connects to your backend server and executes automation commands.
"""

import asyncio
import signal
import sys
from pathlib import Path

# Add src to path

from config import config
from utils.logger import get_logger
from websocket.client import start_client, stop_client, RetryConfig

logger = get_logger(__name__)


async def main():
    """Main entry point for client mode."""
    logger.info("Starting Mobile Automation Service (Client Mode)")
    
    # Create retry configuration from config
    retry_config = RetryConfig(
        max_retries=config.connection_retry_max,
        base_delay=config.connection_retry_delay,
        max_delay=config.connection_retry_max_delay,
        health_check_interval=config.health_check_interval,
        connection_timeout=config.connection_timeout
    )
    
    # Start the client
    success = await start_client(config.backend_server_url, retry_config)
    if not success:
        logger.error("Failed to start WebSocket client")
        sys.exit(1)
    
    logger.info("WebSocket client started successfully")
    logger.info(f"Connected to backend server: {config.backend_server_url}")
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(stop_client())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Keep the client running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    finally:
        await stop_client()
        logger.info("WebSocket client stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
