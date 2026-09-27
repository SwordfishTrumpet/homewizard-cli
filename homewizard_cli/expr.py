"""Expression evaluator for --until conditions."""

import operator
import re
from typing import Any

_SIMPLE_PATTERN = re.compile(
    r"^(?:abs\()?\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\)?\s*"
    r"(>=|<=|==|!=|>|<)\s*"
    r"(-?\d+(?:\.\d+)?)\s*$"
)

_OPS: dict[str, Any] = {
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}


def _resolve(data: dict, key: str) -> Any:
    parts = key.split(".")
    value: Any = data
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def _evaluate_simple(data: dict, expression: str) -> bool:
    """Evaluate a simple comparison expression."""
    if not expression or not expression.strip():
        return False

    expression = expression.strip()
    use_abs = False
    if expression.startswith("abs("):
        use_abs = True
        expression = expression[4:]

    m = _SIMPLE_PATTERN.match(expression)
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


def _split_by_operators(expression: str, operators: list[str]) -> list[str]:
    """Split expression by top-level operators (not inside parentheses)."""
    parts = []
    current = []
    paren_depth = 0
    i = 0
    n = len(expression)
    while i < n:
        if expression[i] == "(":
            paren_depth += 1
            current.append(expression[i])
            i += 1
            continue
        if expression[i] == ")":
            if paren_depth > 0:
                paren_depth -= 1
            current.append(expression[i])
            i += 1
            continue
        if paren_depth == 0:
            for op in operators:
                if expression.startswith(op, i):
                    end = i + len(op)
                    if end == n or expression[end].isspace() or expression[end] in "()":
                        parts.append("".join(current).strip())
                        current = []
                        i = end
                        break
            else:
                current.append(expression[i])
                i += 1
        else:
            current.append(expression[i])
            i += 1
    parts.append("".join(current).strip())
    return parts


def evaluate_until(data: dict, expression: str) -> bool:
    if not expression or not expression.strip():
        return False

    expression = expression.strip()

    # Strip outer parentheses that wrap the entire expression
    while (
        expression.startswith("(") and expression.endswith(")") and len(expression) > 1
    ):
        inner = expression[1:-1].strip()
        if inner:
            expression = inner
        else:
            break

    # Split by OR (lowest precedence)
    or_parts = _split_by_operators(expression, ["OR"])
    if len(or_parts) > 1:
        if any(not part for part in or_parts):
            return False
        return any(evaluate_until(data, part) for part in or_parts)

    # Split by AND
    and_parts = _split_by_operators(expression, ["AND"])
    if len(and_parts) > 1:
        if any(not part for part in and_parts):
            return False
        return all(evaluate_until(data, part) for part in and_parts)

    # Handle NOT
    if expression.startswith("NOT") and (
        len(expression) == 3 or not expression[3].isalnum()
    ):
        inner = expression[3:].strip()
        if inner:
            return not evaluate_until(data, inner)

    # Single expression
    return _evaluate_simple(data, expression)


def _is_valid_simple(expression: str) -> bool:
    """Parse-only check for a simple comparison (no data needed)."""
    if not expression or not expression.strip():
        return False
    e = expression.strip()
    if e.startswith("abs("):
        e = e[4:]
    return bool(_SIMPLE_PATTERN.match(e))


def is_valid_expression(expression: str | None) -> bool:
    """Validate a composite --until expression without data (LOW-2).

    Returns False for unparsable expressions so watch commands can fail
    fast instead of running forever with a condition that never fires.
    """
    if not expression or not expression.strip():
        return False
    expr = expression.strip()
    while expr.startswith("(") and expr.endswith(")") and len(expr) > 1:
        inner = expr[1:-1].strip()
        if inner:
            expr = inner
        else:
            break
    or_parts = _split_by_operators(expr, ["OR"])
    if len(or_parts) > 1:
        return all(is_valid_expression(p) for p in or_parts)
    and_parts = _split_by_operators(expr, ["AND"])
    if len(and_parts) > 1:
        return all(is_valid_expression(p) for p in and_parts)
    if expr.startswith("NOT") and (len(expr) == 3 or not expr[3].isalnum()):
        return is_valid_expression(expr[3:].strip())
    return _is_valid_simple(expr)
