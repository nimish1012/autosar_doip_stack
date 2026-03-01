from common.logger import setup_logger
from diagnostic.diagnostic_messages import DiagnosticRequest, DiagnosticResponse, NegativeResponse, NRC, DiagnosticSession
from doip.connection import DoIPConnection

logger = setup_logger(__name__)

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ecu.base_ecu import BaseECU

class DiagnosticManager:
    """
    Diagnostic Layer (DCM-like)
    Responsibilities:
    - Maintains an ECU registry.
    - Intercepts stateful Universal Diagnostic Services like 0x10.
    - Routes other diagnostic requests based on the target address to the appropriate ECU simulation.
    """

    def __init__(self):
        self.ecu_registry = {}

    def register_ecu(self, logical_address: int, ecu_instance: 'BaseECU'):
        """Register a mock ECU instance to route requests to."""
        self.ecu_registry[logical_address] = ecu_instance
        logger.info(f"Registered ECU at logical address 0x{logical_address:04X}")

    def handle_diagnostic_message(self, request: DiagnosticRequest, connection: DoIPConnection) -> DiagnosticResponse:
        """
        Process an incoming diagnostic request, validate sessions, and route to ECU.
        """
        target_ecu = self.ecu_registry.get(request.target_address)
        uds_payload = request.uds_payload
        
        if not uds_payload:
            return DiagnosticResponse(request.target_address, request.source_address, NegativeResponse(0x00, NRC.INVALID_LENGTH).encode())
            
        sid = uds_payload[0]
        
        # 1. Intercept Global Stateful Services like 0x10 Diagnostic Session Control
        if sid == 0x10:
            return self._handle_session_control(request, connection)

        # 2. For other requests, update the active session timer
        connection.update_session_activity()
        
        # 3. Route to proper registered virtual ECU Instances
        if target_ecu:
            logger.debug(f"Routing request to ECU at 0x{request.target_address:04X}")
            return target_ecu.process_diagnostic_request(request)
        else:
            logger.warning(f"No ECU found for target address 0x{request.target_address:04X}")
            # If the ECU is untraceable, reject silently or via NRC
            return DiagnosticResponse(request.target_address, request.source_address, NegativeResponse(sid, NRC.GENERAL_REJECT).encode())
            
    def _handle_session_control(self, request: DiagnosticRequest, connection: DoIPConnection) -> DiagnosticResponse:
        """Handle Service 0x10 natively in the DiagnosticManager context binding it to the active tcp socket."""
        uds_payload = request.uds_payload
        sid = uds_payload[0]
        
        if len(uds_payload) != 2:
            return DiagnosticResponse(request.target_address, request.source_address, NegativeResponse(sid, NRC.INVALID_LENGTH).encode())
            
        requested_session_val = uds_payload[1]
        
        try:
            # Try to map the requested byte to the formal enum
            new_session = DiagnosticSession(requested_session_val)
            connection.set_session(new_session)
            
            # Send standard Positive Response for 0x10: `[0x50, session, P2, P2*]`
            positive_payload = bytes([0x50, new_session.value, 0x00, 0x32, 0x01, 0xF4])
            return DiagnosticResponse(request.target_address, request.source_address, positive_payload)
            
        except ValueError:
             # Unsupported session identifier mappings
             return DiagnosticResponse(request.target_address, request.source_address, NegativeResponse(sid, NRC.SUB_FUNCTION_NOT_SUPPORTED).encode())
