import asyncio
import argparse
import logging
from time import sleep
from client_wrapper import ClientWrapper
from prometheus_client import start_http_server
import config
from action import ActionExecuter


def __login(ami_client: ClientWrapper) -> None:
    """Log in to the AMIClient with the credentials from the config."""
    ami_client.login(
        config.ami_client_config.username,
        config.ami_client_config.secret,
        config.general_config.login_validation_timeout)


def __shutdown(ami_client: ClientWrapper) -> None:
    """Logoffs the AMIClient."""
    ami_client.logoff()


def __reconnect(ami_client: ClientWrapper) -> None:
    """Disconnects the AMIClient and logs back in again."""
    ami_client.disconnect()
    __login(ami_client)


def __restart_event_thread(ami_client: ClientWrapper) -> None:
    """Logs an error and restarts the connection to the AMI."""
    logging.error(
        "Event thread ended unexpectedly. Trying to restart connection")
    __reconnect(ami_client)


def __restart_connection(ami_client: ClientWrapper) -> None:
    """Logs an error and restarts the connection to the AMI."""
    logging.error("Connection to the AMI lost. Trying to restart connection")
    __reconnect(ami_client)


def __scrape(client: ClientWrapper):
    """Main loop to execute the loaded actions."""
    action_executer = ActionExecuter(client)
    try:
        while True:
            logging.debug("Starting scrape process")

            logging.debug("Checking health")
            if not client.check_event_thread_health():
                __restart_event_thread(client)
            if not client.check_ami_connection_health():
                __restart_connection(client)

            for action in config.scrape_config.action_list:
                action_executer.exec(action)

            logging.debug("Finished scrape process")
            logging.debug(f"Next scrape in: {config.scrape_config.interval}s")

            sleep(config.scrape_config.interval)

    except (KeyboardInterrupt, SystemExit):
        __shutdown(client)


def __parse_args():
    """Parses the program arguments and sets default values.

    :return: The parsed arguments."""
    parser = argparse.ArgumentParser()

    parser.add_argument('port', type=int, default=8080, nargs='?',
                        help="specifies the port the metrics will be exposed to")
    parser.add_argument('--config', type=str, default="config.yml",
                        help="sets the configuration file that will be loaded")

    args = parser.parse_args()

    return args


async def __main() -> None:
    args = __parse_args()

    config.load_from_file(args.config)
    logging.info(f"Loaded configuration file: '{args.config}'")

    ami_client = ClientWrapper(
        config.ami_client_config.ip,
        config.ami_client_config.port,
        config.general_config.response_timeout,
        config.general_config.ping_timeout)

    logging.debug("Attaching runtime event filters")

    # Attach the event filters that filter the events that Asterisk sends to the
    # AMI client without a previously sent action.
    # These filters are attached to the client until the exporter is stopped.
    ami_client.add_event_filter(config.filter_config.filter_list)

    __login(ami_client)
    start_http_server(args.port)
    logging.info(f"Started server on port {args.port}")
    __scrape(ami_client)


if __name__ == "__main__":
    asyncio.run(__main())
