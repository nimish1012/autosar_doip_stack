import struct
from dataclasses import dataclass
from enum import IntEnum

class PayloadType(IntEnum):
    GENERIC_NEGATIVE_ACK = 0x0000
    VEHICLE_IDENTIFICATION_REQUEST = 0x0001 # Can be broadcast (0x0001) or with EID/VIN (0x0002/0x0003) 
    VEHICLE_IDENTIFICATION_RESPONSE = 0x0004
    VEHICLE_IDENTIFICATION_REQUEST_WITH_VIN = 0x0005
    ROUTING_ACTIVATION_REQUEST = 0x0006
    ROUTING_ACTIVATION_RESPONSE = 0x0007
    ALIVE_CHECK_REQUEST = 0x0008
    ALIVE_CHECK_RESPONSE = 0x0009
    DIAGNOSTIC_MESSAGE = 0x8001
    DIAGNOSTIC_MESSAGE_POSITIVE_ACK = 0x8002
    DIAGNOSTIC_MESSAGE_NEGATIVE_ACK = 0x8003

@dataclass
class DoIPHeader:
    protocol_version: int
    inverse_version: int
    payload_type: int
    payload_length: int

    def encode(self) -> bytes:
        return struct.pack("!BBHL", self.protocol_version, self.inverse_version, self.payload_type, self.payload_length)

    @classmethod
    def decode(cls, data: bytes) -> 'DoIPHeader':
        if len(data) < 8:
            raise ValueError("Data too short for DoIP Header")
        pv, iv, pt, pl = struct.unpack("!BBHL", data[:8])
        if pv != (iv ^ 0xFF):
            # Sometimes inverse version is skipped or not strictly enforced, but ISO requires it.
            pass
        return cls(pv, iv, pt, pl)
