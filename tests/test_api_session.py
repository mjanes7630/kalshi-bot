from unittest.mock import Mock

import pytest

from kalshi_bot.api.session import validate_api_credentials
from kalshi_bot.config import Settings


def test_validate_api_credentials_requires_api_key_id() -> None:
    settings = Mock(spec=Settings)
    settings.api_key_id = None
    settings.private_key_path = Mock()

    with pytest.raises(ValueError, match="KALSHI_BOT_API_KEY_ID is required."):
        validate_api_credentials(settings)


def test_validate_api_credentials_requires_private_key_path() -> None:
    settings = Mock(spec=Settings)
    settings.api_key_id = "test-key-id"
    settings.private_key_path = None

    with pytest.raises(ValueError, match="KALSHI_BOT_PRIVATE_KEY_PATH is required."):
        validate_api_credentials(settings)
