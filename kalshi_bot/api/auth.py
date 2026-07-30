import base64
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def load_private_key(private_key_path: Path) -> rsa.RSAPrivateKey:
    private_key_data = private_key_path.read_bytes()

    private_key = serialization.load_pem_private_key(
        private_key_data,
        password=None,
    )

    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise TypeError("Kalshi private key must be an RSA private key.")

    return private_key


def create_auth_headers(
    *,
    api_key_id: str,
    private_key: rsa.RSAPrivateKey,
    timestamp: str,
    method: str,
    path: str,
) -> dict[str, str]:
    return {
        "KALSHI-ACCESS-KEY": api_key_id,
        "KALSHI-ACCESS-SIGNATURE": sign_request(
            private_key=private_key,
            timestamp=timestamp,
            method=method,
            path=path,
        ),
        "KALSHI-ACCESS-TIMESTAMP": timestamp,
    }


def sign_request(
    *,
    private_key: rsa.RSAPrivateKey,
    timestamp: str,
    method: str,
    path: str,
) -> str:
    path_without_query = path.split("?", maxsplit=1)[0]
    message = f"{timestamp}{method.upper()}{path_without_query}".encode()

    signature = private_key.sign(
        message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )

    return base64.b64encode(signature).decode("utf-8")
