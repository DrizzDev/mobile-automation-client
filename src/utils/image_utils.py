"""Image processing and PNG validation utilities."""

import struct
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from PIL import Image
import io

from src.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PNGValidator:
    """PNG file validation and processing."""
    
    @staticmethod
    def validate_png(data: bytes) -> bool:
        """Validate if data is a valid PNG file."""
        try:
            # Check PNG signature
            png_signature = b'\x89PNG\r\n\x1a\n'
            if not data.startswith(png_signature):
                return False
            
            # Try to open with PIL
            with Image.open(io.BytesIO(data)) as img:
                img.verify()
                return True
        except Exception as e:
            logger.warning(f"PNG validation failed: {e}")
            return False
    
    @staticmethod
    def get_png_dimensions(data: bytes) -> Optional[Tuple[int, int]]:
        """Extract dimensions from PNG data."""
        try:
            if len(data) < 24:
                return None
                
            # PNG header: 8 bytes signature + 4 bytes length + 4 bytes type + 8 bytes dimensions
            if data[:8] != b'\x89PNG\r\n\x1a\n':
                return None
                
            # IHDR chunk should be first
            if data[12:16] != b'IHDR':
                return None
                
            width, height = struct.unpack('>II', data[16:24])
            return (width, height)
            
        except Exception as e:
            logger.warning(f"Failed to extract PNG dimensions: {e}")
            return None


class ImageProcessor:
    """Image processing utilities with optional ImageMagick support."""
    
    def __init__(self):
        self.imagemagick_available = self._check_imagemagick()
        
    def _check_imagemagick(self) -> bool:
        """Check if ImageMagick is available."""
        if not config.imagemagick_enabled:
            return False
            
        try:
            result = subprocess.run(
                ['magick', '--version'], 
                capture_output=True, 
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.info("ImageMagick not available, using PIL fallback")
            return False
    
    def resize_image(
        self, 
        image_data: bytes, 
        max_size: Optional[str] = None,
        quality: Optional[int] = None
    ) -> bytes:
        """Resize image with quality compression."""
        max_size = max_size or config.image_max_size
        quality = quality or config.image_quality
        
        if self.imagemagick_available:
            return self._resize_with_imagemagick(image_data, max_size, quality)
        else:
            return self._resize_with_pil(image_data, max_size, quality)
    
    def _resize_with_imagemagick(self, image_data: bytes, max_size: str, quality: int) -> bytes:
        """Resize using ImageMagick."""
        try:
            cmd = [
                'magick', 
                '-', 
                '-resize', max_size,
                '-quality', str(quality),
                'png:-'
            ]
            
            result = subprocess.run(
                cmd,
                input=image_data,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                logger.warning(f"ImageMagick resize failed: {result.stderr.decode()}")
                return self._resize_with_pil(image_data, max_size, quality)
                
        except Exception as e:
            logger.warning(f"ImageMagick resize error: {e}")
            return self._resize_with_pil(image_data, max_size, quality)
    
    def _resize_with_pil(self, image_data: bytes, max_size: str, quality: int) -> bytes:
        """Resize using PIL as fallback."""
        try:
            # Parse max_size (e.g., "1920x1080")
            if 'x' in max_size:
                max_width, max_height = map(int, max_size.split('x'))
            else:
                max_width = max_height = int(max_size)
            
            with Image.open(io.BytesIO(image_data)) as img:
                # Calculate new size maintaining aspect ratio
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                
                # Save to bytes
                output = io.BytesIO()
                img.save(output, format='PNG', optimize=True)
                return output.getvalue()
                
        except Exception as e:
            logger.warning(f"PIL resize error: {e}, returning original")
            return image_data
    
    def convert_to_format(self, image_data: bytes, target_format: str = 'PNG') -> bytes:
        """Convert image to target format."""
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                output = io.BytesIO()
                img.save(output, format=target_format.upper())
                return output.getvalue()
        except Exception as e:
            logger.warning(f"Format conversion error: {e}")
            return image_data


# Global instances
png_validator = PNGValidator()
image_processor = ImageProcessor()
