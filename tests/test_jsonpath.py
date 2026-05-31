"""Tests for homewizard_cli.jsonpath."""

from homewizard_cli.jsonpath import query_jsonpath


class TestQueryJsonpath:
    def test_root_dollar_returns_data(self):
        data = {"a": 1, "b": 2}
        assert query_jsonpath(data, "$") == data

    def test_empty_expression_returns_none(self):
        data = {"a": 1}
        assert query_jsonpath(data, "") is None

    def test_simple_field(self):
        data = {"a": 1, "b": 2}
        assert query_jsonpath(data, "$.a") == 1
        assert query_jsonpath(data, "$.b") == 2

    def test_missing_field_returns_none(self):
        data = {"a": 1}
        assert query_jsonpath(data, "$.missing") is None

    def test_nested_field(self):
        data = {"a": {"b": {"c": 42}}}
        assert query_jsonpath(data, "$.a.b.c") == 42

    def test_nested_missing_returns_none(self):
        data = {"a": {"b": 2}}
        assert query_jsonpath(data, "$.a.b.c") is None
        assert query_jsonpath(data, "$.a.x") is None

    def test_array_index(self):
        data = {"items": [10, 20, 30]}
        assert query_jsonpath(data, "$.items[0]") == 10
        assert query_jsonpath(data, "$.items[1]") == 20
        assert query_jsonpath(data, "$.items[2]") == 30

    def test_array_index_out_of_bounds(self):
        data = {"items": [10, 20]}
        assert query_jsonpath(data, "$.items[5]") is None
        assert query_jsonpath(data, "$.items[-1]") is None

    def test_array_index_on_non_list(self):
        data = {"items": "not a list"}
        assert query_jsonpath(data, "$.items[0]") is None

    def test_array_wildcard(self):
        data = {"items": [10, 20, 30]}
        result = query_jsonpath(data, "$.items[*]")
        assert result == [10, 20, 30]

    def test_array_wildcard_nested_field(self):
        data = {"items": [{"a": 1}, {"a": 2}, {"a": 3}]}
        result = query_jsonpath(data, "$.items[*].a")
        assert result == [1, 2, 3]

    def test_array_wildcard_on_non_list(self):
        data = {"items": "not a list"}
        assert query_jsonpath(data, "$.items[*]") is None

    def test_recursive_search(self):
        data = {"a": {"b": 1}, "c": {"b": 2, "d": {"b": 3}}}
        result = query_jsonpath(data, "$..b")
        assert sorted(result) == [1, 2, 3]

    def test_recursive_search_array(self):
        data = {"items": [{"x": 1}, {"x": 2}], "x": 3}
        result = query_jsonpath(data, "$..x")
        assert sorted(result) == [1, 2, 3]

    def test_recursive_search_no_matches(self):
        data = {"a": {"b": 1}}
        result = query_jsonpath(data, "$..z")
        assert result == []

    def test_invalid_prefix(self):
        data = {"a": 1}
        assert query_jsonpath(data, "a.b") is None
        assert query_jsonpath(data, "@.a") is None

    def test_bare_field_name(self):
        data = {"a": 1, "b": 2}
        assert query_jsonpath(data, "a") == 1
        assert query_jsonpath(data, "b") == 2

    def test_bare_field_name_missing(self):
        data = {"a": 1}
        assert query_jsonpath(data, "missing") is None

    def test_boolean_expression(self):
        data = {"active_power_w": 456}
        assert query_jsonpath(data, "active_power_w > 100") is True
        assert query_jsonpath(data, "active_power_w > 500") is False

    def test_boolean_expression_abs(self):
        data = {"active_power_w": -456}
        assert query_jsonpath(data, "abs(active_power_w) > 100") is True

    def test_boolean_expression_and(self):
        data = {"a": 10, "b": 5}
        assert query_jsonpath(data, "a > 5 AND b < 10") is True
        assert query_jsonpath(data, "a > 15 AND b < 10") is False

    def test_nested_array_index_then_field(self):
        data = {"items": [{"a": [10, 20]}, {"a": [30, 40]}]}
        result = query_jsonpath(data, "$.items[0].a[1]")
        assert result == 20

    def test_bracket_then_dot(self):
        data = {"items": [{"a": 1}, {"a": 2}]}
        result = query_jsonpath(data, "$.items[1].a")
        assert result == 2

    def test_array_expression_invalid_value(self):
        data = {"items": [10, 20]}
        assert query_jsonpath(data, "$.items[abc]") is None

    def test_navigate_dict_with_string_not_dict(self):
        data = {"a": "string"}
        assert query_jsonpath(data, "$.a.b") is None

    def test_navigate_non_dict_top_level(self):
        data = [1, 2, 3]
        assert query_jsonpath(data, "$.a") is None

    def test_navigate_with_empty_remaining_after_bracket(self):
        data = {"items": [10, 20]}
        assert query_jsonpath(data, "$.items[0]") == 10

    def test_array_with_empty_field(self):
        data = [10, 20, 30]
        assert query_jsonpath(data, "$[0]") == 10
        assert query_jsonpath(data, "$[1]") == 20

    def test_array_wildcard_with_empty_field(self):
        data = [10, 20, 30]
        result = query_jsonpath(data, "$[*]")
        assert result == [10, 20, 30]

    def test_deep_nested_mixed(self):
        data = {"a": [{"b": {"c": [1, 2, {"d": 42}]}}]}
        assert query_jsonpath(data, "$.a[0].b.c[2].d") == 42

    def test_query_jsonpath_on_scalar_data(self):
        assert query_jsonpath(42, "$") == 42
