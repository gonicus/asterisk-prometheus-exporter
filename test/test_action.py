from dataclasses import dataclass
from typing import Dict
import unittest
from action import ActionExecuter, Action


@dataclass
class EventMock():
    name: str
    keys: Dict[str, str]


@dataclass
class ResponseMock():
    status: str
    keys: Dict[str, str]


@dataclass
class FutureResponseMock():
    response: ResponseMock


class ClientMock():
    def __init__(self) -> None:
        self.event_filter = []
        self.event_listener = []
        self.response_timeout = 0
        self.last_action_received = None
        self.send_action_result = None
        self.send_action_sleep = 0

    def add_event_filter(self, event_filter) -> None:
        for filter in event_filter:
            self.event_filter.append(filter)

    def remove_event_filter(self, event_filter) -> None:
        for event in event_filter:
            self.event_filter.remove(event)

    def attach_event_listener(self, event_listener) -> None:
        self.event_listener.append(event_listener)

    def detach_event_listener(self, event_listener) -> None:
        self.event_listener.remove(event_listener)

    def set_response_timeout(self, val) -> None:
        self.response_timeout = val

    def send_action(self, action) -> None:
        self.last_action_received = action
        return self.send_action_result


class FilterMock():
    def __init__(self) -> None:
        self.run_on_scrape_start = False
        self.action_id = ""

    def on_scrape_start(self, action_id: str):
        self.run_on_scrape_start = True
        self.action_id = action_id

    def on_scrape_end(self):
        self.action_id = None


class TestActionExecuter(unittest.TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)

    def setUp(self) -> None:
        self.__client_mock = ClientMock()

        self.__f1 = FilterMock()
        self.__f2 = FilterMock()

        self.__ae = ActionExecuter(self.__client_mock)
        self.__ae._ActionExecuter__action_id = "1"
        self.__ae._ActionExecuter__action = Action("ExpectedEvent",
                                                   [self.__f1,
                                                    self.__f2],
                                                   "ExpectedEndEvent",
                                                   1,
                                                   1,
                                                   1,
                                                   "default",
                                                   "python")

    def test__on_event(self) -> None:
        self.__ae._ActionExecuter__on_event(
            EventMock("TestEvent", {"ActionID": "1"}))
        self.assertFalse(
            self.__ae._ActionExecuter__finished,
            "Expected ActionExecuter to not be finished")

        self.__ae._ActionExecuter__on_event(
            EventMock("ExpectedEndEvent", {"ActionID": "2"}))
        self.assertFalse(
            self.__ae._ActionExecuter__finished,
            "Expected ActionExecuter to not be finished")

        self.__ae._ActionExecuter__on_event(
            EventMock("ExpectedEndEvent", {"ActionID": "1"}))
        self.assertTrue(
            self.__ae._ActionExecuter__finished,
            "Expected ActionExecuter to be finished")

    def test__attach_event_filter(self) -> None:
        self.__ae._ActionExecuter__attach_event_filter()

        self.assertEqual(
            self.__f1.action_id,
            "1",
            "Expected action id '1' to be set in filter 1")
        self.assertEqual(
            self.__f2.action_id,
            "1",
            "Expected action id '1' to be set in filter 2")

        self.assertEqual(
            self.__client_mock.event_filter[0],
            self.__f1,
            "Expected first EventFilter to be filter 1")
        self.assertEqual(
            self.__client_mock.event_filter[1],
            self.__f2,
            "Expected second EventFilter to be filter 2")

        self.assertEqual(
            self.__client_mock.event_listener[0],
            self.__ae._ActionExecuter__on_event,
            "Expected __on_event function of ActionExecutor to be attached to client")

    def test__send_action(self) -> None:
        # Test general AMI error
        self.__client_mock.send_action_result = FutureResponseMock(
            ResponseMock("error", {"Message": "Some error"}))
        result = self.__ae._ActionExecuter__send_action()
        self.assertFalse(result, "Expected result to be false")

        # Test timeout
        self.__client_mock.send_action_result = FutureResponseMock(None)
        result = self.__ae._ActionExecuter__send_action()
        self.assertFalse(result, "Expected result to be false")

        # Test successful action
        self.__client_mock.send_action_result = FutureResponseMock(
            ResponseMock("Success", {"Message": "Success"}))
        result = self.__ae._ActionExecuter__send_action()
        self.assertTrue(result, "Expected result to be true")

        self.assertEqual(
            self.__client_mock.last_action_received.keys["Priority"], "1")
        self.assertEqual(
            self.__client_mock.last_action_received.keys["Context"],
            "default")
        self.assertEqual(
            self.__client_mock.last_action_received.keys["CallerID"],
            "python")
        self.assertEqual(
            self.__client_mock.last_action_received.keys["ActionID"], "1")

    def test__collect_event(self) -> None:
        e1 = EventMock("Event1", {})
        e2 = EventMock("Event2", {})
        e3 = EventMock("ExpectedEndEvent", {"ActionID": "1"})

        self.__ae._ActionExecuter__on_event(e1)
        self.__ae._ActionExecuter__on_event(e2)
        self.__ae._ActionExecuter__on_event(e3)

        self.assertTrue(
            self.__ae._ActionExecuter__collect_events(),
            "Expected action executer to already finished collecting every event")

    def test__detach_event_filter(self) -> None:
        self.__client_mock.add_event_filter([self.__f1, self.__f2])
        self.__client_mock.attach_event_listener(
            self.__ae._ActionExecuter__on_event)

        self.__ae._ActionExecuter__detach_event_filter()

        self.assertEqual(len(self.__client_mock.event_filter), 0,
                         "Expected no event filter to be attached to the client.")

        self.assertEqual(len(self.__client_mock.event_listener), 0,
                         "Expected no event listener to be attached to the client.")

        self.assertFalse(self.__ae._ActionExecuter__finished,
                         "Expected action executer to not be finished anymore")
