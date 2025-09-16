"""Session management for S-Enricher backend server."""

import uuid
import requests
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

from config import config
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SessionInfo:
    """Container for session information from S-Enricher."""
    session_id: str
    websocket_url: str
    authentication_token: str
    created_at: float
    expires_at: Optional[float] = None


class SessionManager:
    """Manages sessions and authentication with S-Enricher backend server."""
    
    def __init__(self, enricher_base_url: str, device_id: Optional[str] = None):
        """
        Initialize session manager.
        
        Args:
            enricher_base_url: Base URL for S-Enricher REST API (e.g., "http://localhost:8003")
            device_id: Unique device identifier (auto-generated if not provided)
        """
        self.enricher_base_url = enricher_base_url.rstrip('/')
        self.device_id = device_id or f"mobile-client-{uuid.uuid4().hex[:8]}"
        self.current_session: Optional[SessionInfo] = None
        
        # Session timeout buffer (renew session 5 minutes before expiry)
        self.session_timeout_buffer_seconds = 300
        
    def _extract_base_url_from_websocket_url(self, backend_url: str) -> str:
        """
        Extract the base URL for S-Enricher REST API from WebSocket URL.
        
        Args:
            backend_url: WebSocket URL from config (e.g., "ws://localhost:8675")
            
        Returns:
            HTTP base URL for REST API (e.g., "http://localhost:8003")
        """
        parsed = urlparse(backend_url)
        
        # Convert WebSocket scheme to HTTP
        if parsed.scheme in ('ws', 'wss'):
            http_scheme = 'https' if parsed.scheme == 'wss' else 'http'
        else:
            http_scheme = parsed.scheme or 'http'
        
        # Default to port 8003 for S-Enricher REST API if WebSocket is on 8675
        if parsed.port == 8675:
            port = 8003
        else:
            port = parsed.port
            
        if port:
            return f"{http_scheme}://{parsed.hostname}:{port}"
        else:
            return f"{http_scheme}://{parsed.hostname}"
    
    def create_session(self, provider: str = "LOCAL_CLIENT", platform: str = "ANDROID") -> SessionInfo:
        """
        Create a new session with S-Enricher.
        
        Args:
            provider: Device provider type (default: LOCAL_CLIENT)
            platform: Platform type (default: ANDROID)
            
        Returns:
            SessionInfo object with session details
            
        Raises:
            Exception: If session creation fails
        """
        session_id = f"mobile-session-{uuid.uuid4().hex[:16]}"
        
        # If enricher_base_url is not set, derive it from backend_server_url
        if not hasattr(self, 'enricher_base_url') or not self.enricher_base_url:
            self.enricher_base_url = self._extract_base_url_from_websocket_url(config.backend_server_url)
        
        create_session_url = f"{self.enricher_base_url}/v1/sessions"
        
        payload = {
            "device_id": self.device_id,
            "session_id": session_id,
            "provider": provider,
            "configuration": {
                "platform": platform
            }
        }
        
        try:
            logger.info(f"Creating session with S-Enricher at {create_session_url}")
            logger.debug(f"Session payload: {payload}")
            
            response = requests.post(
                create_session_url,
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            if data.get("status") != "success":
                raise Exception(f"Session creation failed: {data}")
            
            session_data = data["data"]
            
            # Parse WebSocket URL to get the correct format
            websocket_url = session_data["websocket_url"]
            auth_token = session_data["authentication_token"]
            
            # Ensure WebSocket URL has correct scheme and format
            if not websocket_url.startswith(('ws://', 'wss://')):
                # If URL doesn't have scheme, assume it needs to be constructed
                parsed_backend = urlparse(config.backend_server_url)
                websocket_url = f"{parsed_backend.scheme}://{websocket_url}"
            
            # Add authentication token as query parameter
            separator = '&' if '?' in websocket_url else '?'
            authenticated_url = f"{websocket_url}{separator}token={auth_token}"
            
            session_info = SessionInfo(
                session_id=session_data["session_id"],
                websocket_url=authenticated_url,
                authentication_token=auth_token,
                created_at=time.time(),
                expires_at=time.time() + 3600  # Assume 1 hour expiry
            )
            
            self.current_session = session_info
            
            logger.info(f"Session created successfully: {session_info.session_id}")
            logger.debug(f"WebSocket URL: {session_info.websocket_url}")
            
            return session_info
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed while creating session: {e}")
            raise Exception(f"Failed to create session with S-Enricher: {e}")
        except Exception as e:
            logger.error(f"Session creation failed: {e}")
            raise
    
    def get_current_session(self, auto_renew: bool = True) -> Optional[SessionInfo]:
        """
        Get current session, optionally renewing if expired.
        
        Args:
            auto_renew: Whether to automatically renew expired sessions
            
        Returns:
            Current session info or None if no valid session
        """
        if not self.current_session:
            return None
        
        # Check if session is expired or about to expire
        if self.current_session.expires_at:
            time_until_expiry = self.current_session.expires_at - time.time()
            if time_until_expiry <= self.session_timeout_buffer_seconds:
                logger.info("Session expired or about to expire")
                if auto_renew:
                    try:
                        return self.create_session()
                    except Exception as e:
                        logger.error(f"Failed to renew session: {e}")
                        return None
                else:
                    return None
        
        return self.current_session
    
    def delete_session(self) -> bool:
        """
        Delete the current session from S-Enricher.
        
        Returns:
            True if deletion successful, False otherwise
        """
        if not self.current_session:
            return True
            
        try:
            delete_url = f"{self.enricher_base_url}/v1/sessions/{self.current_session.session_id}"
            response = requests.delete(delete_url, timeout=10)
            
            # Consider 404 as success (session already deleted)
            if response.status_code in (200, 404):
                logger.info(f"Session {self.current_session.session_id} deleted successfully")
                self.current_session = None
                return True
            else:
                logger.warning(f"Session deletion returned status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False
    
    def get_authenticated_websocket_url(self) -> Optional[str]:
        """
        Get the authenticated WebSocket URL for the current session.
        
        Returns:
            Full WebSocket URL with authentication token, or None if no session
        """
        session = self.get_current_session()
        return session.websocket_url if session else None


# Global session manager instance
session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get or create the global session manager instance."""
    global session_manager
    if session_manager is None:
        # Extract base URL from backend configuration
        parsed_url = urlparse(config.backend_server_url)
        if parsed_url.port == 8675:
            # WebSocket port, convert to REST API port
            base_url = f"http://{parsed_url.hostname}:8003"
        else:
            # Use the same host/port for REST API
            scheme = 'https' if parsed_url.scheme == 'wss' else 'http'
            port_part = f":{parsed_url.port}" if parsed_url.port else ""
            base_url = f"{scheme}://{parsed_url.hostname}{port_part}"
        
        session_manager = SessionManager(base_url)
        logger.info(f"Created global session manager for {base_url}")
    
    return session_manager


def cleanup_session_manager():
    """Cleanup the global session manager."""
    global session_manager
    if session_manager:
        session_manager.delete_session()
        session_manager = None