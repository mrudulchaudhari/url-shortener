import pytest
import base64
from utils import encode_base62, normalize_url, qr_png_base64


def test_encode_base62_simple():
    """Test simple single digit encoding"""
    assert encode_base62(1) == '1'
    assert encode_base62(10) == 'a'
    assert encode_base62(36) == 'A'

def test_encode_base62_boundary():
    """Test boundary of single digit encoding"""
    assert encode_base62(61) == 'Z'
    assert encode_base62(62) == '10'


def test_encode_base62_large_number():
    """Test a larger number ensures the algorithm holds up."""
    # 62^2 + 62 + 1 = 3844 + 62 + 1 = 3907 => '111'
    assert encode_base62(3907) == "111"


# --- normalize_url Tests ---
# TODO: add it soon

# --- qr_png_base64 Tests ---

def test_qr_png_base64_output_format():
    """Test that the output is a valid base64 encoded string."""
    data = "https://example.com"
    result = qr_png_base64(data)

    # It should be a string
    assert isinstance(result, str)

    # It should be decodable back to bytes
    decoded = base64.b64decode(result)

    # The bytes should start with PNG magic number
    assert decoded.startswith(b'\x89PNG')