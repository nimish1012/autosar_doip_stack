import struct
from ecu.base_ecu import BaseECU
from common.logger import setup_logger

logger = setup_logger(__name__)

class BrakeECU(BaseECU):
    """
    Brake ECU Simulation.
    Supports UDS Services: 0x10, 0x11, 0x22
    """
    
    def __init__(self, logical_address: int = 0x0E01):
        super().__init__(logical_address)
        self.vin = b"WVWZZZBRK00A00002"
        
    def handle_request(self, uds_payload: bytes) -> bytes:
        if not uds_payload:
            return b""
            
        sid = uds_payload[0]
        
        # 0x10 Diagnostic Session Control
        if sid == 0x10 and len(uds_payload) >= 2:
            sub_function = uds_payload[1]
            session_map = {0x01: "DEFAULT", 0x02: "PROGRAMMING", 0x03: "EXTENDED"}
            
            if sub_function in session_map:
                self.state["session"] = session_map[sub_function]
                logger.info(f"BrakeECU (0x{self.logical_address:04X}) entered session: {self.state['session']}")
                # Positive response
                return bytes([sid + 0x40, sub_function, 0x00, 0x32, 0x01, 0xF4])
            else:
                return bytes([0x7F, sid, 0x12])
                
        # 0x11 ECU Reset
        elif sid == 0x11 and len(uds_payload) >= 2:
            reset_type = uds_payload[1]
            if reset_type in (0x01, 0x02, 0x03): 
                self.state["reset_pending"] = True
                logger.info(f"BrakeECU (0x{self.logical_address:04X}) reset requested: type {reset_type}")
                return bytes([sid + 0x40, reset_type])
            else:
                return bytes([0x7F, sid, 0x12])
                
        # 0x22 Read Data By Identifier
        elif sid == 0x22 and len(uds_payload) >= 3:
            did = struct.unpack("!H", uds_payload[1:3])[0]
            if did == 0xF190: # VIN
                logger.info(f"BrakeECU (0x{self.logical_address:04X}) reading VIN")
                return bytes([sid + 0x40]) + uds_payload[1:3] + self.vin
            else:
                return bytes([0x7F, sid, 0x31])
                
        # NRC 0x11 service not supported
        return bytes([0x7F, sid, 0x11])
