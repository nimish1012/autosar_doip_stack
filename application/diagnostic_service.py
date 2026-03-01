from abc import ABC, abstractmethod
from common.logger import setup_logger

logger = setup_logger(__name__)

class DiagnosticService(ABC):
    """
    DiagnosticService Abstract Base Class.

    Responsibilities of the Application Layer:
    - Highest level of the stack.
    - Implements the actual diagnostic logic and service routines.
    - Interacts with the Diagnostic layer to process or provide payloads.
    - Does not care about network protocols (DoIP, TCP).
    """

    @abstractmethod
    def process_request(self, payload: bytes) -> bytes:
        """
        Process an incoming diagnostic request payload.

        :param payload: The raw diagnostic request payload.
        :return: The diagnostic response payload.
        """
        pass
