"""Configuration management for mobile automation service."""

import os
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv


class Config(BaseModel):
    """Application configuration."""

    # WebSocket Server
    websocket_host: str = "localhost"
    websocket_port: int = 8765
    websocket_max_connections: int = 10

    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_file_path: str = "logs/mobile-automation.log"

    # Android
    adb_path: str = "adb"
    adb_timeout: int = 30
    adb_max_buffer_size: int = 4194304

    # iOS
    wda_port: int = 8100
    wda_tunnel_port: int = 60105
    simctl_path: str = "xcrun simctl"

    # Image Processing
    imagemagick_enabled: bool = False
    image_max_size: str = "1920x1080"
    image_quality: int = 90

    # Device Configuration
    device_selection_timeout: int = 30
    auto_select_single_device: bool = True

    # Security
    websocket_auth_enabled: bool = False
    websocket_auth_token: Optional[str] = None

    # Monitoring & Telemetry
    telemetry_enabled: bool = False
    health_check_interval: int = 60
    metrics_enabled: bool = False

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        load_dotenv()
        
        return cls(
            websocket_host=os.getenv("WEBSOCKET_HOST", "localhost"),
            websocket_port=int(os.getenv("WEBSOCKET_PORT", "8765")),
            websocket_max_connections=int(os.getenv("WEBSOCKET_MAX_CONNECTIONS", "10")),
            
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            log_file_path=os.getenv("LOG_FILE_PATH", "logs/mobile-automation.log"),
            
            adb_path=os.getenv("ADB_PATH", "adb"),
            adb_timeout=int(os.getenv("ADB_TIMEOUT", "30")),
            adb_max_buffer_size=int(os.getenv("ADB_MAX_BUFFER_SIZE", "4194304")),
            
            wda_port=int(os.getenv("WDA_PORT", "8100")),
            wda_tunnel_port=int(os.getenv("WDA_TUNNEL_PORT", "60105")),
            simctl_path=os.getenv("SIMCTL_PATH", "xcrun simctl"),
            
            imagemagick_enabled=os.getenv("IMAGEMAGICK_ENABLED", "false").lower() == "true",
            image_max_size=os.getenv("IMAGE_MAX_SIZE", "1920x1080"),
            image_quality=int(os.getenv("IMAGE_QUALITY", "90")),
            
            device_selection_timeout=int(os.getenv("DEVICE_SELECTION_TIMEOUT", "30")),
            auto_select_single_device=os.getenv("AUTO_SELECT_SINGLE_DEVICE", "true").lower() == "true",
            
            websocket_auth_enabled=os.getenv("WEBSOCKET_AUTH_ENABLED", "false").lower() == "true",
            websocket_auth_token=os.getenv("WEBSOCKET_AUTH_TOKEN"),
            
            telemetry_enabled=os.getenv("TELEMETRY_ENABLED", "false").lower() == "true",
            health_check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "60")),
            metrics_enabled=os.getenv("METRICS_ENABLED", "false").lower() == "true",
        )


# Global configuration instance
config = Config.from_env()
