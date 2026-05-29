import signal

from homewizard_cli.main import _setup_signal_handlers, _signal_handler


def test_signal_handler_registered():
    """Test that signal handler is set up."""
    original = signal.getsignal(signal.SIGINT)
    _setup_signal_handlers()
    assert signal.getsignal(signal.SIGINT) is _signal_handler
    signal.signal(signal.SIGINT, original)
