class ExceptionNoEnoughRewards(Exception):
    """Exception raised when there are no enough rewards to distribute"""

class ExceptionRecoverTimestamp(Exception):
    """Exception raised when can not recover the distribute reward timestamp"""

class ExceptionGetNodeOperators(Exception):
    """Exception raised when can not fetch the node operators"""
