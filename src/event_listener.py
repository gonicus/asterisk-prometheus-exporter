import logging
from time import time
import traceback
from typing import List
from asterisk.ami import EventListener as ClientEventListener
from event_filter import EventFilter


class EventListener(ClientEventListener):
    """Class used to listen for all events send to a specific AMI client and filter them using EventFilter."""

    def __init__(self) -> None:
        self.__event_filter: List[EventFilter] = []

        # UNIX timestamp when the last event was received. Used to validate the
        # connection to the AMI.
        self.__last_event_received: float = time()

    def add_event_filter(self, filter: EventFilter) -> None:
        """Adds a filter to the filter list, which thus receives all events."""
        logging.debug(f"Attach event filter: {filter.get_event_names()}")
        self.__event_filter.append(filter)

    def remove_event_filter(self, filter: EventFilter) -> None:
        """Deletes an event filter from the event filter list. The filter will therefore
        no longer receive new events."""
        self.__event_filter.remove(filter)

    def get_time_of_last_event(self) -> float:
        """Returns the UNIX timestamp of the last received event."""
        return self.__last_event_received

    def update_time_of_last_event(self) -> None:
        """Sets the time of the last received event to the current time.
        Used for the validation of the AMI connection."""
        self.__last_event_received = time()

    def reset(self) -> None:
        """Resets the event filter currently attached to the event listener."""
        self.__event_filter.clear()

    def on_event(self, event, **kwargs) -> None:
        """Callback used to get each event. Saves the time of the last event received and forwards the event to
        each event filter. Unhandled exception raised in the event filters are logged here."""
        self.__last_event_received = time()
        try:
            for filter in self.__event_filter:
                filter.process_event(event)
        except Exception:
            logging.error(traceback.format_exc())
