from urllib.parse import urlparse, urlunparse, urlencode, parse_qsl
import qrcode
import io
import base64

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)

