from prometheus_client.metrics import Gauge, Counter


DEPOSITOR_PREFIX = 'lido_on_polygon_bot'

BUILD_INFO = Gauge(f'{DEPOSITOR_PREFIX}build_info', 'Build info', [
    'name',
    'network',
    'max_gas_fee',
    'contract_gas_limit',
    'gas_fee_percentile_1',
    'gas_fee_percentile_days_history_1',
    'gas_fee_percentile_2',
    'gas_fee_percentile_days_history_2',
    'gas_priority_fee_percentile',
    'min_priority_fee',
    'max_priority_fee',
    'account_address',
    'create_transactions'
])

GAS_FEE = Gauge(f'{DEPOSITOR_PREFIX}gas_fee', 'Gas fee', ['type'])

DELEGATE_FAILURE = Counter(
    f'{DEPOSITOR_PREFIX}delegate_failure', 'Delegate failure')
SUCCESS_DELEGATE = Counter(
    f'{DEPOSITOR_PREFIX}delegate_success', 'Delegate done')

DISTIBUTE_REWARDS_FAILURE = Counter(
    f'{DEPOSITOR_PREFIX}distribute_rewards_failure', 'Distribute rewards failure')
SUCCESS_DISTIBUTE_REWARDS = Counter(
    f'{DEPOSITOR_PREFIX}distribute_rewards_success', 'Distribute rewards done')

ACCOUNT_BALANCE = Gauge(
    f'{DEPOSITOR_PREFIX}account_balance', 'Account balance')

CREATING_TRANSACTIONS = Gauge(
    f'{DEPOSITOR_PREFIX}creating_transactions', 'Creating transactions', ['bot'])
