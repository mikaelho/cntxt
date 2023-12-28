from enum import IntEnum

from cntxt import stack


class LogLevel(IntEnum):
    DEBUG = 1
    INFO = 2
    WARNING = 3
    ERROR = 4


def log(level: LogLevel, message: str):
    """Simple fake logger for demonstration purposes."""
    if stack.log_level and stack.log_level > level:
        return
    print(message)
