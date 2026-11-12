import hashlib
import hmac
import secrets

KEY_LENGTH = 64

# Mismos parámetros que `crypto.scrypt` de Node (rama NestJS).
SCRYPT_PARAMS = {"n": 16384, "r": 8, "p": 1}


# Formato guardado: "scrypt$<sal en hex>$<hash en hex>".
# La sal aleatoria hace que dos contraseñas iguales tengan hashes distintos.
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(
        password.encode(), salt=salt, dklen=KEY_LENGTH, **SCRYPT_PARAMS
    )

    return f"scrypt${salt.hex()}${key.hex()}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$")

    if len(parts) != 3 or parts[0] != "scrypt":
        return False

    salt = bytes.fromhex(parts[1])
    expected = bytes.fromhex(parts[2])
    actual = hashlib.scrypt(
        password.encode(), salt=salt, dklen=len(expected), **SCRYPT_PARAMS
    )

    # Comparación en tiempo constante para no filtrar información por timing.
    return hmac.compare_digest(actual, expected)
