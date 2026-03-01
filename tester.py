import asyncio
import argparse
import struct
import sys
from doip.messages import DoIPHeader, PayloadType
from diagnostic.diagnostic_messages import NRC

class TesterLogger:
    @staticmethod
    def step(msg):
        print(f"[\033[94mSTEP\033[0m] {msg}")

    @staticmethod
    def send(msg):
        print(f"[\033[93mTX\033[0m]   {msg}")

    @staticmethod
    def recv(msg):
        print(f"[\033[92mRX\033[0m]   {msg}")

    @staticmethod
    def info(msg):
        print(f"[\033[96mINFO\033[0m] {msg}")

    @staticmethod
    def error(msg):
        print(f"[\033[91mERR\033[0m]  {msg}")

    @staticmethod
    def nrc(msg):
        print(f"[\033[95mNRC\033[0m]   {msg}")

async def udp_discovery(ip):
    TesterLogger.step(f"Performing UDP vehicle discovery on {ip}:13400...")
    
    class UDPProtocol(asyncio.DatagramProtocol):
        def __init__(self, on_con_lost):
            self.on_con_lost = on_con_lost
            self.transport = None
            self.discovered_ip = None

        def connection_made(self, transport):
            self.transport = transport
            header = DoIPHeader(0x02, 0xFD, PayloadType.VEHICLE_IDENTIFICATION_REQUEST, 0)
            self.transport.sendto(header.encode())
            TesterLogger.send("Vehicle Identification Request (0x0001 / 0x0005)")

        def datagram_received(self, data, addr):
            try:
                parsed = DoIPHeader.decode(data)
                TesterLogger.recv(f"Vehicle ID Response from {addr[0]}: {parsed}")
                
                if parsed.payload_type == PayloadType.VEHICLE_IDENTIFICATION_RESPONSE and parsed.payload_length >= 32:
                    vin = data[8:25].decode('ascii', errors='replace').strip('\x00')
                    logical_addr = struct.unpack("!H", data[25:27])[0]
                    TesterLogger.info(f"Discovered Vehicle: VIN={vin}, Logical Address=0x{logical_addr:04X}")
                    self.discovered_ip = addr[0]
                    
            except Exception as e:
                TesterLogger.error(f"Failed to decode UDP response: {e}")
            finally:
                self.transport.close()

        def error_received(self, exc):
            TesterLogger.error(f"UDP Error: {exc}")

        def connection_lost(self, exc):
            if not self.on_con_lost.done():
                self.on_con_lost.set_result(self.discovered_ip)

    loop = asyncio.get_running_loop()
    on_con_lost = loop.create_future()
    
    # We bind locally to an ephemeral port and send to the target IP
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPProtocol(on_con_lost),
        remote_addr=(ip, 13400)
    )
    
    try:
        discovered_ip = await asyncio.wait_for(on_con_lost, timeout=2.0)
        if not discovered_ip:
            discovered_ip = ip # Fallback if no specific payload matched
        return discovered_ip
    except asyncio.TimeoutError:
        TesterLogger.error("UDP discovery timed out. No response received.")
        return ip

async def tcp_connect_and_activate(ip, tester_addr=0x0E00):
    TesterLogger.step(f"Establishing TCP connection to {ip}:13400...")
    try:
        reader, writer = await asyncio.open_connection(ip, 13400)
        TesterLogger.info("TCP socket connected.")
    except Exception as e:
        TesterLogger.error(f"Failed to connect: {e}")
        return None, None

    TesterLogger.step(f"Performing Routing Activation (SA=0x{tester_addr:04X})...")
    payload = struct.pack("!H", tester_addr) + b'\x00\x00\x00\x00\x00'
    header = DoIPHeader(0x02, 0xFD, PayloadType.ROUTING_ACTIVATION_REQUEST, len(payload))
    
    writer.write(header.encode() + payload)
    TesterLogger.send("Routing Activation Request (0x0006)")
    await writer.drain()

    try:
        resp_header_data = await asyncio.wait_for(reader.readexactly(8), timeout=2.0)
        resp_header = DoIPHeader.decode(resp_header_data)
        if resp_header.payload_length > 0:
            await reader.readexactly(resp_header.payload_length)
        
        if resp_header.payload_type == PayloadType.ROUTING_ACTIVATION_RESPONSE:
            TesterLogger.recv(f"Routing Activation Response (0x0007)")
            TesterLogger.info("Routing Activation successful.")
            return reader, writer
        else:
            TesterLogger.error(f"Unexpected response: {resp_header}")
            return None, None
            
    except Exception as e:
        TesterLogger.error(f"Routing activation failed: {e}")
        return None, None

