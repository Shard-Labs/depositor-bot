from prometheus_client import start_http_server

from scripts.delegator_utils.delegator_bot import DelegatorBot
from scripts.utils.logging import logging


logger = logging.getLogger(__name__)

def main():
    logger.info({'msg': 'Start up metrics service on port: 8080.'})
    start_http_server(8080)

    delegator_bot = DelegatorBot()
    delegator_bot.run_as_daemon()