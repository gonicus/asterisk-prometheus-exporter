import logging
from typing import List, Optional
from asterisk.ami import Event
from metric_values import MetricValue


class EventFilter():
    def __init__(
            self,
            event_names: List[str],
            metric_values: List[MetricValue]) -> None:
        self.__event_names: List[str] = event_names
        self.__metric_values: List[MetricValue] = metric_values

        self.__action_id: Optional[str] = None

    def get_event_names(self) -> List[str]:
        return self.__event_names

    def on_scrape_start(self, action_id: str) -> None:
        """Sets the given action_id and passes the on_scrape_start signal to all metrics."""
        self.__action_id = action_id
        for metric in self.__metric_values:
            metric.on_scrape_start()

    def on_scrape_end(self) -> None:
        """Passes the on_scrape_end signal to all metrics."""
        for metric in self.__metric_values:
            metric.on_scrape_end()

    def process_event(self, event: Event) -> None:
        """Processes and filters the given event.
        If the name and, if applicable, the ActionID match, the event is passed to all metrics."""
        if event.name not in self.__event_names:
            return

        if self.__action_id is not None:
            if event.keys["ActionID"] != self.__action_id:
                return

        if self.__action_id is not None:
            logging.debug(f"Processing action based event: {event.name}")
        else:
            logging.debug(f"Processing event: {event.name}")

        for value in self.__metric_values:
            value.process_event(event)
