import logging
import time
from tests.fixtures.pytest_fixtures import *
from tests.utils.logs import find_log_message
import pytest
from scripts.depositor_utils.errors import (
    ExceptionNoEnoughRewards
)

ISSUES_FOUND_LOG = 'Issues found.'
START_DISTRIBUTE_REWARDS_LOG = 'Start distributing rewards.'
ERROR_DISTRIBUTE_REWARDS_LOG = 'Can not distribute rewards.'
START_DELEGATE_LOG = 'Start delegation.'
ISSUES_NOT_FOUND_DELEGATE_LOG = 'No issues found. Try to delegate.'
LOW_ACCOUNT_BALANCE = 'Account balance is too low.'


def test_distribute_rewards_no_create_tx(
    caplog,
    setup_web3_fixtures_distribute_rewards,
    depositor_bot,
    setup_account,
    setup_no_create_txs
):
    caplog.set_level(logging.INFO)
    depositor_bot.run_distribute_rewards_cycle()
    assert not find_log_message(caplog, ISSUES_FOUND_LOG)
    assert find_log_message(caplog, START_DISTRIBUTE_REWARDS_LOG)
    assert find_log_message(caplog, 'Run in dry mode.')
    assert not find_log_message(caplog, 'Creating tx in blockchain.')


def test_delegate_no_create_tx(
    caplog,
    setup_web3_fixtures_delegate,
    depositor_bot,
    setup_account,
    setup_no_create_txs
):
    caplog.set_level(logging.INFO)
    depositor_bot.run_delegate_cycle()
    assert not find_log_message(caplog, ISSUES_FOUND_LOG)
    assert find_log_message(caplog, ISSUES_NOT_FOUND_DELEGATE_LOG)
    assert find_log_message(caplog, 'Run in dry mode.')
    assert not find_log_message(caplog, 'Creating tx in blockchain.')

def test_delegate_max_priority(
    caplog,
    setup_web3_fixtures_delegate,
    depositor_bot,
    setup_account,
    setup_no_create_txs
):
    caplog.set_level(logging.INFO)
    depositor_bot.run_delegate_cycle()
    assert not find_log_message(caplog, ISSUES_FOUND_LOG)
    assert find_log_message(caplog, ISSUES_NOT_FOUND_DELEGATE_LOG)
    assert find_log_message(caplog, 'Run in dry mode.')
    assert not find_log_message(caplog, 'Creating tx in blockchain.')

def test_delegate_range_no_create_tx(
    caplog,
    setup_web3_fixtures_delegate_in_range,
    depositor_bot,
    setup_account,
    setup_no_create_txs
):
    caplog.set_level(logging.INFO)
    depositor_bot.run_delegate_cycle()
    assert not find_log_message(caplog, ISSUES_FOUND_LOG)
    assert find_log_message(caplog, ISSUES_NOT_FOUND_DELEGATE_LOG)
    assert find_log_message(caplog, 'Run in dry mode.')
    assert not find_log_message(caplog, 'Creating tx in blockchain.')


def test_account_balance(
    caplog,
    setup_web3_deposit_fixtures_small_balance,
    depositor_bot,
    setup_account
):
    caplog.set_level(logging.INFO)
    depositor_bot.check_account_balance()
    assert find_log_message(
        caplog, depositor_bot.NOT_ENOUGH_BALANCE_ON_ACCOUNT)
    record = find_log_message(caplog, LOW_ACCOUNT_BALANCE)
    assert record
    assert record.msg['msg'] == depositor_bot.NOT_ENOUGH_BALANCE_ON_ACCOUNT


def test_deposit_issues__gas_strategy(
        caplog,
        setup_web3_deposit_fixtures_with_high_gas,
        depositor_bot,
        setup_account,
        remove_sleep
):
    caplog.set_level(logging.INFO)
    depositor_bot.run_delegate_cycle()

    assert find_log_message(
        caplog, depositor_bot.GAS_FEE_HIGHER_THAN_RECOMMENDED)
    record = find_log_message(caplog, ISSUES_FOUND_LOG)
    assert record
    assert record.msg['value'] == [
        depositor_bot.GAS_FEE_HIGHER_THAN_RECOMMENDED]


