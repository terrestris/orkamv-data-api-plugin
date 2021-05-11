from enum import Enum
from typing import Optional


class ErrorReason(Enum):
    ERROR = 'ERROR'
    TIMEOUT = 'TIMEOUT'
    BBOX_TOO_BIG = 'BBOX_TOO_BIG'
    BBOX_INVALID = 'BBOX_INVALID'
    NO_THREADS_AVAILABLE = 'NO_THREADS_AVAILABLE'


class TaskStatus(Enum):
    STARTED = 1
    CANCELLED = 2
    COMPLETED = 3


class OrkamvApiException(Exception):
    def __init__(self, reason: ErrorReason):
        self.reason = reason
        super().__init__(self, str(reason))
