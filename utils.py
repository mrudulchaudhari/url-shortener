from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl
import qrcode
import io
import base64

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)


def encode_base62(num: int) -> str:
    """Encode an integer into a base62 string."""
    if num == 0:
        return ALPHABET[0]

    s = []
    n = int(num)
    while n>0:
        n, rem = divmod(n, BASE)
        s.append(ALPHABET[rem])
    return ''.join(reversed(s))

