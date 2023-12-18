import unittest
import config


class TestConfig(unittest.TestCase):
    def test__load_metric_labels(self):
        c = {"labels": [
            {"name": "label_1",
             "value": "label_1_value"},
            {"name": "label_2",
             "value": "label_2_value"}
        ]}

        result = config._load_metric_labels(c)
        self.assertEqual(
            result["label_1"],
            "label_1_value",
            "Expected label 1 to be correctly loaded")
        self.assertEqual(
            result["label_2"],
            "label_2_value",
            "Expected label 2 to be correctly loaded")

    def test__load_metric_value_counter(self):
        c = {"type": "counter",
             "increment_value": "inc_val"}
        result = config._load_metric_value_counter(
            c, "counter", "test counter", {"label_1": "value"})
        self.assertEqual(
            result._MetricValueCounter__increment_value,
            "inc_val")

    def test__load_metric_value_gauge(self):
        c = {"type": "gauge",
             "set_value": "set_val",
             "value_on_scrape_start": "5",
             "increment_value": "inc_val"}
        result = config._load_metric_value_gauge(
            c, "gauge", "test gauge", {"label_1": "value"})
        self.assertEqual(result._MetricValueGauge__set_value, "set_val")
        self.assertEqual(result._MetricValueGauge__increment_value, "inc_val")
        self.assertEqual(result._MetricValueGauge__value_on_scrape_start, "5")

    def test__load_metric(self):
        c = {"name": "metric name",
             "description": "metric description",
             "labels": [{"name": "label_1", "value": "value"}],
             "value": {"type": "undef"}}
        self.assertRaisesRegex(
            Exception,
            "Invalid metric type",
            config._load_metric,
            c)

        c = {
            "name": "metric_name", "description": "metric description", "labels": [
                {
                    "name": "label_1", "value": "value 1"}, {
                    "name": "label_2", "value": "value 2"}], "value": {
                "type": "counter", "increment_value": "2"}}
        metric = config._load_metric(c)
        self.assertEqual(metric._metric_name, "metric_name")
        self.assertEqual(metric._metric_description, "metric description")
        self.assertEqual(
            metric._metric_labels, {
                "label_1": "value 1", "label_2": "value 2"})
        self.assertEqual(metric._metric_label_names, ["label_1", "label_2"])

    def test__load_event_filter(self):
        c = {"event": "event1|event2"}
        event_filter = config._load_event_filter(c)
        self.assertEqual(
            event_filter._EventFilter__event_names, [
                "event1", "event2"])

        c = {"event": "event1"}
        event_filter = config._load_event_filter(c)
        self.assertEqual(event_filter._EventFilter__event_names, "event1")

    def test__load_action(self):
        c = {"name": "ActionName",
             "until": "EventName",
             "response_timeout": 5,
             "event_timeout": 5,
             "action_priority": 5,
             "action_context": "context",
             "action_caller_id": "caller_id"}
        action = config._load_action(c)
        self.assertEqual(action.name, "ActionName")
        self.assertEqual(action.until, "EventName")
        self.assertEqual(action.response_timeout, 5)
        self.assertEqual(action.event_timeout, 5)
        self.assertEqual(action.action_priority, 5)
        self.assertEqual(action.action_context, "context")
        self.assertEqual(action.action_caller_id, "caller_id")

        # Test default values
        c = {"name": "ActionName",
             "until": "EventName", }
        action = config._load_action(c)
        self.assertEqual(action.response_timeout,
                         config.default_config.action_response_timeout)
        self.assertEqual(action.event_timeout,
                         config.default_config.action_event_timeout)
        self.assertEqual(
            action.action_priority,
            config.default_config.action_priority)
        self.assertEqual(
            action.action_context,
            config.default_config.action_context)
        self.assertEqual(
            action.action_caller_id,
            config.default_config.action_caller_id)


class TestAMIClientConfig(unittest.TestCase):
    def test_load(self):
        c = {"ip": "<ip>",
             "port": 5,
             "username": "<username>",
             "secret": "<secret>"}
        config.ami_client_config.load(c)
        self.assertEqual(config.ami_client_config.ip, "<ip>")
        self.assertEqual(config.ami_client_config.port, 5)
        self.assertEqual(config.ami_client_config.username, "<username>")
        self.assertEqual(config.ami_client_config.secret, "<secret>")


class TestGeneralConfig(unittest.TestCase):
    def test_load(self):
        c = {"log_level": "<log_level>",
             "login_validation_timeout": 5,
             "response_timeout": 5,
             "ping_timeout": 5}
        config.general_config.load(c)
        self.assertEqual(config.general_config.log_level, "<log_level>")
        self.assertEqual(config.general_config.login_validation_timeout, 5)
        self.assertEqual(config.general_config.response_timeout, 5)
        self.assertEqual(config.general_config.ping_timeout, 5)


class TestDefaultConfig(unittest.TestCase):
    def test_load(self):
        c = {"scrape_interval": 5,
             "action_response_timeout": 5,
             "action_event_timeout": 5,
             "action_priority": 5,
             "action_context": "<context>",
             "action_caller_id": "<caller_id>"}
        config.default_config.load(c)
        self.assertEqual(config.default_config.scrape_interval, 5)
        self.assertEqual(config.default_config.action_response_timeout, 5)
        self.assertEqual(config.default_config.action_event_timeout, 5)
        self.assertEqual(config.default_config.action_priority, 5)
        self.assertEqual(config.default_config.action_context, "<context>")
        self.assertEqual(config.default_config.action_caller_id, "<caller_id>")


class TestScrapeConfig(unittest.TestCase):
    def test_load(self):
        c = {"interval": 5}
        config.scrape_config.load(c)
        self.assertEqual(config.scrape_config.interval, 5)
