from abc import ABC, abstractmethod
from common.logger import setup_logger
from diagnostic.diagnostic_messages import DiagnosticRequest, DiagnosticResponse, NegativeResponse, NRC

logger = setup_logger(__name__)

class BaseECU(ABC):
    """
    BaseECU Abstract Class.

    Responsibilities:
    - Base structure for a concrete ECU simulation.
    - Handles incoming diagnostic requests and maps them to uds_payload router.
    """

    def __init__(self, logical_address: int):
        self.logical_address = logical_address
        self.state = {
            "session": "DEFAULT",  # default, extended, programming
            "reset_pending": False
        }

    def process_diagnostic_request(self, request: DiagnosticRequest) -> DiagnosticResponse:
        """
        Process request from Diagnostic Manager.
        Extracts payload, invokes handle_request, and wraps response.
        Handles default minimum-length invalidations and base response wrappers.
        """
        logger.debug(f"ECU 0x{self.logical_address:04X} received request from 0x{request.source_address:04X}")
        
        if not request.uds_payload or len(request.uds_payload) == 0:
            uds_response_payload = NegativeResponse(0x00, NRC.INVALID_LENGTH).encode()
        else:
            uds_response_payload = self.handle_request(request.uds_payload)
            
            # If sub-classes fail to return or explicitly return None, generate generic failure.
            if not uds_response_payload:
                sid = request.uds_payload[0]
                uds_response_payload = NegativeResponse(sid, NRC.SERVICE_NOT_SUPPORTED).encode()
        
        return DiagnosticResponse(
            source_address=self.logical_address,
            target_address=request.source_address,
            uds_payload=uds_response_payload
        )

    @abstractmethod
    def handle_request(self, uds_payload: bytes) -> bytes:
        """
        Handle the raw UDS payload and return the response payload.
        To be implemented by concrete ECU instances.
        """
        pass

    def initialize(self) -> None:
        """
        Initialize the ECU, setting up logging, and wiring all internal modules.
        """
        logger.info(f"Initialized ECU at 0x{self.logical_address:04X}")

    def start(self) -> None:
        """
        Start ECU operations (e.g., start listening on network interfaces).
        """
        pass

    def shutdown(self) -> None:
        """
        Gracefully shutdown the ECU, stopping network servers and cleaning up resources.
        """
        pass
