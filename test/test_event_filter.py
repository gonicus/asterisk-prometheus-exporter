import unittest
from typing import Dict
from dataclasses import dataclass
from event_filter import EventFilter


@dataclass
class EventMock():
    name: str
    keys: Dict[str, str]


class MetricValueMock():
    def __init__(self) -> None:
        self.exec_on_scrape_start = False
        self.exec_on_scrape_end = False
        self.last_event_processed = None

    def on_scrape_start(self):
        self.exec_on_scrape_start = True

    def on_scrape_end(self):
        self.exec_on_scrape_end = True

    def process_event(self, event):
        self.last_event_processed = event


class TestEventFilter(unittest.TestCase):
    def setUp(self) -> None:
        self.__mv1 = MetricValueMock()
        self.__mv2 = MetricValueMock()

        self.__event_filter = EventFilter(
            ["Event1", "Event2"], [self.__mv1, self.__mv2])

    def test_on_scrape_start(self):
        self.__event_filter.on_scrape_start("1")
        self.assertEqual(self.__event_filter._EventFilter__action_id,
                         "1",
                         "Expected action id to be set in event filter")
        for metric in self.__event_filter._EventFilter__metric_values:
            self.assertTrue(metric.exec_on_scrape_start,
                            "Expected on_scrape_start to be executed in metric")

    def test_on_scrape_end(self):
        self.__event_filter.on_scrape_end()
        for metric in self.__event_filter._EventFilter__metric_values:
            self.assertTrue(metric.exec_on_scrape_end,
                            "Expected on_scrape_start to be executed in metric")

    def test_process_event(self):
        self.__event_filter._EventFilter__action_id = "1"
        ev = EventMock("SomeEvent", {"ActionID": "1"})
        self.__event_filter.process_event(ev)
        self.assertEqual(
            self.__mv1.last_event_processed,
            None,
            "Expected event to not be processed by metric 1.")
        self.assertEqual(
            self.__mv2.last_event_processed,
            None,
            "Expected event to not be processed by metric 2.")

        ev = EventMock("Event1", {"ActionID": "2"})
        self.__event_filter.process_event(ev)
        self.assertEqual(
            self.__mv1.last_event_processed,
            None,
            "Expected event to not be processed by metric 1.")
        self.assertEqual(
            self.__mv2.last_event_processed,
            None,
            "Expected event to not be processed by metric 2.")

        ev = EventMock("Event1", {"ActionID": "1"})
        self.__event_filter.process_event(ev)
        self.assertEqual(self.__mv1.last_event_processed, ev,
                         "Expected event to be processed by metric 1.")
        self.assertEqual(self.__mv2.last_event_processed, ev,
                         "Expected event to be processed by metric 2.")

        ev = EventMock("Event2", {"ActionID": "1"})
        self.__event_filter.process_event(ev)
        self.assertEqual(self.__mv1.last_event_processed, ev,
                         "Expected event to be processed by metric 1.")
        self.assertEqual(self.__mv2.last_event_processed, ev,
                         "Expected event to be processed by metric 2.")