def test_delegate_issues__buffered_matics_no_delegate(
    caplog,
    setup_web3_deposit_fixtures_not_enough_buffered_matic,
    depositor_bot,
    setup_account
):
    caplog.set_level(logging.INFO)
    depositor_bot.LAST_DELEGATE_TIME = time.time()
    depositor_bot.run_delegate_cycle()

    assert find_log_message(
        caplog, depositor_bot.StMATIC_CONTRACT_HAS_NOT_ENOUGH_BUFFERED_MATIC)
    record = find_log_message(caplog, ISSUES_FOUND_LOG)
    assert record
    assert record.msg['value'] == [
        depositor_bot.StMATIC_CONTRACT_HAS_NOT_ENOUGH_BUFFERED_MATIC]

def test_delegate_issues__buffered_matics(
    caplog,
    setup_web3_fixtures_delegate_out_range,
    depositor_bot,
    setup_account
):
    caplog.set_level(logging.INFO)
    depositor_bot.run_delegate_cycle()

    assert find_log_message(
        caplog, depositor_bot.StMATIC_CONTRACT_HAS_NOT_ENOUGH_BUFFERED_MATIC)
    record = find_log_message(caplog, ISSUES_FOUND_LOG)
    assert record
    assert record.msg['value'] == [
        depositor_bot.StMATIC_CONTRACT_HAS_NOT_ENOUGH_BUFFERED_MATIC]

def test_distribute_rewards_issues__not_enough_rewards(
    caplog,
    setup_web3_deposit_fixtures_not_enough_rewards,
    depositor_bot,
    setup_account
):
    caplog.set_level(logging.INFO)
    with pytest.raises(ExceptionNoEnoughRewards):
        depositor_bot.run_distribute_rewards_cycle()


def test_delegate__sucess(
    caplog,
    setup_web3_fixtures_delegate,
    depositor_bot,
    setup_account,
    setup_create_txs
):
    caplog.set_level(logging.INFO)
    depositor_bot.run_delegate_cycle()

    assert not find_log_message(caplog, ISSUES_FOUND_LOG)
    assert find_log_message(caplog, ISSUES_NOT_FOUND_DELEGATE_LOG)
    assert find_log_message(caplog, 'Creating tx in blockchain.')


def test_distribute_rewards__sucess(
    caplog,
    setup_web3_fixtures_distribute_rewards,
    depositor_bot,
    setup_account,
    setup_create_txs
):
    caplog.set_level(logging.INFO)
    depositor_bot.run_distribute_rewards_cycle()

    assert not find_log_message(caplog, ISSUES_FOUND_LOG)
    assert find_log_message(caplog, START_DISTRIBUTE_REWARDS_LOG)
    assert find_log_message(caplog, 'Creating tx in blockchain.')

def test_distribute_rewards__sucess(
    caplog,
    setup_web3_fixtures_distribute_rewards,
    depositor_bot,
    setup_account,
    setup_create_txs
):
    caplog.set_level(logging.INFO)
    depositor_bot.run_distribute_rewards_cycle()

    assert not find_log_message(caplog, ISSUES_FOUND_LOG)
    assert find_log_message(caplog, START_DISTRIBUTE_REWARDS_LOG)
    assert find_log_message(caplog, 'Creating tx in blockchain.')

def test_depositor_bot_priority_fee(
    setup_web3_deposit_fixtures,
    depositor_bot,
):
    priority_fee = depositor_bot._get_deposit_priority_fee(0)
    assert 10 * 10**9 >= priority_fee >= 2 * 10**9

    priority_fee = depositor_bot._get_deposit_priority_fee(55)
    assert 10 * 10**9 >= priority_fee >= 2 * 10**9

    priority_fee = depositor_bot._get_deposit_priority_fee(100)
    assert 10 * 10**9 >= priority_fee >= 2 * 10**9