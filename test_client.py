import asyncio
import struct
from doip.messages import DoIPHeader, PayloadType

async def send_uds_request(writer, reader, source_addr, target_addr, uds_payload):
    print(f"\n[TEST] Sending UDS Request (Tester=0x{source_addr:04X}, ECU=0x{target_addr:04X}, UDS={uds_payload.hex()})...")
    diag_payload = struct.pack("!HH", source_addr, target_addr) + uds_payload
    header = DoIPHeader(0x02, 0xFD, PayloadType.DIAGNOSTIC_MESSAGE, len(diag_payload))
    writer.write(header.encode() + diag_payload)
    await writer.drain()
    
    diag_resp_header_data = await reader.readexactly(8)
    diag_resp_header = DoIPHeader.decode(diag_resp_header_data)
    diag_resp_payload = await reader.readexactly(diag_resp_header.payload_length)
    print(f"[TEST] Received UDS Response: Data={diag_resp_payload.hex()}")

async def run_test_client():
    print("[TEST] Connecting via TCP...")
    reader, writer = await asyncio.open_connection('127.0.0.1', 13400)
    
    # Sending Routing Activation Request
    print("[TEST] Sending Routing Activation Request...")
    payload = b'\x0e\x00\x00\x00\x00\x00\x00' # SA = 0x0E00
    header = DoIPHeader(0x02, 0xFD, PayloadType.ROUTING_ACTIVATION_REQUEST, len(payload))
    writer.write(header.encode() + payload)
    await writer.drain()
    
    resp_header_data = await reader.readexactly(8)
    resp_header = DoIPHeader.decode(resp_header_data)
    resp_payload = await reader.readexactly(resp_header.payload_length)
    print("[TEST] Routing Activation successful.")
    
    # Test Engine ECU (0x0E00)
    print("\n--- Testing EngineECU (0x0E00) ---")
    await send_uds_request(writer, reader, 0x0E00, 0x0E00, b'\x10\x03') # Diagnostic Session Control (Extended)
    await send_uds_request(writer, reader, 0x0E00, 0x0E00, b'\x11\x01') # ECU Reset (Hard)
    await send_uds_request(writer, reader, 0x0E00, 0x0E00, b'\x22\xF1\x90') # Read VIN
    
    # Test Brake ECU (0x0E01)
    print("\n--- Testing BrakeECU (0x0E01) ---")
    await send_uds_request(writer, reader, 0x0E00, 0x0E01, b'\x10\x01') # Diagnostic Session Control (Default)
    await send_uds_request(writer, reader, 0x0E00, 0x0E01, b'\x11\x03') # ECU Reset (Soft)
    await send_uds_request(writer, reader, 0x0E00, 0x0E01, b'\x22\xF1\x90') # Read VIN

    writer.close()
    await writer.wait_closed()
    print("\n[TEST] Finished")

if __name__ == "__main__":
    asyncio.run(run_test_client())
