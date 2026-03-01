from abc import ABC, abstractmethod
from common.logger import setup_logger

logger = setup_logger(__name__)

class DoIPTransport(ABC):
    """
    DoIPTransport Abstract Base Class.

    Responsibilities of the DoIP Layer:
    - Acts as the Transport/Network layer for diagnostics over IP.
    - Handles DoIP specific headers, payload types, and routing activation.
    - Encapsulates and decapsulates UDS/diagnostic messages within DoIP frames.
    - Interfaces with the underlying network components (TCP/UDP).
    """

    @abstractmethod
    def receive_frame(self, frame: bytes) -> None:
        """
        Receive a DoIP frame from the network layer.

        :param frame: The raw DoIP frame received via TCP/UDP.
        """
        pass

    @abstractmethod
    def send_diagnostic_message(self, target_address: int, payload: bytes) -> None:
        """
        Send a diagnostic message wrapped in DoIP protocol.

        :param target_address: The logical address of the target.
        :param payload: The diagnostic payload (e.g., UDS request/response).
        """
        pass
