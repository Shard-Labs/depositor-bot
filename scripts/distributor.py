# from brownie import web3
from prometheus_client import start_http_server

from scripts.distributor_utils.distributor_bot import DistributorBot
from scripts.utils.logging import logging


logger = logging.getLogger(__name__)

def main():
    logger.info({'msg': 'Start up metrics service on port: 8080.'})
    start_http_server(8080)

    distributor_bot = DistributorBot()
    distributor_bot.run_as_daemon()