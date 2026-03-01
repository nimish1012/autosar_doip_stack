from common.logger import setup_logger
from diagnostic.diagnostic_messages import DiagnosticRequest, DiagnosticResponse

logger = setup_logger(__name__)

class DiagnosticManager:
    """
    DiagnosticManager (similar to AUTOSAR DCM).

    Responsibilities:
    - Route diagnostic requests to appropriate ECU instances.
    - Parse logical ECU address from diagnostic requests.
    - Return diagnostic response to DoIP layer.
    """

    def __init__(self):
        self._ecu_registry = {}  # Map of logical_address (int) -> ECU instance

    def register_ecu(self, logical_address: int, ecu_instance) -> None:
        """
        Register an ECU instance at a specific logical address.
        """
        if logical_address in self._ecu_registry:
            logger.warning(f"Overwriting registration for ECU at logical address 0x{logical_address:04X}")
        self._ecu_registry[logical_address] = ecu_instance
        logger.info(f"Registered ECU at logical address 0x{logical_address:04X}")

    def handle_diagnostic_message(self, request: DiagnosticRequest) -> DiagnosticResponse:
        """
        Handle a diagnostic request from the transport layer.
        Routes the request to the target ECU.
        """
        target_addr = request.target_address
        if target_addr not in self._ecu_registry:
            logger.error(f"No ECU registered at target address 0x{target_addr:04X}")
            # Negative Response code for conditions not correct or similar could be returned,
            # but for now we'll just return an empty payload to signify error in transport,
            # or return a specific UDS NRC.
            return DiagnosticResponse(
                source_address=target_addr,
                target_address=request.source_address,
                uds_payload=b""
            )

        ecu = self._ecu_registry[target_addr]
        logger.debug(f"Routing request to ECU at 0x{target_addr:04X}")
        
        # We assume the ECU has a process_diagnostic_request method.
        if hasattr(ecu, "process_diagnostic_request"):
            return ecu.process_diagnostic_request(request)
        else:
            logger.error(f"ECU at 0x{target_addr:04X} does not implement process_diagnostic_request")
            return DiagnosticResponse(
                source_address=target_addr,
                target_address=request.source_address,
                uds_payload=b""
            )
