from dataclasses import dataclass
from enum import IntEnum

class NRC(IntEnum):
    """Negative Response Codes representing standard ISO 14229-1 UDS failures."""
    GENERAL_REJECT = 0x10
    SERVICE_NOT_SUPPORTED = 0x11
    SUB_FUNCTION_NOT_SUPPORTED = 0x12
    INVALID_LENGTH = 0x13
    CONDITIONS_NOT_CORRECT = 0x22
    REQUEST_OUT_OF_RANGE = 0x31
    SECURITY_DENIED = 0x33
    INVALID_KEY = 0x35
    SUB_FUNCTION_NOT_SUPPORTED_IN_ACTIVE_SESSION = 0x7E

class DiagnosticSession(IntEnum):
    """Supported UDS Diagnostic Sessions (Service 0x10)."""
    DEFAULT = 0x01
    PROGRAMMING = 0x02
    EXTENDED = 0x03

class NegativeResponse:
    """Format and generate a UDS Negative Response payload (0x7F)."""
    
    def __init__(self, request_sid: int, nrc: NRC):
        self.request_sid = request_sid
        self.nrc = nrc
        
    def encode(self) -> bytes:
        return bytes([0x7F, self.request_sid, self.nrc.value])

@dataclass
class DiagnosticRequest:
    """Represents a diagnostic request object."""
    source_address: int
    target_address: int
    uds_payload: bytes

@dataclass
class DiagnosticResponse:
    """Represents a diagnostic response object."""
    source_address: int
    target_address: int
    uds_payload: bytes
