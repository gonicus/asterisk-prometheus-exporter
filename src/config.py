from dataclasses import dataclass, field
from typing import List, Dict, Any
import yaml
from event_filter import EventFilter
from jsonschema import validate
from pathlib import Path
from metric_values import MetricValue, MetricValueCounter, MetricValueGauge
from action import Action
import logging


def _load_metric_labels(metric_config: Dict[Any, Any]) -> Dict[str, str]:
    """Loads the given dict and generates the labels from it. See config_schema.yml for more information."""
    if "labels" not in metric_config:
        return {}

    labels: Dict[str, str] = {}
    for label in metric_config["labels"]:
        labels[label["name"]] = label["value"]
    return labels


def _load_metric_value_counter(value_config: Dict[Any, Any],
                               name: str,
                               description: str,
                               labels: Dict[str, str]) -> MetricValueCounter:
    """Loads the given dict and creates a MetricValueCounter based on it. See config_schema.yml for more information."""
    increment_value = value_config.get("increment_value", "1")

    metric = MetricValueCounter(name, description, labels, increment_value)
    metric.init()
    return metric


def _load_metric_value_gauge(value_config: Dict[Any, Any],
                             name: str,
                             description: str,
                             labels: Dict[str, str]) -> MetricValueGauge:
    """Loads the given dict and creates a MetricValueGauge based on it. See config_schema.yml for more information."""
    set_value = value_config.get("set_value", None)
    increment_value = value_config.get("increment_value", None)
    value_on_scrape_start = value_config.get("value_on_scrape_start", None)

    metric = MetricValueGauge(
        name,
        description,
        labels,
        set_value,
        increment_value,
        value_on_scrape_start)
    metric.init()
    return metric


def _load_metric(metric_config: Dict[Any, Any]) -> MetricValue:
    """Loads the given dict and creates a MetricValue based on it. See config_schema.yml for more information."""
    name = metric_config["name"]
    description = metric_config["description"]
    labels = _load_metric_labels(metric_config)

    if metric_config["value"]["type"] == "counter":
        return _load_metric_value_counter(
            metric_config["value"], name, description, labels)
    elif metric_config["value"]["type"] == "gauge":
        return _load_metric_value_gauge(
            metric_config["value"], name, description, labels)

    raise Exception("Invalid metric type")


def _load_event_filter(event_config: Dict[Any, Any]) -> EventFilter:
    """Loads the given dict and creates an EventFilter based on it. See config_schema.yml for more information."""
    event_names: List[str] = event_config["event"]
    metric_values: List[MetricValue] = []

    if "|" in event_config["event"]:
        event_names = event_config["event"].split("|")

    if "metrics" in event_config:
        for metric in event_config["metrics"]:
            metric_values.append(_load_metric(metric))

    return EventFilter(event_names, metric_values)


def _load_action(action_config: Dict[Any, Any]) -> Action:
    """Loads the given dict and creates an Action based on it. See config_schema.yml for more information."""
    name = action_config["name"]
    filter_list: List[EventFilter] = []
    until = action_config["until"]
    response_timeout = action_config.get(
        "response_timeout",
        default_config.action_response_timeout)
    event_timeout = action_config.get(
        "event_timeout", default_config.action_event_timeout)
    action_priority = action_config.get(
        "action_priority", default_config.action_priority)
    action_context = action_config.get(
        "action_context", default_config.action_context)
    action_caller_id = action_config.get(
        "action_caller_id", default_config.action_caller_id)

    if "collect" in action_config:
        for filter in action_config["collect"]:
            filter_list.append(_load_event_filter(filter))

    return Action(
        name,
        filter_list,
        until,
        response_timeout,
        event_timeout,
        action_priority,
        action_context,
        action_caller_id)


@dataclass
class __AMIClientConfig():
    ip: str = "undefined"
    port: int = 0
    username: str = "undefined"
    secret: str = "undefined"

    def load(self, config: Dict[Any, Any]) -> None:
        """Loads the given dict. See config_schema.yml for more information."""
        self.ip = config["ip"]
        self.port = config["port"]
        self.username = config["username"]
        self.secret = config["secret"]


@dataclass
class __GeneralConfig():
    log_level: str = "INFO"
    login_validation_timeout: int = 10
    fully_booted_validation_timeout: int = 60
    response_timeout: int = 10
    ping_timeout: int = 120

    def load(self, config: Dict[Any, Any]) -> None:
        """Loads the given dict. See config_schema.yml for more information."""
        self.log_level = config.get("log_level", self.log_level)
        self.login_validation_timeout = config.get(
            "login_validation_timeout", self.login_validation_timeout)
        self.fully_booted_validation_timeout = config.get(
            "fully_booted_validation_timeout", self.fully_booted_validation_timeout)
        self.response_timeout = config.get(
            "response_timeout", self.response_timeout)
        self.ping_timeout = config.get("ping_timeout", self.ping_timeout)


@dataclass
class __DefaultConfig():
    scrape_interval: int = 10
    action_response_timeout: int = 5
    action_event_timeout: int = 10
    action_priority: int = 1
    action_context: str = "default"
    action_caller_id: str = "python"

    def load(self, config: Dict[Any, Any]):
        """Loads the given dict. See config_schema.yml for more information."""
        self.scrape_interval = config.get(
            "scrape_interval", self.scrape_interval)
        self.action_response_timeout = config.get(
            "action_response_timeout", self.action_response_timeout)
        self.action_event_timeout = config.get(
            "action_event_timeout", self.action_event_timeout)
        self.action_priority = config.get(
            "action_priority", self.action_priority)
        self.action_context = config.get("action_context", self.action_context)
        self.action_caller_id = config.get(
            "action_caller_id", self.action_caller_id)


@dataclass
class __FilterConfig():
    filter_list: List[EventFilter] = field(default_factory=list)

    def load(self, config: Dict[Any, Any]) -> None:
        """Loads the given dict. See config_schema.yml for more information."""
        for filter in config:
            self.filter_list.append(_load_event_filter(filter))


@dataclass
class __ScrapeConfig():
    interval = 0
    action_list: List[Action] = field(default_factory=list)

    def load(self, config: Dict[Any, Any]) -> None:
        """Loads the given dict. See config_schema.yml for more information."""
        self.interval = config.get("interval", default_config.scrape_interval)
        if "actions" in config:
            for action in config["actions"]:
                self.action_list.append(_load_action(action))


ami_client_config = __AMIClientConfig()
general_config = __GeneralConfig()
default_config = __DefaultConfig()
filter_config = __FilterConfig()
scrape_config = __ScrapeConfig()


def load_from_file(path: str) -> None:
    """Loads the specified file. The specified file must match the config_schema.yml,
    otherwise an exception is thrown."""
    global ami_client_config
    global default_config
    global filter_config
    global scrape_config

    with open(Path(__file__).resolve().parent / "config_schema.yml", "r") as stream:
        schema = yaml.safe_load(stream)

    with open(path, "r") as stream:
        config = yaml.safe_load(stream)

    validate(instance=config, schema=schema)

    ami_client_config.load(config["ami_client"])

    if "general" in config:
        general_config.load(config["general"])

    if "default" in config:
        default_config.load(config["default"])

    if "filter" in config:
        filter_config.load(config["filter"])

    if "scrape" in config:
        scrape_config.load(config["scrape"])

    logging.basicConfig()
    logging.getLogger().setLevel(general_config.log_level)
