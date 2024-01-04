# Asterisk prometheus exporter
Repository that provides a dynamically configurable Prometheus exporter for Asterisk. The exporter uses the Asterisk Manager Interface (AMI) to communicate with Asterisk and YAML files to configure what data is scraped from Asterisk and what metrics are generated. This allows the exporter to be used with older Asterisk versions in different environments.

## Installation
### Docker
You can use the provided Docker image from GitHub Packages. \
Run the Docker image and mount the configuration:
```
docker run -p 8080:8080 -v ./config.yml:/home/dev/asterisk-prometheus-exporter/config.yml ghcr.io/gonicus/asterisk-prometheus-exporter:latest
```
The configured metrics can be accessed at http://localhost:8080. \
Alternatively, you can also create a Docker image using the provided Dockerfile.

### Python Poetry
The exporter uses Poetry as it's dependency management. Head over to [Poetry](https://python-poetry.org/) to install the latest version for your desired platform.

Install the required dependencies using Poetry:
```
poetry install
```

Start the exporter:
```
poetry run python src/main.py
```
The configured metrics can be accessed at http://localhost:8080.

By default, the exporter loads the configuration `config.yml` and uses port 8080. \
A different port can be specified via the first positional argument: `poetry run python src/main.py 9090`. \
A different configuration can be set using the `--config` option: `poetry run python src/main.py --config path/to/config.yml`.

## Configuration
This section shows the rough structure of the configuration. See `src/config_schema.yml` for a detailed description of the configuration and what is possible.

Before customizing the configuration, it is recommended to have a rough overview of the Asterisk Manager Interfance (AMI) and how it works. The next section uses AMI terms that will not be explained further.

The configuration is generally structured in such a way that it is determined which events sent by the Asterisk are filtered and which metrics should be generated based on the events received and the data they contain.

The first and only required section of the configuration is the `ami_client` section. Here you configure which Asterisk and which access data you should log in with.
```yml
ami_client:
  ip: "1.2.3.4"
  port: 5038
  username: "ami_user"
  secret: "test"
```

The `filter` section of the configuration is used to define filter, which are used to collect events from the Asterisk that are send to the AMI client when an event is triggered within the Asterisk. An event that falls under this, for example, is the DialBegin event, which is sent by the Asterisk when a dial action is started. The filters defined in this section are used from the start of the exporter until the end. For each filter, you first define which events should be filter and then which metrics should be generated from the filtered events. \
The following example shows a configuration that counts how many calls are made:
```yml
filter:
  - event: "DialBegin"
    metrics:
      - name: "dial_count"
        description: "Total number of started dials"
        value:
          type: counter  # Currently supported open metric types: counter, gauge
          increment_value: "1"  # Increment the metric value every time a DialBegin event is received
```

The `scrape` section is used to define actions that are send to the AMI in a specific interval. Here you first determine the interval at which the scraping is taking place. A list is then specified which actions should be sent to the AMI, which events should then be filtered and the metrics that should be generated based on the filtered events. The attribute `until` is used to set which event is expected to be the last event of the action. \
The following example shows a configuration that counts how many members are logged into a specific queue:
```yml
scrape:
  interval: 15  # Send the actions every 15 seconds
  actions:
    - name: "QueueStatus"  # Action that should be sent
      collect:
        # Events to filter after sending the action
        - event: "QueueMember"
          metrics:
            - name: "queue_member_count"
              description: "Number of members currently logged into a specific queue"
              value:
                type: gauge
                increment_value: "1"
                value_on_scrape_start: 0
              labels:
                - name: "queue"
                  value: "$Queue"  # Use '$' to access attributes from the filtered event
      until: "ContactStatusDetailComplete"
```

## Example configuration
Below is an entire example configuration that scrapes the RTCP fraction lost of the known endpoints and counts the number of members currently logged into a specific queue. \
This configuration allows, for example, to send an alert if too few members are logged into a queue or to see whether a user agent has connection problems.
```yml
ami_client:
  ip: "1.2.3.4"
  port: 5038
  username: "ami_user"
  secret: "test"

filter:
  - event: "RTCPSend|RTCPReceived"
    metrics:
      - name: "rtcp_endpoint_x_fraction_lost"
        description: "Aggregate fraction lost of RTCP events"
        value:
          type: counter
          increment_value: "$Report0FractionLost"
        labels:
          - name: "endpoint"
            value: "$CallerIDNum"

scrape:
  interval: 15
  actions:
    - name: "QueueStatus"
      collect:
        - event: "QueueMember"
          metrics:
            - name: "queue_member_count"
              description: "Number of members currently logged into a specific queue"
              value:
                type: gauge
                increment_value: "1"
                value_on_scrape_start: 0
              labels:
                - name: "queue"
                  value: "$Queue"
      until: "QueueStatusComplete"
```
The metrics generated based on the configuration might look like this:
```
# HELP rtcp_endpoint_x_fraction_lost_total Aggregate fraction lost of RTCP events
# TYPE rtcp_endpoint_x_fraction_lost_total counter
rtcp_endpoint_x_fraction_lost_total{endpoint="100"} 0.0
rtcp_endpoint_x_fraction_lost_total{endpoint="200"} 255.0
rtcp_endpoint_x_fraction_lost_total{endpoint="300"} 291.0
# HELP rtcp_endpoint_x_fraction_lost_created Aggregate fraction lost of RTCP events
# TYPE rtcp_endpoint_x_fraction_lost_created gauge
rtcp_endpoint_x_fraction_lost_created{endpoint="100"} 1.7026356281841428e+09
rtcp_endpoint_x_fraction_lost_created{endpoint="200"} 1.702635652441021e+09
rtcp_endpoint_x_fraction_lost_created{endpoint="300"} 1.7026356524437878e+09
# HELP queue_member_count Number of members currently logged into a specific queue
# TYPE queue_member_count gauge
queue_member_count{queue="zentrale"} 2.0
queue_member_count{queue="support"} 2.0
```
