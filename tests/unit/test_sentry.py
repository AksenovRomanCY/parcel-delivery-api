"""Unit tests for Sentry initialization helper."""

from unittest.mock import MagicMock, patch

from app.core.sentry import init_sentry


@patch("app.core.sentry.sentry_sdk")
@patch("app.core.sentry.settings")
def test_init_sentry_noop_when_dsn_empty(
    mock_settings: MagicMock,
    mock_sentry_sdk: MagicMock,
) -> None:
    """Should not call sentry_sdk.init when DSN is empty."""
    # Arrange
    mock_settings.SENTRY_DSN = ""

    # Act
    init_sentry()

    # Assert
    mock_sentry_sdk.init.assert_not_called()


@patch("app.core.sentry.sentry_sdk")
@patch("app.core.sentry.settings")
def test_init_sentry_calls_init_when_dsn_set(
    mock_settings: MagicMock,
    mock_sentry_sdk: MagicMock,
) -> None:
    """Should call sentry_sdk.init with correct params when DSN is provided."""
    # Arrange
    mock_settings.SENTRY_DSN = "https://key@sentry.io/0"
    mock_settings.SENTRY_TRACES_SAMPLE_RATE = 0.2
    mock_settings.ENVIRONMENT = "test"

    # Act
    init_sentry(release="1.0.0")

    # Assert
    mock_sentry_sdk.init.assert_called_once_with(
        dsn="https://key@sentry.io/0",
        traces_sample_rate=0.2,
        environment="test",
        release="1.0.0",
    )


@patch("app.core.sentry.sentry_sdk")
@patch("app.core.sentry.settings")
def test_init_sentry_default_release(
    mock_settings: MagicMock,
    mock_sentry_sdk: MagicMock,
) -> None:
    """Should use '1.0.0' as default release."""
    # Arrange
    mock_settings.SENTRY_DSN = "https://key@sentry.io/0"
    mock_settings.SENTRY_TRACES_SAMPLE_RATE = 0.1
    mock_settings.ENVIRONMENT = "prod"

    # Act
    init_sentry()

    # Assert
    call_kwargs = mock_sentry_sdk.init.call_args[1]
    assert call_kwargs["release"] == "1.0.0"
