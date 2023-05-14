import logging
import time
from brownie import web3, Wei, chain
import requests
from scripts.utils.interfaces import (
    StMATICInterface,
    ERC20Interface,
    NodeOperatorRegistryInterface,
    get_interface
)

from scripts.depositor_utils.errors import (
    ExceptionNoEnoughRewards,
    ExceptionRecoverTimestamp,
    ExceptionGetNodeOperators
)

from scripts.utils.metrics import (
    GAS_FEE,
    CREATING_TRANSACTIONS,
    BUILD_INFO,
    DELEGATE_FAILURE,
    SUCCESS_DELEGATE,
    DISTIBUTE_REWARDS_FAILURE,
    SUCCESS_DISTIBUTE_REWARDS,
)
from scripts.utils import variables
from scripts.utils.gas_strategy import GasFeeStrategy


logger = logging.getLogger(__name__)


class DepositorBot:
    NOT_ENOUGH_BALANCE_ON_ACCOUNT = 'Account balance is too low.'
    GAS_FEE_HIGHER_THAN_RECOMMENDED = 'Gas fee is higher than recommended fee.'
    StMATIC_CONTRACT_HAS_NOT_ENOUGH_BUFFERED_MATIC = 'StMATIC contract has not enough buffered MATIC.'
    StMATIC_CONTRACT_HAS_NOT_ENOUGH_REWARDS = 'StMATIC contract has not enough rewards to distribute.'
    last_delegate_time = 0
    last_distribution_time = None
    node_operators = []
    success_wait = 600
    fail_wait = 300
    distribute_rewards_wait = 180
    last_cycle = time.time()

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
        self.recover_last_distribution_timestamp()
        self.get_node_operators()

        while True:
            try:
                for _ in chain.new_blocks():
                    self.run_cycle()
                    logger.info({'msg': 'Cycle sleep.', 'time': self.success_wait})
                    time.sleep(self.success_wait)
            except Exception as error:
                logger.error(
                    {'msg': 'Unexpected exception.', 'error': str(error)})
            time.sleep(10)

    def check_account_balance(self):
        if variables.ACCOUNT:
            balance = web3.eth.get_balance(variables.ACCOUNT.address)
            if balance < Wei('0.25 ether'):
                logger.warning(
                    {'msg': self.NOT_ENOUGH_BALANCE_ON_ACCOUNT, 'value': balance})
                return False
            else:
                logger.info(
                    {'msg': 'Check account balance.', 'value': balance})
                return True
        else:
            logger.info({'msg': 'Check account balance. No account provided.'})
            return False

    def run_cycle(self):
        self.last_cycle = time.time()
        if not self.check_account_balance():
            return

        if self.get_next_delegation_time() <= time.time():
            self.run_distribute_rewards_cycle()
            time.sleep(self.distribute_rewards_wait)

        logger.info(
            {'msg': f'Distribute rewards info.', 'value': {
                'Last reward distribution at': self.last_distribution_time,
                'Next reward distribution at': self.get_next_delegation_time(),
            }})

        self.run_delegate_cycle()

    def run_delegate_cycle(self):
        """
        Fetch latest signs from
        """
        logger.info({'msg': 'New delegate cycle.'})

        if not self.check_if_can_delegate():
            return

        logger.info({'msg': f'Start delegation.'})
        self.do_delegate()
        logger.info({'msg': f'Delegate method end.'})

    def check_if_can_distribute_rewards(self):
        self.check_if_bot_is_setup()

        total_rewards, reward_distribution_lower_bound = self._calculate_rewards()

        if total_rewards <= reward_distribution_lower_bound:
            logger.warning({
                'msg': self.StMATIC_CONTRACT_HAS_NOT_ENOUGH_REWARDS,

                'values': {
                    'version': variables.VERSION,
                    'total_rewards': total_rewards,
                    'reward_distribution_lower_bound': reward_distribution_lower_bound,
                }
            })
            return False
        return True

    def run_distribute_rewards_cycle(self):
        """
        Distributer rewards
        """

        if not self.check_if_can_distribute_rewards():
            logger.error({"msg": "Can not distribute rewards."})
            raise ExceptionNoEnoughRewards

        logger.info({'msg': 'Start distributing rewards.'})
        self.do_distribution()
        logger.info({'msg': 'Distribute rewards method end.'})

    def check_if_bot_is_setup(self):
        if not variables.ACCOUNT:
            logger.error({'msg': 'Account was not provided.'})
            return

    def do_distribution(self):
        """Distribute Rewards"""

        priority = variables.PRIORITY_FEE
        if (priority == 0):
            priority = self._get_deposit_priority_fee(
                variables.GAS_PRIORITY_FEE_PERCENTILE)

        logger.info({'msg': 'Tx info.', 'value': {
                    'priority_fee': priority, 'gas_limit': variables.CONTRACT_GAS_LIMIT}})

        if not variables.CREATE_TRANSACTIONS:
            logger.info({'msg': 'Run in dry mode.'})
            return

        logger.info({'msg': 'Creating tx in blockchain.'})

        try:
            # Distribute Rewards
            StMATICInterface.distributeRewards({
                'priority_fee': priority,
                'gas_limit': variables.CONTRACT_GAS_LIMIT
            })

            logger.info({'msg': 'Transaction success.'})
            self.last_distribution_time = time.time()
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

        priority = variables.PRIORITY_FEE
        if (priority == 0):
            priority = self._get_deposit_priority_fee(
                variables.GAS_PRIORITY_FEE_PERCENTILE)

        logger.info({'msg': 'Tx info.', 'value': {
            'priority_fee': priority,
            'gas_limit': variables.CONTRACT_GAS_LIMIT
        }})

        if not variables.CREATE_TRANSACTIONS:
            logger.info({'msg': 'Run in dry mode.'})
            return

        logger.info({'msg': 'Creating tx in blockchain.'})

        try:
            # Delegate
            StMATICInterface.delegate({
                'priority_fee': priority,
                'gas_limit': variables.CONTRACT_GAS_LIMIT
            })

            logger.info({'msg': 'Transaction success.'})
            self.last_delegate_time = time.time()
        except Exception as error:
            logger.error({'msg': f'Delegate failed.', 'error': str(error)})
            DELEGATE_FAILURE.inc()
        else:
            SUCCESS_DELEGATE.inc()

    def check_if_can_delegate(self):
        """Check if can delegate"""

        delegate_issues = []
        delegate_ratio = self._get_deposit_ratio()
        is_high_buffer = False

        if delegate_ratio >= variables.MAX_RATIO:
            is_high_buffer = True
        elif delegate_ratio >= variables.MIN_RATIO \
                and self.last_delegate_time + variables.CYCLE <= time.time():
            is_high_buffer = True
        else:
            logger.warning(
                {'msg': self.StMATIC_CONTRACT_HAS_NOT_ENOUGH_BUFFERED_MATIC})
            delegate_issues.append(
                self.StMATIC_CONTRACT_HAS_NOT_ENOUGH_BUFFERED_MATIC)

        # Gas price check
        current_gas_fee = web3.eth.get_block('pending').baseFeePerGas
        recommended_gas_fee = self.gas_fee_strategy.get_recommended_gas_fee((
            (variables.GAS_FEE_PERCENTILE_DAYS_HISTORY_1,
             variables.GAS_FEE_PERCENTILE_1),
            (variables.GAS_FEE_PERCENTILE_DAYS_HISTORY_2,
             variables.GAS_FEE_PERCENTILE_2),
        ), force=is_high_buffer)

        GAS_FEE.labels('max_fee').set(variables.MAX_GAS_FEE)
        GAS_FEE.labels('current_fee').set(current_gas_fee)
        GAS_FEE.labels('recommended_fee').set(recommended_gas_fee)

        logger.info({'msg': 'Fetch gas fees.', 'values': {
            'version': variables.VERSION,
            'max_fee': variables.MAX_GAS_FEE,
            'current_fee': current_gas_fee,
            'recommended_fee': recommended_gas_fee,
            'gas_fee_percentile_1': variables.GAS_FEE_PERCENTILE_1,
            'gas_fee_percentile_2': variables.GAS_FEE_PERCENTILE_2,
        }})

        if current_gas_fee > recommended_gas_fee:
            logger.warning({
                'msg': self.GAS_FEE_HIGHER_THAN_RECOMMENDED,
                'values': {
                    'version': variables.VERSION,
                    'max_fee': variables.MAX_GAS_FEE,
                    'current_fee': current_gas_fee,
                    'recommended_fee': recommended_gas_fee,
                }
            })
            delegate_issues.append(self.GAS_FEE_HIGHER_THAN_RECOMMENDED)

        if (len(delegate_issues) > 0):
            logger.info({'msg': f'Issues found.', 'value': delegate_issues})

            long_issues = [
                self.NOT_ENOUGH_BALANCE_ON_ACCOUNT,
                self.GAS_FEE_HIGHER_THAN_RECOMMENDED,
                self.StMATIC_CONTRACT_HAS_NOT_ENOUGH_BUFFERED_MATIC
            ]

            for long_issue in long_issues:
                if long_issue in delegate_issues:
                    logger.error(
                        {'msg': f'Long issue found.', 'value': long_issue})
                    break
            return False

        return True

    def _calculate_rewards(self):
        try:
            rewards_accumulated_in_validators = 0
            for idx, node_operator in enumerate(self.node_operators):
                validator_share_address = node_operator[idx][2]
                validator_share = get_interface(validator_share_address)

                reward = validator_share.getLiquidRewards(
                    StMATICInterface.address)
                if reward >= validator_share.minAmount():
                    rewards_accumulated_in_validators += reward

            reward_distribution_lower_bound = StMATICInterface.rewardDistributionLowerBound()
            total_buffered = StMATICInterface.totalBuffered()
            balance_of = ERC20Interface.balanceOf(StMATICInterface.address)
            total_rewards = (balance_of - total_buffered) + \
                rewards_accumulated_in_validators

            logger.info({'msg': 'Rewards.', 'value': {
                'reward_distribution_lower_bound': reward_distribution_lower_bound,
                'rewards_accumulated_in_validators': rewards_accumulated_in_validators,
                'total_buffered': total_buffered,
                'balance_of': balance_of,
                'total_rewards': total_rewards
            }})
            return total_rewards, reward_distribution_lower_bound
        except Exception as error:
            logger.error(
                {'msg': 'Error to calculate rewards.', 'value': error})

    @staticmethod
    def _get_deposit_priority_fee(percentile):
        return min(
            max(
                web3.eth.fee_history(1, 'latest', reward_percentiles=[
                                     percentile])['reward'][0][0],
                variables.MIN_PRIORITY_FEE,
            ),
            variables.MAX_PRIORITY_FEE,
        )

    def _get_deposit_ratio(self):
        try:
            total_buffered = StMATICInterface.totalBuffered()
            reserved_funds = StMATICInterface.reservedFunds()
            delegation_lower_bound = StMATICInterface.delegationLowerBound()
            total_delegated = StMATICInterface.getTotalStakeAcrossAllValidators()
            delegate_ratio = (total_buffered - reserved_funds) * \
                100 / total_delegated

            logger.info({'msg': 'Call `totalBuffered()`.', 'value': {
                'version': variables.VERSION,
                'total_buffered': total_buffered,
                'reserved_funds': reserved_funds,
                'delegation_lower_bound': delegation_lower_bound,
                'total_delegated': total_delegated,
                'delegate_ratio': delegate_ratio,
                'last_delegation_time': self.last_delegate_time,
            }})
            return delegate_ratio
        except Exception as error:
            logger.error(
                {'msg': 'Error to calculate delegation.', 'value': error})
            return 0

    def recover_last_distribution_timestamp(self):
        block_number = web3.eth.get_block_number()

        logger.info({'msg': "Start recovering the distribute rewards time.", "value":
                    {"last_distribution_time": self.last_distribution_time}})

        if (not self.last_distribution_time):
            try:
                url = f'https://api.etherscan.io/api?module=account&action=txlist&address={variables.ACCOUNT}&startblock={(block_number - 6000)}&endblock={block_number}&page=1&offset=10&sort=asc&apikey={variables.ETHERSCAN_API_KEY}'
                txs = (requests.get(url)).json()

                for tx in txs["result"]:
                    if tx["functionName"] == "distributeRewards()":
                        self.last_distribution_time = int(tx["timeStamp"])
                        break

                if self.last_distribution_time == None:
                    self.last_distribution_time = time.time() - variables.CYCLE - 1

                logger.info({'msg': "Distribute rewards time recovered", "value": {
                            "last_distribution_time": self.last_distribution_time}})
            except Exception as err:
                logger.error(
                    {'msg': "Error to recover the timestamp", "value": {err}})
                raise ExceptionRecoverTimestamp

    def get_node_operators(self):
        try:
            validator_ids = NodeOperatorRegistryInterface.getValidatorIds()
            logger.info({'msg': "validator ids", "value": {
                        "validator_ids": validator_ids}})

            for validator_id in validator_ids:
                self.node_operators.append(
                    NodeOperatorRegistryInterface.getNodeOperator["uint256"](validator_id))
            logger.info({'msg': "Node Operators fetched successfully"})

        except Exception as err:
            logger.error(
                {'msg': "Error to fetch the the list of node operators", "value": {err}})
            raise ExceptionGetNodeOperators

    def get_next_delegation_time(self):
        return self.last_distribution_time + variables.CYCLE

    def is_health(self):
        return time.time() < self.last_cycle + self.success_wait * 2
