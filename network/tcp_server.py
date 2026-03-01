import asyncio
from common.logger import setup_logger

logger = setup_logger(__name__)

class AsyncTCPServer:
    def __init__(self, host: str, port: int, client_connected_cb):
        self.host = host
        self.port = port
        self.client_connected_cb = client_connected_cb
        self.server = None

    async def start(self):
        self.server = await asyncio.start_server(
            self.client_connected_cb, self.host, self.port
        )
        logger.info(f"TCP Server started listening on {self.host}:{self.port}")
        
    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("TCP Server stopped")
            
    async def serve_forever(self):
        if self.server:
            async with self.server:
                await self.server.serve_forever()
