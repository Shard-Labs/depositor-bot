# from prometheus_client import start_http_server
import threading
import os
from flask import Flask

from scripts.depositor_utils.depositor_bot import DepositorBot
from scripts.utils.logging import logging

app = Flask(__name__)

logger = logging.getLogger(__name__)

delegator_bot = DepositorBot()


@app.route('/healthcheck')
def health():
    if delegator_bot.is_health():
        return {"status": "ok"}, 200
    
    delegator_bot.inc_retry()
    if (delegator_bot.retry > 3):
        os._exit(1)
    return {"status": "error"}, 500


def main():
    # health check
    logger.info({'msg': 'Start up health service on port: 8080.'})
    host = '0.0.0.0'
    port = 8080
    t = threading.Thread(target=app.run, args=(host, port))
    t.setDaemon(True)
    t.start()

    # depositor bot
    delegator_bot.run_as_daemon()
