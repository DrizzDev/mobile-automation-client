"""Core types and enums for mobile automation service."""

from enum import Enum
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, Field
from datetime import datetime


class DeviceType(str, Enum):
    """Device type enumeration."""
    ANDROID = "android"
    IOS = "ios"
    SIMULATOR = "simulator"


class SwipeDirection(str, Enum):
    """Swipe direction enumeration."""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


class Button(str, Enum):
    """Physical/virtual button enumeration."""
    HOME = "home"
    BACK = "back"
    MENU = "menu"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    POWER = "power"
    RECENT_APPS = "recent_apps"


class Orientation(str, Enum):
    """Screen orientation enumeration."""
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    PORTRAIT_UPSIDE_DOWN = "portrait_upside_down"
    LANDSCAPE_LEFT = "landscape_left"
    LANDSCAPE_RIGHT = "landscape_right"


class LogLevel(str, Enum):
    """Log level enumeration."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


# Data Models
class ScreenSize(BaseModel):
    """Screen size representation."""
    width: int
    height: int
    
    
class DeviceInfo(BaseModel):
    """Device information."""
    id: str
    name: str
    type: DeviceType
    platform_version: Optional[str] = None
    model: Optional[str] = None
    is_emulator: bool = False
    status: str = "available"


class InstalledApp(BaseModel):
    """Installed application information."""
    package_name: str
    app_name: str
    version: Optional[str] = None
    is_system_app: bool = False


class ScreenElement(BaseModel):
    """UI element on screen."""
    id: Optional[str] = None
    class_name: Optional[str] = None
    text: Optional[str] = None
    content_desc: Optional[str] = None
    resource_id: Optional[str] = None
    bounds: Dict[str, int] = Field(default_factory=dict)  # {x, y, width, height}
    clickable: bool = False
    focusable: bool = False
    enabled: bool = True
    visible: bool = True
    children: List['ScreenElement'] = Field(default_factory=list)


class LogOptions(BaseModel):
    """Log retrieval options."""
    level: Optional[LogLevel] = None
    tag_filter: Optional[str] = None
    max_lines: int = 100
    since_timestamp: Optional[datetime] = None


# WebSocket Message Models
class WebSocketRequest(BaseModel):
    """WebSocket request message."""
    id: str
    action: str
    params: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class WebSocketResponse(BaseModel):
    """WebSocket response message."""
    id: str
    success: bool
    data: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorInfo(BaseModel):
    """Error information."""
    type: str
    message: str
    code: str
    traceback: Optional[str] = None


# Update forward references
ScreenElement.model_rebuild()
