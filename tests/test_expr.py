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


def test_expr_and():
    assert evaluate_until({"a": 100, "b": 3}, "a > 10 AND b < 5") is True
    assert evaluate_until({"a": 100, "b": 10}, "a > 10 AND b < 5") is False
    assert evaluate_until({"a": 5, "b": 3}, "a > 10 AND b < 5") is False


def test_expr_or():
    assert evaluate_until({"a": 100, "b": 10}, "a > 10 OR b < 5") is True
    assert evaluate_until({"a": 5, "b": 3}, "a > 10 OR b < 5") is True
    assert evaluate_until({"a": 5, "b": 10}, "a > 10 OR b < 5") is False


def test_expr_not():
    assert evaluate_until({"a": 5}, "NOT a > 10") is True
    assert evaluate_until({"a": 100}, "NOT a > 10") is False


def test_expr_abs_and():
    assert evaluate_until({"a": -100, "b": 3}, "abs(a) > 10 AND b < 5") is True
    assert evaluate_until({"a": -100, "b": 10}, "abs(a) > 10 AND b < 5") is False


def test_expr_nested_precedence():
    # (a > 10 OR b < 5) AND c > 1
    assert (
        evaluate_until({"a": 5, "b": 3, "c": 10}, "(a > 10 OR b < 5) AND c > 1") is True
    )
    assert (
        evaluate_until({"a": 5, "b": 10, "c": 10}, "(a > 10 OR b < 5) AND c > 1")
        is False
    )
    # a > 10 AND (b < 5 OR c > 1)
    assert (
        evaluate_until({"a": 100, "b": 10, "c": 10}, "a > 10 AND (b < 5 OR c > 1)")
        is True
    )
    assert (
        evaluate_until({"a": 100, "b": 10, "c": 0}, "a > 10 AND (b < 5 OR c > 1)")
        is False
    )


def test_expr_invalid_composite():
    assert evaluate_until({"a": 100}, "a > 10 AND") is False
    assert evaluate_until({"a": 100}, "AND a > 10") is False
    assert evaluate_until({"a": 100}, "a > 10 OR") is False
    assert evaluate_until({"a": 100}, "OR a > 10") is False


def test_expr_and_precedence_over_or():
    # a > 10 OR b < 5 AND c > 1
    # should be a > 10 OR (b < 5 AND c > 1)
    assert (
        evaluate_until({"a": 100, "b": 10, "c": 0}, "a > 10 OR b < 5 AND c > 1") is True
    )
    assert (
        evaluate_until({"a": 5, "b": 3, "c": 10}, "a > 10 OR b < 5 AND c > 1") is True
    )
    assert (
        evaluate_until({"a": 5, "b": 10, "c": 0}, "a > 10 OR b < 5 AND c > 1") is False
    )


def test_expr_not_with_and():
    # NOT a > 10 AND b < 5
    # should be (NOT a > 10) AND b < 5
    assert evaluate_until({"a": 5, "b": 3}, "NOT a > 10 AND b < 5") is True
    assert evaluate_until({"a": 100, "b": 3}, "NOT a > 10 AND b < 5") is False


def test_expr_not_with_or():
    assert evaluate_until({"a": 5, "b": 10}, "NOT a > 10 OR b < 5") is True
    assert evaluate_until({"a": 100, "b": 10}, "NOT a > 10 OR b < 5") is False
