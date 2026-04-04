"""Unit tests for Sentry initialization helper."""

from unittest.mock import patch

from app.core.sentry import init_sentry


@patch("app.core.sentry.sentry_sdk")
@patch("app.core.sentry.settings")
def test_init_sentry_noop_when_dsn_empty(mock_settings, mock_sentry_sdk):
    """Should not call sentry_sdk.init when DSN is empty."""
    mock_settings.SENTRY_DSN = ""
    init_sentry()
    mock_sentry_sdk.init.assert_not_called()


@patch("app.core.sentry.sentry_sdk")
@patch("app.core.sentry.settings")
def test_init_sentry_calls_init_when_dsn_set(mock_settings, mock_sentry_sdk):
    """Should call sentry_sdk.init with correct params when DSN is provided."""
    mock_settings.SENTRY_DSN = "https://key@sentry.io/0"
    mock_settings.SENTRY_TRACES_SAMPLE_RATE = 0.2
    mock_settings.ENVIRONMENT = "test"

    init_sentry(release="1.0.0")

    mock_sentry_sdk.init.assert_called_once_with(
        dsn="https://key@sentry.io/0",
        traces_sample_rate=0.2,
        environment="test",
        release="1.0.0",
    )


@patch("app.core.sentry.sentry_sdk")
@patch("app.core.sentry.settings")
def test_init_sentry_default_release(mock_settings, mock_sentry_sdk):
    """Should use '0.1.0' as default release."""
    mock_settings.SENTRY_DSN = "https://key@sentry.io/0"
    mock_settings.SENTRY_TRACES_SAMPLE_RATE = 0.1
    mock_settings.ENVIRONMENT = "prod"

    init_sentry()

    call_kwargs = mock_sentry_sdk.init.call_args[1]
    assert call_kwargs["release"] == "0.1.0"
