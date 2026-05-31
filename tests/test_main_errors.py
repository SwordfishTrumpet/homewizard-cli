from unittest.mock import patch

from homewizard_cli.errors import P1Error
from homewizard_cli.main import main


def test_main_p1_error(capsys):
    with patch("homewizard_cli.main.app") as mock_app:
        mock_app.side_effect = P1Error("device error", code=5)
        import pytest

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 5
    captured = capsys.readouterr()
    assert "device error" in captured.err


def test_main_p1_error_with_details(capsys):
    with patch("homewizard_cli.main.app") as mock_app:
        mock_app.side_effect = P1Error("device error", code=5, details="more info")
        import pytest

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 5
    captured = capsys.readouterr()
    assert "device error" in captured.err
    assert "more info" in captured.err


def test_main_generic_exception(capsys):
    with patch("homewizard_cli.main.app") as mock_app:
        mock_app.side_effect = Exception("unexpected")
        import pytest

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "unexpected" in captured.err


def test_main_system_exit():
    with patch("homewizard_cli.main.app") as mock_app:
        mock_app.side_effect = SystemExit(0)
        import pytest

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
