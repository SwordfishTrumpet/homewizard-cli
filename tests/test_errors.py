from homewizard_cli.errors import (
    CrcMismatchError,
    DeviceNotFoundError,
    HttpError,
    P1Error,
    ParseError,
    TimeoutError,
    UnsupportedError,
    UntilConditionMetError,
    WriteError,
)


def test_p1_error_base():
    err = P1Error("test error", code=5)
    assert err.code == 5
    assert err.message == "test error"
    assert err.to_json() == '{"error":"test error","code":5}'


def test_p1_error_with_details():
    err = P1Error("test error", details="more info")
    assert err.details == "more info"
    assert "more info" in str(err)


def test_device_not_found():
    err = DeviceNotFoundError("not found", "192.168.1.1")
    assert err.code == 2


def test_http_error():
    err = HttpError(404, "http://test")
    assert err.code == 3
    assert "404" in err.message


def test_timeout_error():
    err = TimeoutError(3.0)
    assert err.code == 4


def test_parse_error():
    err = ParseError("bad json")
    assert err.code == 5


def test_crc_mismatch():
    err = CrcMismatchError("1234", "5678")
    assert err.code == 6


def test_write_error():
    err = WriteError("write failed")
    assert err.code == 7


def test_unsupported_error():
    err = UnsupportedError("Device does not support this feature")
    assert err.code == 8
    assert (
        err.to_json() == '{"error":"Device does not support this feature","code":8}'
    )


def test_until_condition():
    err = UntilConditionMetError("condition met")
    assert err.code == 10
