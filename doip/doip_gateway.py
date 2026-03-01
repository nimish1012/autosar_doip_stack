import asyncio
import struct
import time
from common.logger import setup_logger
from network.udp_server import AsyncUDPServer
from network.tcp_server import AsyncTCPServer
from doip.messages import DoIPHeader, PayloadType
from doip.connection import DoIPConnection, InvalidTransitionError
from diagnostic.diagnostic_messages import DiagnosticRequest

logger = setup_logger(__name__)

class DoIPGateway:
    """
    DoIP Gateway managing both UDP discovery and TCP connections.
    Routes diagnostic messages to the Diagnostic Manager via the State Machine.
    """
    def __init__(self, diagnostic_manager, logical_address=0x0E80, vin=b"WVWZZZ1ZZA0000000"):
        self.diagnostic_manager = diagnostic_manager
        self.logical_address = logical_address
        self.vin = vin
        self.tcp_server = AsyncTCPServer("0.0.0.0", 13400, self.handle_tcp_client)
        self.udp_transport = None
        
        # State Tracking: map of addr -> (DoIPConnection, writer)
        self.active_connections = {}
        self.monitor_task = None

    async def start(self):
        """Start both UDP discovery, TCP server, and timeout monitor asynchronously."""
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: AsyncUDPServer(self.handle_udp_datagram),
            local_addr=("0.0.0.0", 13400)
        )
        self.udp_transport = transport
        await self.tcp_server.start()
        
        # Start Idle Timeout Background Task
        self.monitor_task = asyncio.create_task(self.monitor_idle_connections())

    async def stop(self):
        """Stop all servers and clean up connections."""
        if self.monitor_task:
            self.monitor_task.cancel()
            
        for addr, (conn, writer) in list(self.active_connections.items()):
            conn.close()
            writer.close()
            
        if self.udp_transport:
            self.udp_transport.close()
            
        await self.tcp_server.stop()

    async def monitor_idle_connections(self):
        """Periodically check active sockets and close timed-out ones."""
        while True:
            try:
                await asyncio.sleep(5) # Check every 5 seconds
                for addr, (conn, writer) in list(self.active_connections.items()):
                    if conn.check_timeout():
                        logger.warning(f"Closing idle connection {addr}")
                        conn.close()
                        writer.close()
                        del self.active_connections[addr]
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor: {e}")

    def handle_udp_datagram(self, data: bytes, addr, transport):
        """Handle incoming UDP broadcast DoIP messages."""
        try:
            header = DoIPHeader.decode(data)
            if header.payload_type in (PayloadType.VEHICLE_IDENTIFICATION_REQUEST, PayloadType.VEHICLE_IDENTIFICATION_REQUEST_WITH_VIN):
                logger.info(f"Received Vehicle ID Request from {addr} (State: DISCOVERY)")
                # Send Vehicle Identification Response (0x0004)
                eid = b'\x00\x11\x22\x33\x44\x55'
                gid = b'\x00\x00\x00\x00\x00\x00'
                further_action = b'\x00'
                payload = self.vin.ljust(17, b'\x00') + struct.pack("!H", self.logical_address) + eid + gid + further_action
                
                resp_header = DoIPHeader(0x02, 0xFD, PayloadType.VEHICLE_IDENTIFICATION_RESPONSE, len(payload))
                transport.sendto(resp_header.encode() + payload, addr)
        except Exception as e:
            logger.error(f"Error handling UDP datagram: {e}")

    async def handle_tcp_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming TCP connections enforcing the DoIP State Machine."""
        addr = writer.get_extra_info('peername')
        
        # Initialize the State Machine for this client
        conn = DoIPConnection(addr, timeout_seconds=60.0) # Using 60s timeout for testing flow
        self.active_connections[addr] = (conn, writer)
        
        try:
            while True:
                header_data = await reader.readexactly(8)
                header = DoIPHeader.decode(header_data)
                
                payload = b""
                if header.payload_length > 0:
                    payload = await reader.readexactly(header.payload_length)
                    
                conn.update_activity()
                
                if header.payload_type == PayloadType.ROUTING_ACTIVATION_REQUEST:
                    logger.info(f"Received Routing Activation Request from {addr}")
                    conn.activate_routing() # State transition
                    
                    sa = payload[:2] # Tester Source address 
                    resp_payload = struct.pack("!H", self.logical_address) + sa + b'\x10' + b'\x00\x00\x00\x00'
                    resp_header = DoIPHeader(0x02, 0xFD, PayloadType.ROUTING_ACTIVATION_RESPONSE, len(resp_payload))
                    writer.write(resp_header.encode() + resp_payload)
                    await writer.drain()
                    
                elif header.payload_type == PayloadType.DIAGNOSTIC_MESSAGE:
                    # Enforce transition to DIAGNOSTIC_ACTIVE or fail if not routed
                    conn.start_diagnostic()
                    
                    source_addr, target_addr = struct.unpack("!HH", payload[:4])
                    uds_payload = payload[4:]
                    logger.info(f"Received Diagnostic Message: SA=0x{source_addr:04X} TA=0x{target_addr:04X}")
                    
                    diag_req = DiagnosticRequest(source_address=source_addr, target_address=target_addr, uds_payload=uds_payload)
                    diag_resp = self.diagnostic_manager.handle_diagnostic_message(diag_req)
                    
                    if diag_resp and diag_resp.uds_payload:
                        resp_payload = struct.pack("!HH", diag_resp.source_address, diag_resp.target_address) + diag_resp.uds_payload
                        resp_header = DoIPHeader(0x02, 0xFD, PayloadType.DIAGNOSTIC_MESSAGE, len(resp_payload))
                        writer.write(resp_header.encode() + resp_payload)
                        await writer.drain()
                        
                else:
                    logger.warning(f"Unhandled/Ignored Payload Type: {header.payload_type}")
                    
        except InvalidTransitionError as e:
            logger.error(f"[{addr}] State Error: {e}. Dropping connection.")
            
        except asyncio.IncompleteReadError:
            pass # Client gently disconnected
            
        except Exception as e:
            if str(e) != "Connection object has been closed":
                logger.error(f"Error handling TCP client {addr}: {e}")
            
        finally:
            conn.close()
            if addr in self.active_connections:
                del self.active_connections[addr]
                
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            logger.info(f"[{addr}] TCP Connection securely closed.")
