from brownie import interface

from scripts.utils.constants import (
    STMATIC_CONTRACT_ADDRESSES
)
from scripts.utils.variables import WEB3_CHAIN_ID, ACCOUNT


StMATICInterface = interface.StMATIC(STMATIC_CONTRACT_ADDRESSES[WEB3_CHAIN_ID], owner=ACCOUNT)
