import logging
from time import sleep, time
from typing import List, Any
from asterisk.ami import AMIClient, SimpleAction, Event, FutureResponse
from event_listener import EventListener
from event_filter import EventFilter


class ClientWrapper:
    def __init__(
            self,
            address: str,
            port: int,
            timeout: int,
            ping_timeout: int) -> None:
        self.__client: AMIClient = AMIClient(
            address=address, port=port, timeout=timeout)
        self.__event_listener: EventListener = EventListener()
        self.__is_login_validated: bool = False
        self.__is_asterisk_fully_booted: bool = False

        self.__wait_sequence_timeout = 0.02

        self.__ping_timeout = ping_timeout

    def __raise_critical(self, msg: str) -> None:
        """Logs a critical message and raises an exception.

        :param str message: Message that is logged and used within the exception."""
        logging.critical(msg)
        raise Exception(msg)

    def __validate_login(self, event: Event, **kwargs) -> None:
        """Event callback used during login to wait for the SuccessfulAuth event."""
        if event.name is None:
            return
        if event.name == "SuccessfulAuth":
            self.__is_login_validated = True
            self.__client.remove_event_listener(self.__validate_login)
            logging.info("Validated AMI client login")

    def __validate_asterisk_fully_booted(self, event: Event, **kwargs) -> None:
        """Event callback used during login to wait for the FullyBooted event."""
        if event.name is None:
            return
        if event.name == "FullyBooted":
            self.__is_asterisk_fully_booted = True
            self.__client.remove_event_listener(self.__validate_asterisk_fully_booted)
            logging.info("Validated Asterisk is fully booted")

    def __validate_ami_connection(self) -> bool:
        """Sends a test action to the AMI to make sure the connection is still up.

        :return: True if the connection is still up. Otherwise False is returned."""
        # Send a test action to validate the connection to the AMI
        action = SimpleAction(
            "Ping",
            ActionID=self.get_next_action_id())

        future = self.__client.send_action(action)
        if future.response is None:
            logging.error(
                f"Did not receive response after {str(self.__client._timeout)}s")
            return False

        self.__event_listener.update_time_of_last_event()
        return True

    def login(self, username: str, secret: str, login_timeout: int, fully_booted_timeout: int) -> None:
        """Connects to the AMI as a client and sends a login action with the given credentials.
        Validates the login by waiting for the SuccessfulAuth event and validates that the Asterisk is fully booted
        by waiting for the FullyBooted event.
        Returns after both events are validated."""
        self.__client.add_event_listener(self.__validate_login)
        self.__client.add_event_listener(self.__validate_asterisk_fully_booted)
        self.__client.add_event_listener(self.__event_listener.on_event)

        logging.debug(f"Connecting to AMI: {self.__client._address}:{self.__client._port}")

        self.__client.connect()

        # Prevent socket from closing if no events are sent by the AMI. We are validating the
        # AMI connection using the custom EventListener.
        self.__client._socket.settimeout(None)

        future = self.__client.login(username, secret)
        if future.response.is_error():
            self.__raise_critical(str(future.response))

        # - Validate successful login by waiting for the __validate_login function to collect the SuccessfulAuth event
        # - Validate that Asterisk is fully booted by waiting for the __validate_asterisk_fully_booted
        #   function to collect the FullyBooted event.
        start_time = time()
        while self.__is_login_validated is False or self.__is_asterisk_fully_booted is False:
            if not self.__is_login_validated and time() > start_time + login_timeout:
                self.__raise_critical(
                    f"Unable to login AMI client: reached timeout of {login_timeout}s when validating login")
            if not self.__is_asterisk_fully_booted and time() > start_time + fully_booted_timeout:
                self.__raise_critical(f"Unable to login AMI client: reached timeout of {fully_booted_timeout}s when "
                                      "validating that Asterisk is fully booted")

            sleep(self.__wait_sequence_timeout)

    def logoff(self) -> None:
        """Logs of the client and resets the event filters currently attached to the event listener."""
        self.__client._event_listeners.clear()
        self._validated_login = False
        self.__client.logoff()

    def disconnect(self) -> None:
        """Disconnects the client from the AMI and resets the event filters currently attached to the event listener"""
        self.__client.disconnect()
        self.__client._event_listeners.clear()
        self.__is_login_validated = False

    def check_event_thread_health(self) -> bool:
        """Checks the status of the event thread an if it is still running.

        :return: True if the event thread is still running. Otherwise False is returned."""
        if not self.__is_login_validated:
            return True
        if self.__client._thread.is_alive():
            return True
        return False

    def check_ami_connection_health(self) -> bool:
        """Checks the status of the connection to the AMI.

        :return: True if the connection still persists. If the connection is lost, false is returned."""
        if self.__event_listener.get_time_of_last_event() + self.__ping_timeout < time():
            logging.warning(
                f"Did not receive any events after {self.__ping_timeout}s, validating connection to the AMI.")
            return self.__validate_ami_connection()
        return True

    def add_event_filter(self, filter_list: List[EventFilter]) -> None:
        """Adds an event filter to the main event listener of the client.
        The event filter will therefore receive any event send by the AMI."""
        for filter in filter_list:
            self.__event_listener.add_event_filter(filter)

    def remove_event_filter(self, filter_list: List[EventFilter]) -> None:
        """Removes a specific event filter from the main event listener of the client.
        The event filter will then no longer receive any new events send by the AMI."""
        for filter in filter_list:
            self.__event_listener.remove_event_filter(filter)

    def attach_event_listener(self, listener: Any) -> None:
        """Attaches an event listener to the AMI client.
        The event listener will therefore receive events send by the AMI."""
        self.__client.add_event_listener(listener)

    def detach_event_listener(self, listener: Any) -> None:
        """Detaches a specific event listener from the AMI client, if it exists.
        The event listener will then no longer receive any new events send by the AMI."""
        self.__client.remove_event_listener(listener)

    def get_next_action_id(self) -> str:
        """Returns the next action id."""
        return self.__client.next_action_id()

    def set_response_timeout(self, timeout: float) -> None:
        """Sets the response timeout of the AMI client."""
        self.__client._timeout = timeout

    def send_action(self, action: SimpleAction) -> FutureResponse:
        """Sends a simple action to the AMI client"""
        return self.__client.send_action(action)
