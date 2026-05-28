"""Expression evaluator for --until conditions."""

import operator
import re
from typing import Any

_EXPR_PATTERN = re.compile(
    r"^(?:abs\()?\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\)?\s*"
    r"(>=|<=|==|!=|>|<)\s*"
    r"(-?\d+(?:\.\d+)?)\s*$"
)

_OPS = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}


def _resolve(data: dict, key: str) -> Any:
    """Resolve dotted key path in data dict."""
    parts = key.split(".")
    value = data
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def evaluate_until(data: dict, expression: str) -> bool:
    """Evaluate a simple --until expression against data."""
    if not expression or not expression.strip():
        return False

    expression = expression.strip()
    use_abs = False
    if expression.startswith("abs("):
        use_abs = True
        expression = expression[4:]

    m = _EXPR_PATTERN.match(expression)
    if not m:
        return False

    field = m.group(1)
    op_str = m.group(2)
    rhs = float(m.group(3))

    value = _resolve(data, field)
    if value is None:
        return False

    try:
        val = float(value)
    except (ValueError, TypeError):
        return False

    if use_abs:
        val = abs(val)

    op_func = _OPS.get(op_str)
    if op_func is None:
        return False

    return op_func(val, rhs)
