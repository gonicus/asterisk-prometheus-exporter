import unittest
from dataclasses import dataclass
from typing import Dict, Any, Sequence, List
from metric_values import MetricValueCounter, MetricValueGauge
from prometheus_client import Gauge


@dataclass
class EventMock:
    name: str
    keys: Dict[str, str]


class CounterMock():
    def __init__(self, label_names: List[str]) -> None:
        self.last_inc = None
        self.child_counters: Dict[Sequence[str], CounterMock] = {}
        self.__label_names: List[str] = label_names

    def inc(self, val):
        self.last_inc = val

    def labels(self, **labelkwargs: Any):
        label_values = tuple(str(labelkwargs[label]) for label in self.__label_names)

        if label_values in self.child_counters:
            return self.child_counters[label_values]

        child = CounterMock([])
        self.child_counters[label_values] = child
        return child


class GaugeMock():
    def __init__(self, label_names: List[str]) -> None:
        self.last_inc = None
        self.last_set = None
        self.child_gauges: Dict[Sequence[str], GaugeMock] = {}
        self.__label_names: List[str] = label_names

    def set(self, val):
        self.last_set = val

    def inc(self, val):
        self.last_inc = val

    def labels(self, **labelkwargs: Any):
        label_values = tuple(str(labelkwargs[label]) for label in self.__label_names)

        if label_values in self.child_gauges:
            return self.child_gauges[label_values]

        child = GaugeMock([])
        self.child_gauges[label_values] = child
        return child


class TestMetricValueCounter(unittest.TestCase):
    def test_process_event(self):
        # Test without labels
        event = EventMock("SomeEvent", {"key_1": "2", "key_2": "invalid"})
        metric_value = MetricValueCounter(
            "test__convert_value_metric", "metric_description", {}, "1")
        counter = CounterMock({})
        metric_value._MetricValueCounter__counter = counter

        metric_value.process_event(event)
        self.assertEqual(
            counter.last_inc,
            1,
            "Expected counter to be increment by 1")

        metric_value._MetricValueCounter__increment_value = "$key_1"
        metric_value.process_event(event)
        self.assertEqual(
            counter.last_inc,
            2,
            "Expected counter to be increment by 2")

        metric_value._MetricValueCounter__increment_value = "$key_2"
        metric_value.process_event(event)
        self.assertEqual(
            counter.last_inc,
            0,
            "Expected counter to be increment by 0")

        metric_value._MetricValueCounter__increment_value = "invalid_number"
        metric_value.process_event(event)
        self.assertEqual(
            counter.last_inc,
            0,
            "Expected counter to be increment by 0")

        # Test with labels
        event = EventMock(
            "SomeEvent", {
                "key_1": "label_val_1", "key_2": "label_val_2", "key_3": "2"})
        counter = CounterMock(["label_1", "label_2"])
        metric_value = MetricValueCounter(
            "test__convert_value_metric_labels", "metric description", {
                "label_1": "$key_1", "label_2": "$key_2"}, "1")
        metric_value._MetricValueCounter__counter = counter
        labels = tuple(["label_val_1", "label_val_2"])

        metric_value.process_event(event)
        self.assertEqual(
            counter.child_counters[labels].last_inc,
            1,
            f"Expected child counter with labels {labels} to be incremented by 1")

        metric_value._MetricValueCounter__increment_value = "$key_3"
        metric_value.process_event(event)
        self.assertEqual(
            counter.child_counters[labels].last_inc,
            2,
            f"Expected child counter with labels {labels} to be incremented by 2")

        metric_value._MetricValueCounter__increment_value = "invalid"
        metric_value.process_event(event)
        self.assertEqual(
            counter.child_counters[labels].last_inc,
            0,
            f"Expected child counter with labels {labels} to be incremented by 0")

        metric_value._MetricValueCounter__counter = None
        self.assertRaisesRegex(
            Exception,
            "Metric is not initialized",
            metric_value.process_event,
            event)


