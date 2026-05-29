from homewizard_cli.obis import lookup_obis, list_obis_codes


def test_lookup_known():
    result = lookup_obis("1-0:1.8.1")
    assert result is not None
    assert "import" in result.lower() or "tariff" in result.lower()


def test_lookup_known_power():
    result = lookup_obis("1-0:1.7.0")
    assert result is not None
    assert "power" in result.lower() or "active" in result.lower()


def test_lookup_unknown():
    result = lookup_obis("9-9:9.9.9")
    assert result is None


def test_lookup_gas():
    result = lookup_obis("0-1:24.2.1")
    assert result is not None
    assert "gas" in result.lower()


def test_lookup_invalid():
    assert lookup_obis("") is None
    assert lookup_obis("abc") is None


def test_list_codes():
    codes = list_obis_codes()
    assert len(codes) > 0
    assert any("1.8.1" in key for key in codes)
