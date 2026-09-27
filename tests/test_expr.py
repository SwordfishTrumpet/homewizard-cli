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


def test_is_valid_expression():
    from homewizard_cli.expr import is_valid_expression

    assert is_valid_expression("active_power_w > 10")
    assert is_valid_expression("active_power_w > 10 AND abs(total_gas_m3) < 5")
    assert is_valid_expression("NOT active_power_w > 10")
    assert is_valid_expression("(active_power_w > 10 OR total_gas_m3 < 5)")
    assert not is_valid_expression("garbage expression")
    assert not is_valid_expression("active_power_w >> 10")
    assert not is_valid_expression("")
    assert not is_valid_expression(None)


def test_expr_grouped_parens_and():
    # Regression: both sides parenthesized used to be stripped to garbage.
    expr = "(active_power_w > 0) AND (total_gas_m3 < 10)"
    assert evaluate_until({"active_power_w": 500.0, "total_gas_m3": 5.0}, expr) is True
    assert evaluate_until({"active_power_w": 500.0, "total_gas_m3": 50.0}, expr) is False
    assert evaluate_until({"active_power_w": 0.0, "total_gas_m3": 5.0}, expr) is False


def test_expr_grouped_parens_or():
    expr = "(active_power_w > 0) OR (total_gas_m3 < 10)"
    assert evaluate_until({"active_power_w": 500.0, "total_gas_m3": 50.0}, expr) is True
    assert evaluate_until({"active_power_w": 0.0, "total_gas_m3": 5.0}, expr) is True
    assert evaluate_until({"active_power_w": 0.0, "total_gas_m3": 50.0}, expr) is False


def test_expr_grouped_parens_three_groups():
    expr = "(a > 0) AND (b < 10) AND (c == 3)"
    assert evaluate_until({"a": 1, "b": 5, "c": 3}, expr) is True
    assert evaluate_until({"a": 1, "b": 5, "c": 4}, expr) is False
    assert evaluate_until({"a": 0, "b": 5, "c": 3}, expr) is False


def test_expr_grouped_parens_nested():
    assert evaluate_until({"a": 500.0}, "((a > 0))") is True
    assert evaluate_until({"a": 0.0}, "((a > 0))") is False


def test_is_valid_expression_grouped_parens():
    from homewizard_cli.expr import is_valid_expression

    assert is_valid_expression("(active_power_w > 0) AND (total_gas_m3 < 10)")
    assert is_valid_expression("(active_power_w > 0) OR (total_gas_m3 < 10)")
    assert is_valid_expression(
        "(active_power_w > 0) AND (total_gas_m3 < 10) AND (active_tariff == 1)"
    )
    # Still rejects genuinely malformed input.
    assert not is_valid_expression("(a > 0) AND () ")
    assert not is_valid_expression("(a > 0")
