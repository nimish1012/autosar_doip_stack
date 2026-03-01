import struct
from ecu.base_ecu import BaseECU
from diagnostic.diagnostic_messages import NegativeResponse, NRC
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
        sid = uds_payload[0]
        
        # 0x10 Diagnostic Session Control
        if sid == 0x10:
            if len(uds_payload) != 2:
                return NegativeResponse(sid, NRC.INVALID_LENGTH).encode()
                
            sub_function = uds_payload[1]
            session_map = {0x01: "DEFAULT", 0x02: "PROGRAMMING", 0x03: "EXTENDED"}
            
            if sub_function in session_map:
                self.state["session"] = session_map[sub_function]
                logger.info(f"BrakeECU (0x{self.logical_address:04X}) entered session: {self.state['session']}")
                return bytes([sid + 0x40, sub_function, 0x00, 0x32, 0x01, 0xF4])
            else:
                return NegativeResponse(sid, NRC.SUB_FUNCTION_NOT_SUPPORTED).encode()
                
        # 0x11 ECU Reset
        elif sid == 0x11:
            if len(uds_payload) != 2:
                return NegativeResponse(sid, NRC.INVALID_LENGTH).encode()
                
            reset_type = uds_payload[1]
            if reset_type in (0x01, 0x02, 0x03): 
                self.state["reset_pending"] = True
                logger.info(f"BrakeECU (0x{self.logical_address:04X}) reset requested: type {reset_type}")
                return bytes([sid + 0x40, reset_type])
            else:
                return NegativeResponse(sid, NRC.SUB_FUNCTION_NOT_SUPPORTED).encode()
                
        # 0x22 Read Data By Identifier
        elif sid == 0x22:
            if len(uds_payload) != 3:
                return NegativeResponse(sid, NRC.INVALID_LENGTH).encode()
                
            did = struct.unpack("!H", uds_payload[1:3])[0]
            if did == 0xF190: # VIN
                logger.info(f"BrakeECU (0x{self.logical_address:04X}) reading VIN")
                return bytes([sid + 0x40]) + uds_payload[1:3] + self.vin
            else:
                return NegativeResponse(sid, NRC.REQUEST_OUT_OF_RANGE).encode()
                
        # NRC 0x11 service not supported
        return NegativeResponse(sid, NRC.SERVICE_NOT_SUPPORTED).encode()
