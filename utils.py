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


def normalize_url(url: str) -> str:
    """Normalize and validate a URL.
    -ensure url is http/https
    - lowercase host, removes default ports
    - drops utm_* query params(optional)
    Raises ValueError if url is invalid.
    """

    p = urlparse(url, scheme="http")
    if p.scheme not in ("http", "https"):
        raise ValueError("only http and https schemes are supported")

    netloc = p.netloc.lower()
    if (p.scheme == 'http' and netloc.endswith(':80')) or (p.scheme == 'https' and netloc.endswith(':443')):
        netloc = netloc.rsplit(':', 1)[0]

    qs = [(k, v) for k, v in parse_qsl(p.query) if not k.startswith('utm_')]
    return urlunparse((p.scheme, netloc, p.path or '/', p.params, urlencode(qs), p.fragment))