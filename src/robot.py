"""Robot interface and actionable error classes."""

from abc import ABC, abstractmethod
from typing import List, Optional

from enums import (
    InstalledApp,
    ScreenElement,
    ScreenSize,
    SwipeDirection,
    Button,
    Orientation,
    LogOptions,
)


class ActionableError(Exception):
    """An error that the user can act upon to resolve (e.g., no device selected)."""

    def __init__(self, message: str, code: str = "ACTIONABLE_ERROR") -> None:
        super().__init__(message)
        self.code = code


class Robot(ABC):
    """Abstract Robot interface for device operations."""

    # Device lifecycle
    @abstractmethod
    async def list_apps(self) -> List[InstalledApp]:
        raise NotImplementedError

    @abstractmethod
    async def get_installed_apps(self) -> List[dict]:
        """Get installed apps in dictionary format."""
        raise NotImplementedError

    @abstractmethod
    async def launch_app(self, package_name: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def terminate_app(self, package_name: str) -> None:
        raise NotImplementedError
    
    @abstractmethod
    async def is_app_running(self, package_name: str) -> bool:
        """Check if specific app is currently running."""
        raise NotImplementedError
    
    @abstractmethod
    async def get_running_apps(self) -> List[dict]:
        """Get list of currently running apps."""
        raise NotImplementedError

    # Screen interaction
    @abstractmethod
    async def tap(self, x: int, y: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def long_press(self, x: int, y: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def swipe(self, direction: SwipeDirection) -> None:
        raise NotImplementedError

    @abstractmethod
    async def swipe_from_coordinate(
        self, x: int, y: int, direction: SwipeDirection, distance: Optional[int] = None
    ) -> None:
        raise NotImplementedError

    # Input
    @abstractmethod
    async def send_keys(self, text: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def press_button(self, button: Button) -> None:
        raise NotImplementedError

    @abstractmethod
    async def open_url(self, url: str) -> None:
        raise NotImplementedError

    # Screen state
    @abstractmethod
    async def get_screenshot(self) -> bytes:
        raise NotImplementedError

    @abstractmethod
    async def get_screen_size(self) -> ScreenSize:
        raise NotImplementedError

    @abstractmethod
    async def get_elements_on_screen(self) -> List[ScreenElement]:
        raise NotImplementedError
    
    @abstractmethod
    async def get_elements(self) -> List[dict]:
        """Get screen elements in dictionary format for API compatibility."""
        raise NotImplementedError

    @abstractmethod
    async def set_orientation(self, orientation: Orientation) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_orientation(self) -> Orientation:
        raise NotImplementedError

    # Debugging
    @abstractmethod
    async def get_device_logs(self, options: Optional[LogOptions] = None) -> str:
        raise NotImplementedError

