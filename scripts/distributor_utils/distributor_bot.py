import logging
import time

from brownie import web3, Wei, chain, accounts
from web3.exceptions import BlockNotFound

from scripts.utils.interfaces import (
    StMATICInterface
)

from scripts.utils.metrics import (
    ACCOUNT_BALANCE,
    GAS_FEE,
    CREATING_TRANSACTIONS,
    BUILD_INFO,
    DISTIBUTE_REWARDS_FAILURE,
    SUCCESS_DISTIBUTE_REWARDS,
)
from scripts.utils import variables
from scripts.utils.gas_strategy import GasFeeStrategy


logger = logging.getLogger(__name__)


class DistributorBot:
    NOT_ENOUGH_BALANCE_ON_ACCOUNT = 'Account balance is too low.'
    GAS_FEE_HIGHER_THAN_RECOMMENDED = 'Gas fee is higher than recommended fee.'
    StMATIC_CONTRACT_HAS_NOT_ENOUGH_BUFFERED_MATIC = 'StMATIC contract has not enough buffered MATIC.'
    
    def __init__(self):
        logger.info({'msg': 'Initialize DistributorBot.'})
        self.gas_fee_strategy = GasFeeStrategy(web3, blocks_count_cache=150, max_gas_fee=variables.MAX_GAS_FEE)

        # Some rarely change things
        self._load_constants()
        logger.info({'msg': 'Delegator bot initialize done'})

        BUILD_INFO.labels(
            'Delegator bot',
            variables.NETWORK,
            variables.MAX_GAS_FEE,
            variables.MAX_BUFFERED_MATICS,
            variables.CONTRACT_GAS_LIMIT,
            variables.GAS_FEE_PERCENTILE_1,
            variables.GAS_FEE_PERCENTILE_DAYS_HISTORY_1,
            variables.GAS_FEE_PERCENTILE_2,
            variables.GAS_FEE_PERCENTILE_DAYS_HISTORY_2,
            variables.GAS_PRIORITY_FEE_PERCENTILE,
            variables.MIN_PRIORITY_FEE,
            variables.MAX_PRIORITY_FEE,
            variables.ACCOUNT.address if variables.ACCOUNT else '0x0',
            variables.CREATE_TRANSACTIONS
        )

    def _load_constants(self):
        if variables.CREATE_TRANSACTIONS:
            CREATING_TRANSACTIONS.labels('deposit').set(1)
        else:
            CREATING_TRANSACTIONS.labels('deposit').set(0)

    # ------------ CYCLE STAFF -------------------
    def run_as_daemon(self):
        """Super-Mega infinity cycle!"""
        while True:
            self.run_cycle()
            logger.info({'msg': 'Sleep for 15 minute.'})
            time.sleep(60*15)

    def run_cycle(self):
        """
        Fetch latest signs from
        """
        logger.info({'msg': 'New distribute rewards cycle.'})
        self._update_state()

        # Pause message instantly if we receive pause message
        distribute_rewards_issues = self.get_distribute_rewards_issues()

        if not distribute_rewards_issues:
            logger.info({'msg': 'Distribute Rewards.'})
            return self.do_distribution()

        logger.info({'msg': f'Issues found.', 'value': distribute_rewards_issues})

        long_issues = [
            self.NOT_ENOUGH_BALANCE_ON_ACCOUNT,
            self.GAS_FEE_HIGHER_THAN_RECOMMENDED,
            self.StMATIC_CONTRACT_HAS_NOT_ENOUGH_BUFFERED_MATIC
        ]

        for long_issue in long_issues:
            if long_issue in distribute_rewards_issues:
                logger.info({'msg': f'Long issue found. Sleep for 1 minute.', 'value': long_issue})
                time.sleep(60)
                break

    def _update_state(self):
        self._current_block = web3.eth.get_block('latest')
        logger.info({'msg': f'Fetch `latest` block.', 'value': self._current_block.number})


    # # ------------- FIND ISSUES -------------------
    def get_distribute_rewards_issues(self):
        """Do a lot of checks and send all things why distribute rewards could not be done"""
        
        distribute_rewards_issues = []
        if variables.ACCOUNT:
            balance = web3.eth.get_balance(variables.ACCOUNT.address)
            ACCOUNT_BALANCE.set(balance)
            if balance < Wei('0.05 ether'):
                logger.warning({'msg': self.NOT_ENOUGH_BALANCE_ON_ACCOUNT, 'value': balance})
                distribute_rewards_issues.append(self.NOT_ENOUGH_BALANCE_ON_ACCOUNT)

            else:
                logger.info({'msg': 'Check account balance.', 'value': balance})

        else:
            ACCOUNT_BALANCE.set(0)
            logger.info({'msg': 'Check account balance. No account provided.'})

        current_gas_fee = web3.eth.get_block('pending').baseFeePerGas

        # Gas price check
        recommended_gas_fee = self.gas_fee_strategy.get_recommended_gas_fee((
            (variables.GAS_FEE_PERCENTILE_DAYS_HISTORY_1, variables.GAS_FEE_PERCENTILE_1),
            (variables.GAS_FEE_PERCENTILE_DAYS_HISTORY_2, variables.GAS_FEE_PERCENTILE_2),
        ), force = False)

        GAS_FEE.labels('max_fee').set(variables.MAX_GAS_FEE)
        GAS_FEE.labels('current_fee').set(current_gas_fee)
        GAS_FEE.labels('recommended_fee').set(recommended_gas_fee)

        logger.info({'msg': 'Fetch gas fees.', 'values': {
            'max_fee': variables.MAX_GAS_FEE,
            'current_fee': current_gas_fee,
            'recommended_fee': recommended_gas_fee,
        }})

        if current_gas_fee < recommended_gas_fee:
            logger.warning({
                'msg': self.GAS_FEE_HIGHER_THAN_RECOMMENDED,
                'values': {
                    'max_fee': variables.MAX_GAS_FEE,
                    'current_fee': current_gas_fee,
                    'recommended_fee': recommended_gas_fee
                }
            })
            distribute_rewards_issues.append(self.GAS_FEE_HIGHER_THAN_RECOMMENDED)

        return distribute_rewards_issues


    def do_distribution(self):
        """Distribute Rewards"""
        logger.info({'msg': 'No issues found. Try to distribute rewards.'})

        if not variables.ACCOUNT:
            logger.info({'msg': 'Account was not provided.'})
            return

        if not variables.CREATE_TRANSACTIONS:
            logger.info({'msg': 'Run in dry mode.'})
            return

        logger.info({'msg': 'Creating tx in blockchain.'})
        
        try:
            # Distribute Rewards
            StMATICInterface.distributeRewards()

            # Make sure it works locally
            logger.info({'msg': 'Transaction call is success.'})

        except Exception as error:
            logger.error({'msg': f'Distribute Rewards failed.', 'error': str(error)})
            DISTIBUTE_REWARDS_FAILURE.inc()
        else:
            SUCCESS_DISTIBUTE_REWARDS.inc()

        logger.info({'msg': f'Distribute Rewards method end. Sleep for 24 Hours.'})
        time.sleep(variables.DISTRIBUTE_CYCLE)

