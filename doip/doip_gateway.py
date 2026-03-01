import asyncio
import struct
from common.logger import setup_logger
from network.udp_server import AsyncUDPServer
from network.tcp_server import AsyncTCPServer
from doip.messages import DoIPHeader, PayloadType
from diagnostic.diagnostic_messages import DiagnosticRequest

logger = setup_logger(__name__)

class DoIPGateway:
    """
    DoIP Gateway managing both UDP discovery and TCP connections.
    Routes diagnostic messages to the Diagnostic Manager.
    """
    def __init__(self, diagnostic_manager, logical_address=0x0E80, vin=b"WVWZZZ1ZZA0000000"):
        self.diagnostic_manager = diagnostic_manager
        self.logical_address = logical_address
        self.vin = vin
        self.tcp_server = AsyncTCPServer("0.0.0.0", 13400, self.handle_tcp_client)
        self.udp_transport = None

    async def start(self):
        """Start both UDP discovery and TCP server asynchronously."""
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: AsyncUDPServer(self.handle_udp_datagram),
            local_addr=("0.0.0.0", 13400)
        )
        self.udp_transport = transport
        await self.tcp_server.start()

    async def stop(self):
        """Stop all servers."""
        if self.udp_transport:
            self.udp_transport.close()
        await self.tcp_server.stop()

    def handle_udp_datagram(self, data: bytes, addr, transport):
        """Handle incoming UDP broadcast DoIP messages."""
        try:
            header = DoIPHeader.decode(data)
            if header.payload_type in (PayloadType.VEHICLE_IDENTIFICATION_REQUEST, PayloadType.VEHICLE_IDENTIFICATION_REQUEST_WITH_VIN):
                logger.info(f"Received Vehicle ID Request from {addr}")
                # Send Vehicle Identification Response (0x0004)
                # Payload: VIN (17) + Logical Address (2) + EID (6) + GID (6) + Further action (1) = 32 bytes
                eid = b'\x00\x11\x22\x33\x44\x55'
                gid = b'\x00\x00\x00\x00\x00\x00'
                further_action = b'\x00'
                payload = self.vin.ljust(17, b'\x00') + struct.pack("!H", self.logical_address) + eid + gid + further_action
                
                resp_header = DoIPHeader(0x02, 0xFD, PayloadType.VEHICLE_IDENTIFICATION_RESPONSE, len(payload))
                transport.sendto(resp_header.encode() + payload, addr)
                logger.info(f"Sent Vehicle ID Response to {addr}")
        except ValueError as e:
            logger.debug(f"Invalid DoIP UDP packet: {e}")
        except Exception as e:
            logger.error(f"Error handling UDP datagram: {e}")

    async def handle_tcp_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming TCP connections and DoIP messages."""
        addr = writer.get_extra_info('peername')
        logger.info(f"TCP Client connected: {addr}")
        
        try:
            while True:
                header_data = await reader.readexactly(8)
                header = DoIPHeader.decode(header_data)
                
                payload = b""
                if header.payload_length > 0:
                    payload = await reader.readexactly(header.payload_length)
                
                if header.payload_type == PayloadType.ROUTING_ACTIVATION_REQUEST:
                    logger.info(f"Received Routing Activation Request from {addr}")
                    sa = payload[:2] # Tester Source address 
                    # Routing Activation Response (0x0007)
                    # Payload: Logical Address (2) + SA (2) + Routing Activation Code (1) + Reserved (4)
                    resp_payload = struct.pack("!H", self.logical_address) + sa + b'\x10' + b'\x00\x00\x00\x00'
                    resp_header = DoIPHeader(0x02, 0xFD, PayloadType.ROUTING_ACTIVATION_RESPONSE, len(resp_payload))
                    writer.write(resp_header.encode() + resp_payload)
                    await writer.drain()
                    logger.info(f"Sent Routing Activation Response to {addr}")
                    
                elif header.payload_type == PayloadType.DIAGNOSTIC_MESSAGE:
                    source_addr, target_addr = struct.unpack("!HH", payload[:4])
                    uds_payload = payload[4:]
                    logger.info(f"Received Diagnostic Message: SA=0x{source_addr:04X} TA=0x{target_addr:04X} Data={uds_payload.hex()}")
                    
                    # Route via Diagnostic Manager
                    diag_req = DiagnosticRequest(source_address=source_addr, target_address=target_addr, uds_payload=uds_payload)
                    diag_resp = self.diagnostic_manager.handle_diagnostic_message(diag_req)
                    
                    if diag_resp and diag_resp.uds_payload:
                        resp_payload = struct.pack("!HH", diag_resp.source_address, diag_resp.target_address) + diag_resp.uds_payload
                        resp_header = DoIPHeader(0x02, 0xFD, PayloadType.DIAGNOSTIC_MESSAGE, len(resp_payload))
                        writer.write(resp_header.encode() + resp_payload)
                        await writer.drain()
                        logger.info(f"Sent Diagnostic Response: SA=0x{diag_resp.source_address:04X} TA=0x{diag_resp.target_address:04X} Data={diag_resp.uds_payload.hex()}")
                else:
                    logger.warning(f"Unhandled Payload Type: {header.payload_type}")
                    
        except asyncio.IncompleteReadError:
            logger.info(f"TCP Client disconnected: {addr}")
        except Exception as e:
            logger.error(f"Error handling TCP client {addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info(f"TCP Connection closed: {addr}")
