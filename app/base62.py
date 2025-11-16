ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)

def encode_base62(num: int) -> str:
    if num == 0:
        return ALPHABET[0]

    arr = []
    while num:
        num, rem = divmod(num, BASE)
        arr.append(ALPHABET[rem])
    return ''.join(reversed(arr))


def decode_base62(s: str) -> int:
    num = 0
    for ch in s:
        num = num*BASE + ALPHABET.index(ch)
    return num

