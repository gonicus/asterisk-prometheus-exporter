from dataclasses import dataclass
from typing import Dict, List
from client_wrapper import ClientWrapper
from event_filter import EventFilter
from asterisk.ami import Event, SimpleAction
import logging
from time import time, sleep


@dataclass
class Action():
    name: str
    filter_list: List[EventFilter]
    until: str
    response_timeout: int
    event_timeout: int
    action_priority: int
    action_context: str
    action_caller_id: str


class ActionExecuter():
    """Class to execute multiple actions via a specific AMI client."""

    def __init__(self, client: ClientWrapper) -> None:
        self.__client = client

        self.__finished: bool = False
        self.__action_id: str = ""

        self.__wait_sequence_timeout: float = 0.02

    def __on_event(self, event: Event, **kwargs) -> None:
        """Callback for the AMI Client. Used to wait for the end event of an action."""
        if "ActionID" not in event.keys:
            return
        if event.name == self.__action.until and event.keys["ActionID"] == self.__action_id:
            logging.debug(f"Collected success event: {event.name}")
            self.__finished = True

    def __attach_event_filter(self) -> None:
        """Attaches all event filters of the action to the AMIClient as well as the __on_event callback."""
        for filter in self.__action.filter_list:
            filter.on_scrape_start(self.__action_id)

        self.__client.add_event_filter(self.__action.filter_list)
        self.__client.attach_event_listener(self.__on_event)

    def __send_action(self) -> bool:
        """Sends the action to the AMIClient and evaluates the response.

        :return: True on success, False if an error occurred."""
        kwargs: Dict[str, str] = {}
        kwargs["Priority"] = str(self.__action.action_priority)
        kwargs["Context"] = str(self.__action.action_context)
        kwargs["CallerID"] = str(self.__action.action_caller_id)
        kwargs["ActionID"] = str(self.__action_id)

        action = SimpleAction(self.__action.name, **kwargs)
        self.__client.set_response_timeout(self.__action.response_timeout)

        future = self.__client.send_action(action)
        if future.response is None:
            logging.error(
                f"Action '{self.__action.name}': Did not receive response after {self.__action.response_timeout}s")
            return False
        if future.response.status != "Success":
            msg = str(future.response.keys.get("Message", future.response))
            logging.error(f"Unable to fetch {self.__action.name}: action response: {msg}")
            return False

        return True

    def __collect_events(self) -> bool:
        """Waits for all expected events to be collected.
        Should only be called if the __on_event callback has already been attached to the AMIClient.
        Otherwise the function will run until the event_timeout is reached.

        :return True when every expected event is collected. False is returned if the expected events were
                not collected in the given event_timeout."""
        start_time = time()
        while not self.__finished:
            if time() > start_time + self.__action.event_timeout:
                logging.error(
                    f"Unable to fetch {self.__action.name}: reached event timeout of {self.__action.event_timeout}s")
                return False
            sleep(self.__wait_sequence_timeout)
        return True

    def __detach_event_filter(self) -> None:
        """Detaches any previously attached EventListener, as well as the __on_event callback."""
        for filter in self.__action.filter_list:
            filter.on_scrape_end()

        self.__client.remove_event_filter(self.__action.filter_list)
        self.__client.detach_event_listener(self.__on_event)
        self.__finished = False

    def exec(self, action: Action) -> None:
        """Executes the given action and waits until all events and metrics have been collected."""
        self.__action = action
        self.__finished = False
        self.__action_id = self.__client.get_next_action_id()

        logging.debug(f"Executing action: '{action.name}', action_id={self.__action_id}")

        self.__attach_event_filter()
        result = self.__send_action()
        if result:
            self.__collect_events()
        self.__detach_event_filter()

        logging.debug(f"Finished processing action: {action.name}, action_id={self.__action_id}")
