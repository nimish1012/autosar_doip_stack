import os
import struct

class SecurityManager:
    """Manages UDS Security Access (Service 0x27) algorithms and keys."""
    LEVEL_1_REQUEST_SEED = 0x01
    LEVEL_1_SEND_KEY = 0x02

    @staticmethod
    def generate_seed() -> bytes:
        """Generate a random 4-byte seed."""
        return os.urandom(4)

    @staticmethod
    def validate_key(seed: bytes, key: bytes) -> bool:
        """
        Validate the provided key against the active seed.
        Placeholder algorithm: key = seed XOR 0xA5A5A5A5
        """
        if len(seed) != 4 or len(key) != 4:
            return False
            
        seed_int = struct.unpack(">I", seed)[0]
        key_int = struct.unpack(">I", key)[0]
        
        expected_key = seed_int ^ 0xA5A5A5A5
        return key_int == expected_key
