import asyncio
import os
from common.logger import setup_logger
from common.config_loader import load_ecu_configs
from diagnostic.diagnostic_manager import DiagnosticManager
from doip.doip_gateway import DoIPGateway
from ecu.dynamic_ecu import DynamicECU

logger = setup_logger("main")

async def run_stack():
    logger.info("Starting AUTOSAR-inspired DoIP Stack...")
    
    # 1. Initialize Diagnostic Manager
    diag_manager = DiagnosticManager()
    
    # 2. Dynamically Load and Register ECUs from /configs
    config_dir = os.path.join(os.path.dirname(__file__), "configs")
    loaded_configs = load_ecu_configs(config_dir)
    
    if not loaded_configs:
        logger.error("No ECU configurations found. Stack cannot route diagnostic messages.")
    
    for config in loaded_configs:
        ecu_instance = DynamicECU(config)
        diag_manager.register_ecu(config["logical_address"], ecu_instance)
        logger.info(f"Dynamically registered {config['name']} at 0x{config['logical_address']:04X}")
    
    # 3. Initialize DoIP Gateway
    gateway = DoIPGateway(diagnostic_manager=diag_manager, logical_address=0x0E80)
    
    # 4. Start Gateway and Servers
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
