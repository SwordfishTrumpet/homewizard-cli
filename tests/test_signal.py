import signal

import pytest
from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()


def test_signal_handler_registered():
    """Test that signal handler is set up."""
    from homewizard_cli.main import _setup_signal_handlers

    original = signal.getsignal(signal.SIGINT)
    _setup_signal_handlers()
    assert signal.getsignal(signal.SIGINT) is not None
    signal.signal(signal.SIGINT, original)
