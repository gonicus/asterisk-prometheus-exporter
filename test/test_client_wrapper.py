from dataclasses import dataclass
from typing import Dict
import unittest
from client_wrapper import ClientWrapper


@dataclass
class EventMock():
    name: str
    keys: Dict[str, str]


@dataclass
class ResponseMock():
    status: str
    error: bool

    def is_error(self) -> bool:
        return self.error


@dataclass
class FutureResponseMock():
    response: ResponseMock


class EventListenerMock():
    def __init__(self) -> None:
        self.updated_time = False
        self.event_filter = []

    def update_time_of_last_event(self):
        self.updated_time = True

    def on_event(self):
        ...

    def add_event_filter(self, filter):
        self.event_filter.append(filter)

    def remove_event_filter(self, filter):
        self.event_filter.remove(filter)


class EventFilterMock():
    ...


class SocketMock():
    def __init__(self) -> None:
        self.timeout = -1

    def settimeout(self, val):
        self.timeout = val


class ThreadMock():
    def __init__(self) -> None:
        self.alive = False

    def is_alive(self) -> bool:
        return self.alive


class AMIClientMock():
    def __init__(self, address, port, timeout) -> None:
        self.send_action_last_action = None
        self.send_action_response = None
        self.action_count = 0
        self.connected = False
        self.logged_in = False
        self.logged_in_username = None
        self.logged_in_secret = None
        self.login_response = None

        self._event_listeners = []
        self._timeout = 10
        self._socket = SocketMock()
        self._thread = ThreadMock()

        self._address = address
        self._port = port

    def add_event_listener(self, event_listener):
        self._event_listeners.append(event_listener)

    def remove_event_listener(self, event_listener):
        self._event_listeners.remove(event_listener)

    def send_action(self, action):
        self.send_action_last_action = action
        return self.send_action_response

    def next_action_id(self) -> int:
        self.action_count += 1
        return self.action_count

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def login(self, username, secret) -> FutureResponseMock:
        self.logged_in = True
        self.logged_in_username = username
        self.logged_in_secret = secret
        return self.login_response

    def logoff(self) -> None:
        self.logged_in = False


class TestClientWrapper(unittest.TestCase):
    def setUp(self) -> None:
        self.__client = ClientWrapper("", 0, 1, 0)
        self.__ami_client = AMIClientMock("", 1, 0)
        self.__event_listener = EventListenerMock()

        self.__client._ClientWrapper__client = self.__ami_client
        self.__client._ClientWrapper__event_listener = self.__event_listener

    def test_login(self):
        self.__ami_client.login_response = FutureResponseMock(
            ResponseMock("Error", True))
        self.assertRaises(Exception, self.__client.login, "", "", 1, 1)

        self.__ami_client.login_response = FutureResponseMock(
            ResponseMock("Error", False))
        self.assertRaises(
            SystemExit,
            self.__client.login,
            "",
            "",
            0,
            0)

        self.__ami_client.login_response = FutureResponseMock(
            ResponseMock("Success", False))
        self.__client._ClientWrapper__is_login_validated = True
        self.__client._ClientWrapper__is_asterisk_fully_booted = True
        self.__client.login("<username>", "<secret>", 0, 0)

        self.assertEqual(self.__ami_client.logged_in_username, "<username>")
        self.assertEqual(self.__ami_client.logged_in_secret, "<secret>")
        self.assertEqual(
            self.__ami_client._socket.timeout,
            None,
            "Expected socket timeout to be set to None")

    def test_logoff(self):
        self.__ami_client._event_listeners.append(
            self.__client._ClientWrapper__validate_ami_connection)
        self.__client._validated_login = True
        self.__ami_client.logged_in = True

        self.__client.logoff()

        self.assertFalse(
            self.__ami_client.logged_in,
            "Expected AMI Client to be logged off")
        self.assertEqual(len(self.__ami_client._event_listeners),
                         0, "Expected event listeners to be detached")

    def test_disconnect(self):
        self.__ami_client.connected = True
        self.__client.disconnect()
        self.assertFalse(
            self.__ami_client.connected,
            "Expected client to be disconnected")

    def test_check_event_thread_health(self):
        self.__client._ClientWrapper__is_login_validated = False
        self.__ami_client._thread.alive = True
        self.assertTrue(
            self.__client.check_event_thread_health(),
            "Expected thread to be alive")

        self.__client._ClientWrapper__is_login_validated = True
        self.assertTrue(
            self.__client.check_event_thread_health(),
            "Expected thread to be alive")

        self.__ami_client._thread.alive = False
        self.assertFalse(
            self.__client.check_event_thread_health(),
            "Expected thread to not be alive")

    def test_add_event_filter(self):
        f1 = EventFilterMock()
        f2 = EventFilterMock()
        self.__client.add_event_filter([f1, f2])
        self.assertEqual(
            self.__event_listener.event_filter[0],
            f1,
            "Expected filter 1 to be attached to the event listener")
        self.assertEqual(
            self.__event_listener.event_filter[1],
            f2,
            "Expected filter 2 to be attached to the event listener")

    def test_remove_event_filter(self):
        f1 = EventFilterMock()
        f2 = EventFilterMock()
        self.__event_listener.event_filter = [f1, f2]
        self.__client.remove_event_filter([f1])
        self.assertEqual(len(self.__event_listener.event_filter), 1,
                         "Expected only one filter left attached to the event listener")
        self.assertEqual(
            self.__event_listener.event_filter[0],
            f2,
            "Expected filter 2 still attached to the event listener")

    def test_attach_event_listener(self):
        self.__client.attach_event_listener(self.__event_listener.on_event)
        self.assertEqual(
            self.__ami_client._event_listeners[0],
            self.__event_listener.on_event)

    def test_detach_event_listener(self):
        el1 = EventListenerMock()
        el2 = EventListenerMock()
        self.__ami_client._event_listeners = [el1, el2]
        self.__client.detach_event_listener(el1)
        self.assertEqual(len(self.__ami_client._event_listeners), 1,
                         "Expected only one listener left attached to the ami client")
        self.assertEqual(
            self.__ami_client._event_listeners[0],
            el2,
            "Expected listener 2 still attached to the ami client")

    def test_get_next_action_id(self):
        self.__client.get_next_action_id()
        self.__client.get_next_action_id()
        self.assertEqual(self.__ami_client.action_count, 2,
                         "Expected action count to be increased to 2")

    def test_set_response_timeout(self):
        self.__client.set_response_timeout(20)
        self.assertEqual(self.__ami_client._timeout, 20,
                         "Expected ami client timeout to be 20s")

    def test_send_action(self):
        action = {"Test": "Action"}
        self.__client.send_action(action)
        self.assertEqual(self.__ami_client.send_action_last_action,
                         action,
                         "Expected action to be send to the ami client")
