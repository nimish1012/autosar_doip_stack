import asyncio
from common.logger import setup_logger

logger = setup_logger(__name__)

class AsyncUDPServer(asyncio.DatagramProtocol):
    def __init__(self, callback):
        self.callback = callback
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        logger.info(f"UDP Server started listening")

    def datagram_received(self, data, addr):
        logger.debug(f"Received UDP datagram from {addr}: {data.hex()}")
        self.callback(data, addr, self.transport)

    def error_received(self, exc):
        logger.error(f"UDP Server error: {exc}")
