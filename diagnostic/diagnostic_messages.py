from dataclasses import dataclass

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
