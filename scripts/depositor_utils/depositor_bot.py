from ast import For
import logging
from re import A
import time

from brownie import web3, Wei, chain, accounts
from web3.exceptions import BlockNotFound

from scripts.utils.interfaces import (
    StMATICInterface,
    ERC20Interface,
    NodeOperatorRegistryInterface,
    get_interface
)

from scripts.utils.metrics import (
    ACCOUNT_BALANCE,
    GAS_FEE,
    BUFFERED_MATIC,
    CREATING_TRANSACTIONS,
    BUILD_INFO,
    DELEGATE_FAILURE,
    SUCCESS_DELEGATE,
    DISTIBUTE_REWARDS_FAILURE,
    SUCCESS_DISTIBUTE_REWARDS,
    REQUIRED_BUFFERED_MATIC,
    REQUIRED_REWARDS_MATIC,
    REWARDS_MATIC
)
from scripts.utils import variables
from scripts.utils.gas_strategy import GasFeeStrategy


logger = logging.getLogger(__name__)


class DepositorBot:
    NOT_ENOUGH_BALANCE_ON_ACCOUNT = 'Account balance is too low.'
    GAS_FEE_HIGHER_THAN_RECOMMENDED = 'Gas fee is higher than recommended fee.'
    StMATIC_CONTRACT_HAS_NOT_ENOUGH_BUFFERED_MATIC = 'StMATIC contract has not enough buffered MATIC.'
    StMATIC_CONTRACT_HAS_NOT_ENOUGH_REWARDS = 'StMATIC contract has not enough rewards to distribute.'

    def __init__(self):
        logger.info({'msg': 'Initialize DepositorBot.'})
        self.gas_fee_strategy = GasFeeStrategy(
            web3, blocks_count_cache=150, max_gas_fee=variables.MAX_GAS_FEE)

        # Some rarely change things
        self._load_constants()
        logger.info({'msg': 'Depositor bot initialize done'})

        BUILD_INFO.labels(
            'Depositor bot',
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
            CREATING_TRANSACTIONS.labels('delegate').set(1)
        else:
            CREATING_TRANSACTIONS.labels('delegate').set(0)

    # ------------ CYCLE STAFF -------------------
    def run_as_daemon(self):
        """Super-Mega infinity cycle!"""
        while True:
            self.run_cycle()

    def run_cycle(self):
        self.run_distribute_rewards_cycle()
        logger.info({'msg': f'Distribute rewards method end.'})

        self.run_delegate_cycle()
        logger.info({'msg': f'Delegate method end.'})

        logger.info({'msg': f'Sleep for {variables.CYCLE} seconds.'})
        time.sleep(variables.CYCLE)

    def run_delegate_cycle(self):
        """
        Fetch latest signs from
        """
        logger.info({'msg': 'New delegate cycle.'})
        self._update_state()

        # Pause message instantly if we receive pause message
        delegate_issues = self.get_delegate_issues()

        if not delegate_issues:
            logger.info({'msg': 'Start delegate.'})
            return self.do_delegate()

        logger.info({'msg': f'Issues found.', 'value': delegate_issues})

        long_issues = [
            self.NOT_ENOUGH_BALANCE_ON_ACCOUNT,
            self.GAS_FEE_HIGHER_THAN_RECOMMENDED,
            self.StMATIC_CONTRACT_HAS_NOT_ENOUGH_BUFFERED_MATIC
        ]

        for long_issue in long_issues:
            if long_issue in delegate_issues:
                logger.info({'msg': f'Long issue found.', 'value': long_issue})
                break

    def _update_state(self):
        self._current_block = web3.eth.get_block('latest')
        logger.info({'msg': f'Fetch `latest` block.',
                    'value': self._current_block.number})

    def run_distribute_rewards_cycle(self):
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

        logger.info({'msg': f'Issues found.',
                    'value': distribute_rewards_issues})

        long_issues = [
            self.NOT_ENOUGH_BALANCE_ON_ACCOUNT,
            self.GAS_FEE_HIGHER_THAN_RECOMMENDED,
            self.StMATIC_CONTRACT_HAS_NOT_ENOUGH_BUFFERED_MATIC
        ]

        for long_issue in long_issues:
            if long_issue in distribute_rewards_issues:
                logger.info(
                    {'msg': f'Long issue found. Sleep for 1 minute.', 'value': long_issue})
                time.sleep(60)
                break

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
            logger.error(
                {'msg': f'Distribute Rewards failed.', 'error': str(error)})
            DISTIBUTE_REWARDS_FAILURE.inc()
        else:
            SUCCESS_DISTIBUTE_REWARDS.inc()

    def do_delegate(self):
        """Delegate"""
        logger.info({'msg': 'No issues found. Try to delegate.'})

        if not variables.ACCOUNT:
            logger.info({'msg': 'Account was not provided.'})
            return

        if not variables.CREATE_TRANSACTIONS:
            logger.info({'msg': 'Run in dry mode.'})
            return

        logger.info({'msg': 'Creating tx in blockchain.'})

        try:
            # Delegate
            StMATICInterface.delegate()

            # Make sure it works locally
            logger.info({'msg': 'Transaction call is success.'})

        except Exception as error:
            logger.error({'msg': f'Delegate failed.', 'error': str(error)})
            DELEGATE_FAILURE.inc()
        else:
            pass
            SUCCESS_DELEGATE.inc()

    def get_delegate_issues(self):
        """Do a lot of checks and send all things why delegate could not be done"""
        delegate_issues = []
        if variables.ACCOUNT:
            balance = web3.eth.get_balance(variables.ACCOUNT.address)
            ACCOUNT_BALANCE.set(balance)
            if balance < Wei('0.05 ether'):
                logger.warning(
                    {'msg': self.NOT_ENOUGH_BALANCE_ON_ACCOUNT, 'value': balance})
                delegate_issues.append(self.NOT_ENOUGH_BALANCE_ON_ACCOUNT)

            else:
                logger.info(
                    {'msg': 'Check account balance.', 'value': balance})

        else:
            ACCOUNT_BALANCE.set(0)
            logger.info({'msg': 'Check account balance. No account provided.'})

        current_gas_fee = web3.eth.get_block('pending').baseFeePerGas

        # Check buffered Matics
        total_buffered = StMATICInterface.totalBuffered()
        delegation_lower_bound = StMATICInterface.delegationLowerBound()

        logger.info({'msg': 'Call `totalBuffered()`.', 'value': {
            'total_buffered': total_buffered,
            'delegation_lower_bound': delegation_lower_bound,
        }})

        BUFFERED_MATIC.set(total_buffered)
        REQUIRED_BUFFERED_MATIC.set(delegation_lower_bound)

        if total_buffered < delegation_lower_bound:
            logger.warning(
                {'msg': self.StMATIC_CONTRACT_HAS_NOT_ENOUGH_BUFFERED_MATIC, 'value': total_buffered})
            delegate_issues.append(
                self.StMATIC_CONTRACT_HAS_NOT_ENOUGH_BUFFERED_MATIC)

        # Gas price check
        recommended_gas_fee = self.gas_fee_strategy.get_recommended_gas_fee((
            (variables.GAS_FEE_PERCENTILE_DAYS_HISTORY_1,
             variables.GAS_FEE_PERCENTILE_1),
            (variables.GAS_FEE_PERCENTILE_DAYS_HISTORY_2,
             variables.GAS_FEE_PERCENTILE_2),
        ), force=False)

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
                    'recommended_fee': recommended_gas_fee,
                    'total_buffered': total_buffered,
                }
            })
            delegate_issues.append(self.GAS_FEE_HIGHER_THAN_RECOMMENDED)

        return delegate_issues

    def get_distribute_rewards_issues(self):
        """Do a lot of checks and send all things why distribute rewards could not be done"""

        distribute_rewards_issues = []
        if variables.ACCOUNT:
            balance = web3.eth.get_balance(variables.ACCOUNT.address)
            ACCOUNT_BALANCE.set(balance)
            if balance < Wei('0.05 ether'):
                logger.warning(
                    {'msg': self.NOT_ENOUGH_BALANCE_ON_ACCOUNT, 'value': balance})
                distribute_rewards_issues.append(
                    self.NOT_ENOUGH_BALANCE_ON_ACCOUNT)

            else:
                logger.info(
                    {'msg': 'Check account balance.', 'value': balance})

        else:
            ACCOUNT_BALANCE.set(0)
            logger.info({'msg': 'Check account balance. No account provided.'})

        current_gas_fee = web3.eth.get_block('pending').baseFeePerGas

        # calculate rewards
        total_rewards, reward_distribution_lower_bound = self._calculate_rewards()

        REWARDS_MATIC.set(total_rewards)
        REQUIRED_REWARDS_MATIC.set(reward_distribution_lower_bound)

        if total_rewards <= reward_distribution_lower_bound:
            logger.warning({
                'msg': self.StMATIC_CONTRACT_HAS_NOT_ENOUGH_REWARDS,

                'values': {
                    'total_rewards': total_rewards,
                    'reward_distribution_lower_bound': reward_distribution_lower_bound,
                }
            })
            distribute_rewards_issues.append(
                self.StMATIC_CONTRACT_HAS_NOT_ENOUGH_REWARDS)

        # Gas price check
        recommended_gas_fee = self.gas_fee_strategy.get_recommended_gas_fee((
            (variables.GAS_FEE_PERCENTILE_DAYS_HISTORY_1,
             variables.GAS_FEE_PERCENTILE_1),
            (variables.GAS_FEE_PERCENTILE_DAYS_HISTORY_2,
             variables.GAS_FEE_PERCENTILE_2),
        ), force=False)

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
            distribute_rewards_issues.append(
                self.GAS_FEE_HIGHER_THAN_RECOMMENDED)

        return distribute_rewards_issues

    def _calculate_rewards(self):
        res = NodeOperatorRegistryInterface.getOperatorInfos(True, False)
        accumulatedRewards = 0
        for r in res:
            validator_share = get_interface(r[1])
            reward = validator_share.getLiquidRewards(StMATICInterface.address)
            if reward >= validator_share.minAmount():
                accumulatedRewards += reward

        reward_distribution_lower_bound = StMATICInterface.rewardDistributionLowerBound()
        total_buffered = StMATICInterface.totalBuffered()
        balance_of = ERC20Interface.balanceOf(StMATICInterface.address)
        total_rewards = (balance_of - total_buffered) + accumulatedRewards

        logger.info({'msg': 'Rewards.', 'value': {
            'reward_distribution_lower_bound': reward_distribution_lower_bound,
            'total_buffered': total_buffered,
            'balance_of': balance_of,
            'total_rewards': total_rewards
        }})
        return total_rewards, reward_distribution_lower_bound
