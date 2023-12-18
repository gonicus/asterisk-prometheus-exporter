import unittest
from dataclasses import dataclass
from typing import Dict, List
from event_listener import EventListener
from time import time


class EventFilterMock():
    def __init__(self) -> None:
        self.last_event_processed = None

    def process_event(self, event):
        self.last_event_processed = event

    def get_event_names(self) -> List[str]:
        return []


@dataclass
class EventMock():
    name: str
    keys: Dict[str, str]


class TestEventListener(unittest.TestCase):
    def setUp(self) -> None:
        self.__ef1 = EventFilterMock()
        self.__ef2 = EventFilterMock()

        self.__event_listener = EventListener()
        self.__event_listener._EventListener__event_filter = [
            self.__ef1, self.__ef2]

    def test_add_event_filter(self):
        self.__event_listener._EventListener__event_filter.clear()
        self.__event_listener.add_event_filter(self.__ef1)
        self.__event_listener.add_event_filter(self.__ef2)
        self.assertEqual(
            self.__event_listener._EventListener__event_filter[0],
            self.__ef1,
            "Expected filter 1 to be attached to the event listener")
        self.assertEqual(
            self.__event_listener._EventListener__event_filter[1],
            self.__ef2,
            "Expected filter 2 to be attached to the event listener")

    def test_remove_event_filter(self):
        self.__event_listener.remove_event_filter(self.__ef1)
        self.assertEqual(len(self.__event_listener._EventListener__event_filter),
                         1,
                         "Expected only one filter to be attached to the event listener")
        self.assertEqual(
            self.__event_listener._EventListener__event_filter[0],
            self.__ef2,
            "Expected filter 2 to still be attached to the event listener")

    def test_get_time_of_last_event(self):
        self.__event_listener._EventListener__last_event_received = 55475484
        self.assertEqual(
            self.__event_listener.get_time_of_last_event(),
            55475484)

    def test_update_time_of_last_event(self):
        self.__event_listener.update_time_of_last_event()
        self.assertAlmostEqual(
            time(),
            self.__event_listener._EventListener__last_event_received,
            msg="Expected time to be updated to current time",
            delta=0.0001)

    def test_rest(self):
        self.__event_listener.reset()
        self.assertEqual(len(self.__event_listener._EventListener__event_filter),
                         0,
                         "Expected to more event filter to be attached to the event listener")

    def test_on_event(self):
        event = EventMock("Event", {"ActionID", "1"})
        self.__event_listener.on_event(event)
        self.assertAlmostEqual(
            time(),
            self.__event_listener._EventListener__last_event_received,
            msg="Expected time to be updated to current time",
            delta=0.0001)
        self.assertEqual(self.__ef1.last_event_processed,
                         event,
                         "Expected event to be processed by filter 1")
        self.assertEqual(self.__ef2.last_event_processed,
                         event,
                         "Expected event to be processed by filter 2")
