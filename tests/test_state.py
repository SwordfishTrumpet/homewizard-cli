"""Tests for homewizard_cli.state."""

from homewizard_cli.state import Aggregator, DeltaTracker


class TestDeltaTracker:
    def test_update_first_call_no_changes(self):
        tracker = DeltaTracker()
        data = {"a": 1, "b": 2.0}
        changes = tracker.update(data)
        assert changes == {}

    def test_update_second_call_change_detected(self):
        tracker = DeltaTracker()
        tracker.update({"a": 1, "b": 2.0})
        changes = tracker.update({"a": 3, "b": 2.0})
        assert changes == {"a": (1.0, 3.0, 2.0)}

    def test_update_third_call_no_change(self):
        tracker = DeltaTracker()
        tracker.update({"a": 1, "b": 2.0})
        tracker.update({"a": 3, "b": 2.0})
        changes = tracker.update({"a": 3, "b": 2.0})
        assert changes == {}

    def test_update_with_explicit_fields(self):
        tracker = DeltaTracker(fields=["a"])
        tracker.update({"a": 1, "b": 2.0})
        changes = tracker.update({"a": 3, "b": 4.0})
        assert changes == {"a": (1.0, 3.0, 2.0)}

    def test_changed_boolean(self):
        tracker = DeltaTracker()
        tracker.update({"a": 1})
        assert tracker.changed({"a": 1}) is False
        assert tracker.changed({"a": 2}) is True
        # changed() does not update state; it still compares against original
        assert tracker.changed({"a": 2}) is True
        tracker.update({"a": 2})
        assert tracker.changed({"a": 2}) is False

    def test_changed_with_explicit_fields(self):
        tracker = DeltaTracker(fields=["b"])
        tracker.update({"a": 1, "b": 2})
        assert tracker.changed({"a": 10, "b": 2}) is False
        assert tracker.changed({"a": 10, "b": 3}) is True

    def test_non_numeric_values_ignored(self):
        tracker = DeltaTracker()
        tracker.update({"a": 1, "s": "hello"})
        changes = tracker.update({"a": 1, "s": "world"})
        assert changes == {}

    def test_float_conversion(self):
        tracker = DeltaTracker()
        tracker.update({"a": 1})
        assert tracker._previous["a"] == 1.0
        tracker.update({"a": 2.5})
        assert tracker._previous["a"] == 2.5


class TestAggregator:
    def test_aggregator_two_samples(self):
        agg = Aggregator(window_size=10)
        result = agg.update({"power": 100})
        assert result == {}
        result = agg.update({"power": 200})
        assert "power_mean" in result
        assert "power_min" in result
        assert "power_max" in result
        assert "power_stddev" in result
        assert result["power_mean"] == 150.0
        assert result["power_min"] == 100.0
        assert result["power_max"] == 200.0

    def test_aggregator_three_samples(self):
        agg = Aggregator(window_size=10)
        agg.update({"power": 100})
        agg.update({"power": 200})
        result = agg.update({"power": 300})
        assert result["power_mean"] == 200.0
        assert result["power_min"] == 100.0
        assert result["power_max"] == 300.0

    def test_aggregator_rolling_window(self):
        agg = Aggregator(window_size=3)
        agg.update({"power": 100})
        agg.update({"power": 200})
        agg.update({"power": 300})
        agg.update({"power": 400})
        result = agg.update({"power": 500})
        # Only last 3 values: 300, 400, 500
        assert result["power_mean"] == 400.0
        assert result["power_min"] == 300.0
        assert result["power_max"] == 500.0

    def test_aggregator_multiple_fields(self):
        agg = Aggregator(window_size=10)
        agg.update({"power": 100, "voltage": 230.0})
        result = agg.update({"power": 200, "voltage": 235.0})
        assert "power_mean" in result
        assert "voltage_mean" in result

    def test_aggregator_empty_dict(self):
        agg = Aggregator()
        assert agg.update({}) == {}

    def test_aggregator_non_numeric_ignored(self):
        agg = Aggregator()
        agg.update({"a": 1, "b": "hello"})
        result = agg.update({"a": 2, "b": "world"})
        assert "a_mean" in result
        assert "b_mean" not in result

    def test_aggregator_field_count(self):
        agg = Aggregator()
        agg.update({"power": 100})
        assert agg.field_count("power") == 1
        agg.update({"power": 200})
        assert agg.field_count("power") == 2
        agg.update({"power": 300})
        assert agg.field_count("power") == 3
        assert agg.field_count("missing") == 0
