from typing import List, Dict, Optional, Sequence
from asterisk.ami import Event
from prometheus_client import Counter, Gauge
import logging


class MetricValue():
    """Parent class for any wrapper of a Prometheus metric type."""

    def __init__(self, metric_name: str, metric_description: str,
                 metric_labels: Dict[str, str]) -> None:
        self._metric_name = metric_name
        self._metric_description = metric_description
        self._metric_labels = metric_labels
        self._metric_label_names: List[str] = list(metric_labels)

    def init(self) -> None:
        """Function implemented by the child classes, used to initialize the Prometheus metric.
        This function may only be called once per metric. Otherwise an exception is thrown."""
        ...

    def on_scrape_start(self) -> None:
        """Function implemented by the child classes, used to send a signal to the metrics that they can
        reset values if necessary."""
        ...

    def on_scrape_end(self) -> None:
        """Function implemented by the child classes, used to send a signal to the metrics that they can
        update the metric values."""
        ...

    def process_event(self, event: Event):
        """Function implemented by the child classes, used to process the given event and extract the
        expected values.

        :param Event event: The event to process"""
        ...

    def _eval_value(self, event: Event, value: str) -> str:
        """Evaluates a specific value. If the value begins with a '$', the value is looked up in the given event.

        :param Event event: The event in which the value will be looked up
        :return: If the value begins with a "$", the searched value of the specified event is returned.
                 Otherwise, the value itself is returned."""
        if len(value) == 0:
            return value

        if value[0] == "$":
            key = value[1:]
            if key not in event.keys:
                logging.error(
                    f"Unable to eval reference: Attribute '{key}' does not exist in event "
                    f"with name '{event.name}'")
                return value
            return str(event.keys[value[1:]])  # type: ignore

        return value

    def _eval_labels(self, event: Event) -> Dict[str, str]:
        """Evaluates the self._metric_labels list and their value for the given event.
        The function eval_value is used to evaluate each value.

        :param Event event: The event in which the values are looked up.
        :return: Dict of the evaluated labels. If the label value begins with a "$", the searched value of the
                 specified event is used.
                 Otherwise, the value itself is used."""
        result: Dict[str, str] = {}
        for key in self._metric_labels:
            value = self._metric_labels[key]
            result[key] = self._eval_value(event, value)
        return result


class MetricValueCounter(MetricValue):
    """Wrapper above the Prometheus Counter metric type."""

    def __init__(self,
                 metric_name: str,
                 metric_description: str,
                 metric_labels: Dict[str, str],
                 increment_value: str) -> None:
        super().__init__(metric_name, metric_description, metric_labels)

        self.__counter: Optional[Counter] = None
        self.__increment_value: str = increment_value

    def __convert_value(self, value: str) -> float:
        """Converts the given value to a float and logs any errors that occur. If an error occurred, 0 is returned."""
        try:
            return float(value)
        except ValueError:
            logging.error(
                f"metric_name: {self._metric_name}: Unable to convert value {value} to a type of float")
            return 0

    def init(self) -> None:
        """Initializes the Prometheus Counter metric."""
        self.__counter = Counter(
            self._metric_name,
            self._metric_description,
            self._metric_label_names)

    def process_event(self, event: Event) -> None:
        """Processes the given event and evaluates the expected metrics from it.

        :param Event event: The event from which the metrics are evaluated."""
        if self.__counter is None:
            raise Exception("Metric is not initialized")

        if len(self._metric_labels) == 0:
            self.__counter.inc(
                self.__convert_value(
                    self._eval_value(
                        event,
                        self.__increment_value)))
            return

        labels = self._eval_labels(event)
        self.__counter.labels(
            **labels).inc(self.__convert_value(self._eval_value(event, self.__increment_value)))


class MetricValueGauge(MetricValue):
    """Wrapper above the Prometheus Gauge metric type."""

    def __init__(self,
                 metric_name: str,
                 metric_description: str,
                 metric_labels: Dict[str, str],
                 set_value: Optional[str],
                 increment_value: Optional[str],
                 value_on_scrape_start: Optional[float]) -> None:
        super().__init__(metric_name, metric_description, metric_labels)

        self.__gauge: Optional[Gauge] = None
        self.__set_value: Optional[str] = set_value
        self.__increment_value: Optional[str] = increment_value
        self.__value_on_scrape_start: Optional[float] = value_on_scrape_start

        self.__value: float = 0
        self.__label_values: Dict[Sequence[str], float] = {}
        self.__scrape_metric: bool = False

    def __convert_value(self, value: str) -> float:
        """Converts the given value to a float and logs any errors that occur. If an error occurred, 0 is returned."""
        try:
            return float(value)
        except ValueError:
            logging.error(
                f"metric_name: {self._metric_name}: Unable to convert value {value} to a type of float")
            return 0

    def __set_on_scrape_start_value(self) -> None:
        """If __value_on_scrape_start is set, the function sets all already created metrics of
        the gauge with the respective labels to the __value_on_scrape_start value"""
        if self.__value_on_scrape_start is None:
            return

        if len(self._metric_labels) == 0:
            self.__value = self.__value_on_scrape_start
            return

        for key in self.__label_values:
            self.__label_values[key] = self.__value_on_scrape_start

    def __update_gauge(self) -> None:
        """Updates the gauge with the custom value types."""
        if self.__gauge is None:
            raise Exception("Metric is not initialized")

        if len(self._metric_labels) == 0:
            self.__gauge.set(self.__value)
            return

        for key in self.__label_values:
            self.__gauge.labels(*key).set(self.__label_values[key])

    def init(self) -> None:
        """Initializes the Prometheus Gauge metric."""
        self.__gauge = Gauge(
            self._metric_name,
            self._metric_description,
            self._metric_label_names)

    def on_scrape_start(self) -> None:
        """The function should be called at the beginning of a scraping process.
        If necessary, the function resets the metrics that have already been created."""
        if self.__gauge is None:
            return

        self.__scrape_metric = True
        self.__set_on_scrape_start_value()

    def on_scrape_end(self) -> None:
        """The function should be called at the end of a scraping process.
        Used to update the gauge metrics to the values evaluated by the scrape process."""
        self.__update_gauge()

    def process_event(self, event: Event) -> None:
        """Processes the given event, evaluates the expected metrics and updates the custom value types.
        The Prometheus Gauge must then be updated manually using the __update_gauge function.
        Otherwise the changes will not have any effect.

        :param Event event: The event from which the metrics are evaluated."""
        if len(self._metric_labels) == 0:
            if self.__set_value is not None:
                self.__value = self.__convert_value(
                    self._eval_value(event, self.__set_value))
            if self.__increment_value is not None:
                self.__value += self.__convert_value(
                    self._eval_value(event, self.__increment_value))
        else:
            labels = self._eval_labels(event)
            key = tuple(str(labels[label]) for label in self._metric_label_names)

            if key not in self.__label_values:
                self.__label_values[key] = 0

            if self.__set_value is not None:
                self.__label_values[key] = self.__convert_value(
                    self._eval_value(event, self.__set_value))
            if self.__increment_value is not None:
                self.__label_values[key] += self.__convert_value(
                    self._eval_value(event, self.__increment_value))

        if not self.__scrape_metric:
            self.__update_gauge()
