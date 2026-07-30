import base64
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from kalshi_bot.api.auth import create_auth_headers, load_private_key, sign_request


def test_sign_request_creates_valid_signature_without_query_parameters() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    timestamp = "1703123456789"
    method = "GET"
    path = "/trade-api/v2/portfolio/balance?test=true"

    signature = sign_request(
        private_key=private_key,
        timestamp=timestamp,
        method=method,
        path=path,
    )

    assert isinstance(signature, str)

    expected_message = f"{timestamp}{method}/trade-api/v2/portfolio/balance".encode()

    private_key.public_key().verify(
        base64.b64decode(signature),
        expected_message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )


def test_load_private_key_reads_rsa_key_from_file(tmp_path: Path) -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_key_path = tmp_path / "kalshi-private-key.txt"

    private_key_path.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    loaded_private_key = load_private_key(private_key_path)

    assert loaded_private_key.private_numbers() == private_key.private_numbers()


def test_create_auth_headers_returns_required_kalshi_headers() -> None:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    timestamp = "1703123456789"
    method = "GET"
    path = "/trade-api/v2/portfolio/balance"

    headers = create_auth_headers(
        api_key_id="test-key-id",
        private_key=private_key,
        timestamp=timestamp,
        method=method,
        path=path,
    )

    assert set(headers) == {
        "KALSHI-ACCESS-KEY",
        "KALSHI-ACCESS-SIGNATURE",
        "KALSHI-ACCESS-TIMESTAMP",
    }
    assert headers["KALSHI-ACCESS-KEY"] == "test-key-id"
    assert headers["KALSHI-ACCESS-TIMESTAMP"] == timestamp

    expected_message = f"{timestamp}{method}{path}".encode()

    private_key.public_key().verify(
        base64.b64decode(headers["KALSHI-ACCESS-SIGNATURE"]),
        expected_message,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )
