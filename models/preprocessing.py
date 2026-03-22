"""
Image preprocessing utilities for medical imaging
"""
from PIL import Image
import numpy as np
import io
from typing import Tuple


def validate_image_format(image_bytes: bytes, max_size: int = 10 * 1024 * 1024) -> bool:
    """
    Validate image format and size
    
    Args:
        image_bytes: Raw image bytes
        max_size: Maximum allowed size in bytes
        
    Returns:
        True if valid, raises ValueError otherwise
    """
    if len(image_bytes) > max_size:
        raise ValueError(f"Image size {len(image_bytes)} exceeds maximum {max_size}")
    
    try:
        image = Image.open(io.BytesIO(image_bytes))
        # Verify it's a valid image
        image.verify()
        return True
    except Exception as e:
        raise ValueError(f"Invalid image format: {e}")


def normalize_medical_image(image: Image.Image, modality: str = 'xray') -> np.ndarray:
    """
    Normalize medical image based on modality
    
    Args:
        image: PIL Image
        modality: Type of medical image (xray, ct, mri, etc.)
        
    Returns:
        Normalized numpy array
    """
    img_array = np.array(image)
    
    if modality in ['xray', 'ct']:
        # Apply windowing for radiological images
        img_array = apply_window(img_array, window_center=40, window_width=400)
    
    # Normalize to [0, 1]
    img_min = img_array.min()
    img_max = img_array.max()
    
    if img_max > img_min:
        img_array = (img_array - img_min) / (img_max - img_min)
    
    return img_array


def apply_window(image: np.ndarray, window_center: int, window_width: int) -> np.ndarray:
    """
    Apply windowing to medical image (HU windowing for CT)
    
    Args:
        image: Image array
        window_center: Center of window
        window_width: Width of window
        
    Returns:
        Windowed image array
    """
    img_min = window_center - window_width // 2
    img_max = window_center + window_width // 2
    
    windowed = np.clip(image, img_min, img_max)
    return windowed
