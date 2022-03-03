from enum import IntEnum


class Network(IntEnum):
    Mainnet = 1
    Görli = 5


STMATIC_CONTRACT_ADDRESSES = {
    Network.Mainnet: "0x9ee91F9f426fA633d227f7a9b000E28b9dfd8599",
    Network.Görli: "0x9A7c69A167160C507602ecB3Df4911e8E98e1279",
}
DEPOSIT_CONTRACT_DEPLOY_BLOCK = {
    Network.Mainnet: 11052984,
    Network.Görli: 3085928,
}

# 100 blocks is safe enough
UNREORGABLE_DISTANCE = 100
# reasonably high number (nb. if there is > 10000 deposit events infura will throw error)
EVENT_QUERY_STEP = 1000