async def send_uds(writer, reader, sa, ta, uds_payload, desc="UDS"):
    TesterLogger.step(f"Sending {desc} (SA=0x{sa:04X}, TA=0x{ta:04X})...")
    diag_payload = struct.pack("!HH", sa, ta) + uds_payload
    header = DoIPHeader(0x02, 0xFD, PayloadType.DIAGNOSTIC_MESSAGE, len(diag_payload))
    
    writer.write(header.encode() + diag_payload)
    TesterLogger.send(f"Diagnostic Message (0x8001), Data: {uds_payload.hex().upper()}")
    await writer.drain()
    
    try:
        data = await asyncio.wait_for(reader.readexactly(8), timeout=2.0)
        resp_header = DoIPHeader.decode(data)
        if resp_header.payload_type == PayloadType.DIAGNOSTIC_MESSAGE:
            resp_payload = await asyncio.wait_for(reader.readexactly(resp_header.payload_length), timeout=2.0)
            uds_resp = resp_payload[4:] # Skip SA and TA
            
            if uds_resp[0] == 0x7F:
                req_sid, nrc_val = uds_resp[1], uds_resp[2]
                try:
                    nrc_name = NRC(nrc_val).name
                except ValueError:
                    nrc_name = "UNKNOWN_NRC"
                TesterLogger.nrc(f"Negative Response (0x7F): request_sid=0x{req_sid:02X}, NRC=0x{nrc_val:02X} ({nrc_name})")
            else:
                TesterLogger.recv(f"Diagnostic Message, UDS Positive Response: {uds_resp.hex().upper()}")
                
            return uds_resp
        else:
             if resp_header.payload_length > 0:
                 await reader.readexactly(resp_header.payload_length)
             TesterLogger.recv(f"Unexpected DoIP message: {resp_header}")
    except Exception as e:
        TesterLogger.error(f"Failed to receive UDS response: {e}")
    return None

async def main():
    parser = argparse.ArgumentParser(description="DoIP Diagnostic Tester Client")
    parser.add_argument("--ip", required=True, help="Target vehicle IP address")
    parser.add_argument("--target-ecu", type=lambda x: int(x, 16), default=0x0E00, help="Target ECU logical address (hex, default 0x0E00)")
    parser.add_argument("--tester-addr", type=lambda x: int(x, 16), default=0x0E81, help="Tester logical address (hex, default 0x0E81)")
    
    parser.add_argument("--session", type=lambda x: int(x, 16), help="Start diagnostic session (e.g. 01 for Default, 03 for Extended)")
    parser.add_argument("--read-vin", action="store_true", help="Read VIN (Service 0x22, DID 0xF190)")
    parser.add_argument("--reset", type=lambda x: int(x, 16), help="ECU Reset (e.g. 01 for Hard Reset, 03 for Soft)")
    
    # Negative Testing Helpers
    parser.add_argument("--test-nrc-11", action="store_true", help="Send an unknown SID (0x44) to trigger NRC 0x11")
    parser.add_argument("--test-nrc-13", action="store_true", help="Send a truncated Session Control Request to trigger NRC 0x13")
    parser.add_argument("--test-nrc-31", action="store_true", help="Send requested DID reading unknown value to trigger NRC 0x31")

    args = parser.parse_args()

    # 1. UDP Discovery
    target_ip = await udp_discovery(args.ip)

    # 2. TCP Connect & 3. Routing Activation
    reader, writer = await tcp_connect_and_activate(target_ip, tester_addr=args.tester_addr)
    if not writer:
        return

    try:
        has_tests = False
        
        # 4. Standard UDS Requests
        if args.session is not None:
            has_tests = True
            await send_uds(writer, reader, args.tester_addr, args.target_ecu, bytes([0x10, args.session]), desc=f"Diagnostic Session Control (0x{args.session:02X})")
            
        if args.read_vin:
            has_tests = True
            resp = await send_uds(writer, reader, args.tester_addr, args.target_ecu, b'\x22\xF1\x90', desc="Read VIN (0x22 0xF190)")
            if resp and resp[0] == 0x62 and resp[1:3] == b'\xF1\x90':
                vin = resp[3:].decode('ascii', errors='replace')
                TesterLogger.info(f"Decoded VIN: {vin}")
                
        if args.reset is not None:
            has_tests = True
            await send_uds(writer, reader, args.tester_addr, args.target_ecu, bytes([0x11, args.reset]), desc=f"ECU Reset (0x{args.reset:02X})")
            
        # 5. Negative NRC Validation Requests
        if args.test_nrc_11:
            has_tests = True
            await send_uds(writer, reader, args.tester_addr, args.target_ecu, bytes([0x44]), desc="Unknown SID Test (0x44)")
            
        if args.test_nrc_13:
            has_tests = True
            await send_uds(writer, reader, args.tester_addr, args.target_ecu, bytes([0x10]), desc="Truncated Session Control Request")
            
        if args.test_nrc_31:
            has_tests = True
            await send_uds(writer, reader, args.tester_addr, args.target_ecu, bytes([0x22, 0xF1, 0x99]), desc="Unknown DID Read Request (0x22 0xF199)")
            
        if not has_tests:
            TesterLogger.info("No UDS actions requested. Closing connection.")

    finally:
        TesterLogger.step("Closing TCP connection...")
        writer.close()
        await writer.wait_closed()
        TesterLogger.info("Done.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        TesterLogger.error("Interrupted by user.")
        sys.exit(1)
