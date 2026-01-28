import pytest
import base64
from utils import encode_base62, normalize_url#, qr_png_base64


def test_encode_base62_simple():
    """Test simple single digit encoding"""
    assert encode_base62(1) == '1'
    assert encode_base62(10) == 'a'
    assert encode_base62(36) == 'A'

def test_encode_base62_boundary():
    """Test boundary of single digit encoding"""
    assert encode_base62(61) == 'Z'
    assert encode_base62(62) == '10'
