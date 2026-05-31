from typing import Any


def query_jsonpath(data: Any, expression: str) -> Any:
    if not expression:
        return None
    expression = expression.strip()
    if expression.startswith("$"):
        path = expression[1:]
        if not path:
            return data
        if path.startswith(".."):
            field = path[2:]
            results: list[Any] = []
            _recursive_find(data, field, results)
            return results
        if path.startswith("."):
            path = path[1:]
        return _navigate(data, path)
    # Support bare field names (e.g. "active_power_w")
    if any(op in expression for op in (">", "<", "==", "!=")):
        from .expr import evaluate_until

        return evaluate_until(data, expression)
    if isinstance(data, dict):
        return data.get(expression)
    return None


def _navigate(data: Any, path: str) -> Any:
    if not path:
        return data
    bracket_idx = path.find("[")
    dot_idx = path.find(".")
    if bracket_idx == -1 and dot_idx == -1:
        if isinstance(data, dict):
            return data.get(path)
        return None
    if bracket_idx != -1 and (dot_idx == -1 or bracket_idx < dot_idx):
        field = path[:bracket_idx]
        rest = path[bracket_idx:]
        close_bracket = rest.find("]")
        array_expr = rest[1:close_bracket]
        remaining = rest[close_bracket + 1 :]
        if remaining.startswith("."):
            remaining = remaining[1:]
        val = (data.get(field) if isinstance(data, dict) else None) if field else data
        if val is None:
            return None
        if array_expr == "*":
            if isinstance(val, list):
                return [
                    _navigate(item, remaining) if remaining else item for item in val
                ]
            return None
        try:
            idx = int(array_expr)
        except ValueError:
            return None
        if isinstance(val, list) and 0 <= idx < len(val):
            return _navigate(val[idx], remaining) if remaining else val[idx]
        return None
    if dot_idx != -1:
        field = path[:dot_idx]
        remaining = path[dot_idx + 1 :]
        if isinstance(data, dict):
            val = data.get(field)
            if val is None:
                return None
            return _navigate(val, remaining)
        return None
    return None


def _recursive_find(data: Any, field: str, results: list[Any]) -> None:
    if isinstance(data, dict):
        for key, val in data.items():
            if key == field:
                results.append(val)
            _recursive_find(val, field, results)
    elif isinstance(data, list):
        for item in data:
            _recursive_find(item, field, results)
