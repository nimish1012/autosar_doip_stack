import asyncio
from common.logger import setup_logger
from diagnostic.diagnostic_manager import DiagnosticManager
from doip.doip_gateway import DoIPGateway
from ecu.engine_ecu import EngineECU
from ecu.brake_ecu import BrakeECU

logger = setup_logger("main")

async def run_stack():
    logger.info("Starting AUTOSAR-inspired DoIP Stack...")
    
    # 1. Initialize Diagnostic Manager
    diag_manager = DiagnosticManager()
    
    # 2. Register ECUs
    engine_ecu = EngineECU()
    brake_ecu = BrakeECU()
    diag_manager.register_ecu(0x0E00, engine_ecu)
    diag_manager.register_ecu(0x0E01, brake_ecu)
    
    # 3. Initialize DoIP Gateway
    gateway = DoIPGateway(diagnostic_manager=diag_manager, logical_address=0x0E80)
    
    # 4. Start Gateway
    await gateway.start()
    
    logger.info("Stack running. Press Ctrl+C to stop.")
    
    # Keep running forever
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await gateway.stop()
        logger.info("Stopping...")

def main():
    try:
        asyncio.run(run_stack())
    except KeyboardInterrupt:
        logger.info("Shutting down DoIP Stack...")

if __name__ == "__main__":
    main()