class TestMetricValueGauge(unittest.TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)

        self.__updated_gauge: bool = False
        self.__set_on_scrape_start_values: bool = False

    def __update_gauge_mock(self):
        self.__updated_gauge = True

    def __is_gauge_updated(self) -> bool:
        temp = self.__updated_gauge
        self.__updated_gauge = False
        return temp

    def __set_on_scrape_start_mock(self):
        self.__set_on_scrape_start_values = True

    def __is_set_on_scrape_start_values(self) -> bool:
        temp = self.__set_on_scrape_start_values
        self.__set_on_scrape_start_values = False
        return temp

    def test_on_scrape_end(self):
        metric_value = MetricValueGauge(
            "test_metric_gauge", "metric_description", {}, None, "1", None)
        metric_value._MetricValueGauge__set_on_scrape_start_value = self.__set_on_scrape_start_mock

        metric_value.on_scrape_start()
        self.assertFalse(
            self.__is_set_on_scrape_start_values(),
            "Expected values to not be reset")
        self.assertFalse(
            metric_value._MetricValueGauge__scrape_metric,
            "Expected scrape_metric to not be updated")

        gauge = GaugeMock([])
        metric_value._MetricValueGauge__gauge = gauge

        metric_value.on_scrape_start()
        self.assertTrue(
            self.__is_set_on_scrape_start_values(),
            "Expected values to be reset")
        self.assertTrue(
            metric_value._MetricValueGauge__scrape_metric,
            "Expected scrape_metric to be updated to true")

    def test_on_scrape_start(self):
        metric_value = MetricValueGauge(
            "test_metric_gauge", "metric_description", {}, None, "1", None)
        metric_value._MetricValueGauge__update_gauge = self.__update_gauge_mock

        self.assertTrue(
            self.__is_gauge_updated,
            "Expected gauge to be updated")

    def test_process_event(self):
        event = EventMock("SomeEvent", {"key_1": "2", "key_2": "invalid"})

        # Test without labels and increment values
        metric_value = MetricValueGauge(
            "test_metric_gauge", "metric_description", {}, None, "1", None)
        metric_value._MetricValueGauge__update_gauge = self.__update_gauge_mock

        metric_value.process_event(event)
        self.assertEqual(metric_value._MetricValueGauge__value,
                         1, "Expected gauge to be increment by 1")

        metric_value._MetricValueGauge__increment_value = "$key_1"
        metric_value.process_event(event)
        self.assertEqual(metric_value._MetricValueGauge__value,
                         3, "Expected gauge to be increment by 2")

        metric_value._MetricValueGauge__increment_value = "invalid_number"
        metric_value.process_event(event)
        self.assertEqual(metric_value._MetricValueGauge__value,
                         3, "Expected gauge to be increment by 0")

        # Test without labels and set values
        metric_value = MetricValueGauge(
            "test_metric_gauge_set_values",
            "metric_description",
            {},
            "1",
            None,
            None)
        metric_value._MetricValueGauge__update_gauge = self.__update_gauge_mock

        metric_value.process_event(event)
        self.assertEqual(metric_value._MetricValueGauge__value,
                         1, "Expected gauge to be set to 1")

        metric_value._MetricValueGauge__set_value = "$key_1"
        metric_value.process_event(event)
        self.assertEqual(metric_value._MetricValueGauge__value,
                         2, "Expected gauge to be set to 2")

        metric_value._MetricValueGauge__set_value = "invalid_number"
        metric_value.process_event(event)
        self.assertEqual(metric_value._MetricValueGauge__value,
                         0, "Expected gauge to be set to 0")

        # Test with labels and increment values
        event = EventMock(
            "SomeEvent", {
                "key_1": "label_val_1", "key_2": "label_val_2", "key_3": "2"})
        labels = tuple(["label_val_1", "label_val_2"])
        metric_value = MetricValueGauge(
            "test_metric_gauge_labels", "metric description", {
                "label_1": "$key_1", "label_2": "$key_2"}, None, "1", None)
        metric_value._MetricValueGauge__update_gauge = self.__update_gauge_mock

        metric_value.process_event(event)
        self.assertEqual(
            metric_value._MetricValueGauge__label_values[labels],
            1,
            f"Expected value with labels {labels} to be incremented by 1")

        metric_value._MetricValueGauge__increment_value = "$key_3"
        metric_value.process_event(event)
        self.assertEqual(
            metric_value._MetricValueGauge__label_values[labels],
            3,
            f"Expected value with labels {labels} to be incremented by 2")

        metric_value._MetricValueGauge__increment_value = "invalid_value"
        metric_value.process_event(event)
        self.assertEqual(
            metric_value._MetricValueGauge__label_values[labels],
            3,
            f"Expected value with labels {labels} to be incremented by 0")

        # Test with labels and set values
        metric_value = MetricValueGauge(
            "test_metric_gauge_labels_set_value", "metric description", {
                "label_1": "$key_1", "label_2": "$key_2"}, "1", None, None)
        metric_value._MetricValueGauge__update_gauge = self.__update_gauge_mock

        metric_value.process_event(event)
        self.assertEqual(
            metric_value._MetricValueGauge__label_values[labels],
            1,
            f"Expected value with labels {labels} to be set to 1")

        metric_value._MetricValueGauge__set_value = "$key_3"
        metric_value.process_event(event)
        self.assertEqual(
            metric_value._MetricValueGauge__label_values[labels],
            2,
            f"Expected value with labels {labels} to be set to 2")

        metric_value._MetricValueGauge__set_value = "invalid_value"
        metric_value.process_event(event)
        self.assertEqual(
            metric_value._MetricValueGauge__label_values[labels],
            0,
            f"Expected value with labels {labels} to be set to 0")

        self.assertTrue(
            self.__is_gauge_updated(),
            "Expected gauge to be updated")
        metric_value._MetricValueGauge__scrape_metric = True
        metric_value.process_event(event)
        self.assertFalse(
            self.__is_gauge_updated(),
            "Expected gauge to not be updated")

    def test_init(self):
        metric_value = MetricValueGauge(
            "test__init_metric_gauge",
            "metric_description",
            {},
            "1",
            None,
            None)
        metric_value.init()
        self.assertTrue(
            isinstance(
                metric_value._MetricValueGauge__gauge,
                Gauge),
            "Expected gauge to be created")
