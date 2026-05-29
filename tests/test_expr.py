from homewizard_cli.expr import evaluate_until


def test_expr_gt():
    assert evaluate_until({"a": 100}, "a > 50") is True
    assert evaluate_until({"a": 30}, "a > 50") is False


def test_expr_lt():
    assert evaluate_until({"a": 30}, "a < 50") is True
    assert evaluate_until({"a": 100}, "a < 50") is False


def test_expr_eq():
    assert evaluate_until({"a": 50}, "a == 50") is True
    assert evaluate_until({"a": 30}, "a == 50") is False


def test_expr_gte():
    assert evaluate_until({"a": 50}, "a >= 50") is True
    assert evaluate_until({"a": 49}, "a >= 50") is False


def test_expr_lte():
    assert evaluate_until({"a": 50}, "a <= 50") is True
    assert evaluate_until({"a": 51}, "a <= 50") is False


def test_expr_abs():
    assert evaluate_until({"a": -100}, "abs(a) > 50") is True
    assert evaluate_until({"a": -30}, "abs(a) > 50") is False


def test_expr_nested_key():
    assert evaluate_until({"x": {"y": 100}}, "x.y > 50") is True
    assert evaluate_until({"x": {"y": 30}}, "x.y > 50") is False


def test_expr_float():
    assert evaluate_until({"a": 50.5}, "a > 50") is True
    assert evaluate_until({"a": 49.9}, "a > 50") is False


def test_expr_field_not_found():
    assert evaluate_until({"a": 100}, "b > 50") is False


def test_expr_ne():
    assert evaluate_until({"a": 30}, "a != 50") is True
    assert evaluate_until({"a": 50}, "a != 50") is False


def test_expr_negative_rhs():
    assert evaluate_until({"a": -10}, "a > -50") is True
    assert evaluate_until({"a": -100}, "a > -50") is False


def test_expr_invalid():
    assert evaluate_until({"a": 100}, "") is False
    assert evaluate_until({"a": 100}, "a > ") is False
