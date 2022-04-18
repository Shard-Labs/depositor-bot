import logging
import os

from brownie import Wei, web3, accounts


logger = logging.getLogger(__name__)


NETWORK = os.getenv('NETWORK')
VERSION = '1.1.0'

# Transaction limits
MAX_GAS_FEE = Wei(os.getenv('MAX_GAS_FEE', '100 gwei'))
DISTRIBUTE_REWARDS_MAX_GAS_FEE = Wei(os.getenv('DISTRIBUTE_REWARDS_MAX_GAS_FEE', '300 gwei'))
CONTRACT_GAS_LIMIT = Wei(os.getenv('CONTRACT_GAS_LIMIT', 10 * 10**6))

# Gas fee percentile
GAS_FEE_PERCENTILE_1: int = int(os.getenv('GAS_FEE_PERCENTILE_1', 50))
GAS_FEE_PERCENTILE_DAYS_HISTORY_1: int = int(
    os.getenv('GAS_FEE_PERCENTILE_DAYS_HISTORY_1', 1))

GAS_FEE_PERCENTILE_2: int = int(os.getenv('GAS_FEE_PERCENTILE_2', 50))
GAS_FEE_PERCENTILE_DAYS_HISTORY_2: int = int(
    os.getenv('GAS_FEE_PERCENTILE_DAYS_HISTORY_2', 2))

GAS_PRIORITY_FEE_PERCENTILE = int(os.getenv('GAS_PRIORITY_FEE_PERCENTILE', 55))

MIN_PRIORITY_FEE = Wei(os.getenv('MIN_PRIORITY_FEE', '2 gwei'))
MAX_PRIORITY_FEE = Wei(os.getenv('MAX_PRIORITY_FEE', '10 gwei'))

WEB3_CHAIN_ID = web3.eth.chain_id
CREATE_TRANSACTIONS = os.getenv('CREATE_TRANSACTIONS') == 'true'
CYCLE = int(os.getenv('CYCLE', 86400))
MIN_RATIO = int(os.getenv('MIN_RATIO', 1))
MAX_RATIO = int(os.getenv('MAX_RATIO', 3))

PRIORITY_FEE = Wei(os.getenv('PRIORITY_FEE', '0 gwei'))

# Account private key
WALLET_PRIVATE_KEY = os.getenv('WALLET_PRIVATE_KEY', None)

if WALLET_PRIVATE_KEY:
    ACCOUNT = accounts.add(WALLET_PRIVATE_KEY)
    logger.info({'msg': 'Load account from private key.',
                'value': ACCOUNT.address})
else:
    ACCOUNT = None
    logger.warning({'msg': 'Account not provided. Run in dry mode.'})
