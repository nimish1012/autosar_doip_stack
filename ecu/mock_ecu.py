from diagnostic.diagnostic_messages import DiagnosticRequest, DiagnosticResponse
from common.logger import setup_logger

logger = setup_logger(__name__)

class MockECU:
    def __init__(self, logical_address: int):
        self.logical_address = logical_address

    def process_diagnostic_request(self, request: DiagnosticRequest) -> DiagnosticResponse:
        logger.info(f"MockECU at 0x{self.logical_address:04X} processing UDS request: {request.uds_payload.hex()}")
        # Just returning a positive response for testing (adding 0x40 to SID)
        if request.uds_payload:
            sid = request.uds_payload[0]
            resp_sid = sid + 0x40
            resp_payload = bytes([resp_sid]) + request.uds_payload[1:]
            return DiagnosticResponse(source_address=self.logical_address, target_address=request.source_address, uds_payload=resp_payload)
        return DiagnosticResponse(source_address=self.logical_address, target_address=request.source_address, uds_payload=b"")
