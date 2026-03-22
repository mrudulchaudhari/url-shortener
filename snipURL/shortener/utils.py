"""
Utility functions for URL shortening service.
Handles base62 encoding, URL normalization, and QR code generation.
"""
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from io import BytesIO
import base64

# Optional qrcode support
try:
    import qrcode
    QRCODE_AVAILABLE = True
except ImportError:
    QRCODE_AVAILABLE = False


# Base62 alphabet for encoding IDs
BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def encode_base62(num):
    """
    Encode an integer to base62 string.
    Used to convert database IDs to short codes.

    Args:
        num (int): Number to encode

    Returns:
        str: Base62 encoded string
    """
    if num == 0:
        return BASE62_ALPHABET[0]

    result = []
    while num:
        num, remainder = divmod(num, 62)
        result.append(BASE62_ALPHABET[remainder])

    return ''.join(reversed(result))


def decode_base62(code):
    """
    Decode a base62 string back to integer.

    Args:
        code (str): Base62 encoded string

    Returns:
        int: Decoded number
    """
    num = 0
    for char in code:
        num = num * 62 + BASE62_ALPHABET.index(char)
    return num


def normalize_url(url):
    """
    Canonicalize URL before storage.
    - Enforces http/https schemes only
    - Lowercases hostname
    - Strips default ports (:80 for http, :443 for https)
    - Removes utm_* tracking parameters from query string

    Args:
        url (str): Original URL

    Returns:
        str: Normalized URL

    Raises:
        ValueError: If URL scheme is not http or https
    """
    parsed = urlparse(url)

    # Validate scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only http and https schemes are supported")

    # Lowercase hostname
    netloc = parsed.netloc.lower()

    # Strip default ports
    if parsed.scheme == 'http' and netloc.endswith(':80'):
        netloc = netloc[:-3]
    elif parsed.scheme == 'https' and netloc.endswith(':443'):
        netloc = netloc[:-4]

    # Remove utm_* tracking parameters
    if parsed.query:
        params = parse_qs(parsed.query, keep_blank_values=True)
        # Filter out utm_* parameters
        filtered_params = {k: v for k, v in params.items() if not k.startswith('utm_')}
        query = urlencode(filtered_params, doseq=True) if filtered_params else ''
    else:
        query = ''

    # Reconstruct URL
    normalized = urlunparse((
        parsed.scheme,
        netloc,
        parsed.path,
        parsed.params,
        query,
        parsed.fragment
    ))

    return normalized


def validate_custom_code(code):
    """
    Validate custom alias code.
    Must be alphanumeric and max 32 characters.

    Args:
        code (str): Custom code to validate

    Returns:
        bool: True if valid

    Raises:
        ValueError: If code is invalid with description
    """
    if not code:
        raise ValueError("Custom code cannot be empty")

    if len(code) > 32:
        raise ValueError("Custom code must be 32 characters or less")

    if not re.match(r'^[a-zA-Z0-9]+$', code):
        raise ValueError("Custom code must be alphanumeric")

    return True


def generate_qr_code(url, size=10, border=4):
    """
    Generate QR code for a URL and return as base64-encoded PNG.

    Args:
        url (str): URL to encode in QR code
        size (int): Size of QR code box (default 10)
        border (int): Border size in boxes (default 4)

    Returns:
        str: Base64-encoded PNG image (empty string if qrcode not available)
    """
    if not QRCODE_AVAILABLE:
        # Return empty string if qrcode module is not installed
        return ''

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def qr_code_to_bytes(base64_string):
    """
    Convert base64-encoded QR code back to bytes for HTTP response.

    Args:
        base64_string (str): Base64-encoded PNG

    Returns:
        bytes: PNG image bytes (empty bytes if string is empty)
    """
    if not base64_string:
        return b''
    return base64.b64decode(base64_string)
