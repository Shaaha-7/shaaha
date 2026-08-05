"""
shaaha.wrappers.image_pillow
============================
Wraps Pillow (PIL) to expose a standardised Shaaha image API.
When OpenCV is available, Shaaha prefers it; this wrapper is used as fallback.
"""

from __future__ import annotations
from typing import Union
from pathlib import Path


def open(path: Union[str, Path]):
    """Open an image file. Returns a PIL Image."""
    from PIL import Image as _Image
    return _Image.open(str(path))


def save(image, path: Union[str, Path], **kwargs):
    """Save an image to disk."""
    image.save(str(path), **kwargs)


def resize(image, width: int, height: int):
    """Resize an image."""
    from PIL import Image as _Image
    return image.resize((width, height), _Image.LANCZOS)


def to_grayscale(image):
    """Convert image to grayscale."""
    return image.convert("L")


def to_array(image):
    """Convert PIL image to numpy array."""
    import numpy as np
    return np.array(image)


def from_array(arr):
    """Create PIL image from numpy array."""
    from PIL import Image as _Image
    return _Image.fromarray(arr)
