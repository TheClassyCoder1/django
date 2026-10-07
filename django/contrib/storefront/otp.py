import base64
import hashlib
import hmac
import struct
import time


def totp(secret, for_time=None, step=30, digits=6):
    key = base64.b32decode(secret.upper() + "=" * (-len(secret) % 8))
    counter = int((time.time() if for_time is None else for_time) // step)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = int.from_bytes(digest[offset : offset + 4], "big") & 0x7FFFFFFF
    return str(code % 10**digits).zfill(digits)
