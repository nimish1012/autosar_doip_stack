# AUTOSAR-inspired DoIP Stack

A Python-based, fully asynchronous Document over IP (DoIP) and Diagnostic testing stack built to mimic the AUTOSAR Layered Architecture.

## Features
- **DoIP Transport Layer**: Asynchronous UDP Vehicle Discovery and TCP connection/routing management.
- **Diagnostic Routing (DCM-like)**: Routes diagnostic requests based on target logical addresses configured in a dynamic ECU Registry.
- **Virtual ECUs**: 
  - `EngineECU` (`0x0E00`) 
  - `BrakeECU` (`0x0E01`)
- **UDS Services**: Implements basic Unified Diagnostic Services:
  - `0x10` - Diagnostic Session Control
  - `0x11` - ECU Reset
  - `0x22` - Read Data By Identifier (e.g., VIN at `0xF190`)
- **CLI Tester**: Built-in, interactive diagnostic tester client.

## Quickstart

### Running the Stack
Launch the virtual ECUs and Gateway:
```bash
python main.py
```
*Ctrl+C to stop the server.*

### Running the Tester Client
Communicate with the running stack using the included `tester.py` CLI utility:
```bash
# Discover the ECU and Read the Engine VIN
python tester.py --ip 127.0.0.1 --read-vin --target-ecu 0x0E00

# Perform a Soft Reset on the Brake ECU
python tester.py --ip 127.0.0.1 --reset 03 --target-ecu 0x0E01

# Enter Extended Diagnostic Session on Engine ECU
python tester.py --ip 127.0.0.1 --session 03 --target-ecu 0x0E00
```
