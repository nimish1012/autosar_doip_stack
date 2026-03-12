import struct
from ecu.base_ecu import BaseECU
from diagnostic.diagnostic_messages import NegativeResponse, NRC
from common.logger import setup_logger

logger = setup_logger(__name__)

class DynamicECU(BaseECU):
    """
    Dynamic ECU Simulation running entirely off a loaded YAML configuration.
    Supports basic UDS Services: 0x10, 0x11, 0x22 depending on config.
    """
    
    def __init__(self, config: dict):
        # The schema is guaranteed to be validated upstream.
        super().__init__(config["logical_address"])
        self.config = config
        self.name = config["name"]
        self.vin = config["vin"].encode('ascii', errors='replace')
        self.supported_services = dict(config["supported_services"])  # Shallow copy to avoid mutating original config
        for sid, details in self.supported_services.items():
            if isinstance(details, list):
                self.supported_services[sid] = {"sessions": details, "requires_security": False}
            elif isinstance(details, dict):
                self.supported_services[sid] = {
                    "sessions": details.get("sessions", []),
                    "requires_security": details.get("requires_security", False)
                }
        self.data_identifiers = config["data_identifiers"]
        
    def is_service_supported(self, sid: int) -> bool:
        return sid in self.supported_services

    def is_service_supported_in_session(self, sid: int, session_id: int) -> bool:
        return self.is_service_supported(sid) and (session_id in self.supported_services[sid]["sessions"])

    def is_service_security_required(self, sid: int) -> bool:
        if self.is_service_supported(sid):
            return self.supported_services[sid]["requires_security"]
        return False
        
    def handle_request(self, uds_payload: bytes) -> bytes:
        sid = uds_payload[0]
        
        # 1. 0x11 ECU Reset
        if sid == 0x11:
            if len(uds_payload) != 2:
                return NegativeResponse(sid, NRC.INVALID_LENGTH).encode()
                
            reset_type = uds_payload[1]
            if reset_type in (0x01, 0x02, 0x03): 
                self.state["reset_pending"] = True
                logger.info(f"{self.name} (0x{self.logical_address:04X}) reset requested: type {reset_type}")
                return bytes([sid + 0x40, reset_type])
            else:
                return NegativeResponse(sid, NRC.SUB_FUNCTION_NOT_SUPPORTED).encode()
                
        # 2. 0x22 Read Data By Identifier
        elif sid == 0x22:
            if len(uds_payload) != 3:
                return NegativeResponse(sid, NRC.INVALID_LENGTH).encode()
                
            did_hex_str_or_int = uds_payload[1:3].hex().upper()
            did_int = struct.unpack("!H", uds_payload[1:3])[0]
            
            # Let's cleanly resolve the YAML configuration matching mechanism
            # The config data_identifiers keys could be typed as ints (if hex wasn't quoted in YAML) or string
            matched_value = None
            if f"0x{did_hex_str_or_int}" in self.data_identifiers:
                matched_value = self.data_identifiers[f"0x{did_hex_str_or_int}"]
            elif did_int in self.data_identifiers:
                matched_value = self.data_identifiers[did_int]
                
            if matched_value == "VIN":
                logger.info(f"{self.name} (0x{self.logical_address:04X}) reading VIN")
                return bytes([sid + 0x40]) + uds_payload[1:3] + self.vin
            elif matched_value is not None:
                # E.g. returning strings or values from config dynamically
                encoded_val = str(matched_value).encode('ascii', errors='replace')
                return bytes([sid + 0x40]) + uds_payload[1:3] + encoded_val
            else:
                logger.warning(f"{self.name} (0x{self.logical_address:04X}) unable to read unknown DID {did_int:04X}")
                return NegativeResponse(sid, NRC.REQUEST_OUT_OF_RANGE).encode()
                
        # Safety net (Should technically be caught by `if sid not in supported_services` earlier)
        return NegativeResponse(sid, NRC.SERVICE_NOT_SUPPORTED).encode()
