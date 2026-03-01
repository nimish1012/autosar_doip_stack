from enum import Enum
import time
from common.logger import setup_logger

logger = setup_logger(__name__)

class DoIPConnectionState(Enum):
    IDLE = "IDLE"
    DISCOVERY = "DISCOVERY"
    TCP_CONNECTED = "TCP_CONNECTED"
    ROUTING_ACTIVATED = "ROUTING_ACTIVATED"
    DIAGNOSTIC_ACTIVE = "DIAGNOSTIC_ACTIVE"
    CLOSED = "CLOSED"

class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass

class DoIPConnection:
    """Manages the state and timeout of a single DoIP TCP connection."""
    
    def __init__(self, addr, timeout_seconds=30.0):
        self.addr = addr
        self.state = DoIPConnectionState.TCP_CONNECTED
        self.last_activity = time.time()
        self.timeout_seconds = timeout_seconds
        logger.info(f"[{addr}] Connection established. State: {self.state.value}")

    def update_activity(self):
        """Update the timestamp of the last activity on the connection."""
        self.last_activity = time.time()

    def check_timeout(self) -> bool:
        """Check if the connection has timed out due to inactivity."""
        if self.state == DoIPConnectionState.CLOSED:
            return False
            
        elapsed = time.time() - self.last_activity
        if elapsed > self.timeout_seconds:
            logger.warning(f"[{self.addr}] Connection timed out after {elapsed:.1f}s of inactivity.")
            return True
        return False

    def activate_routing(self):
        """Transition to ROUTING_ACTIVATED state."""
        self.update_activity()
        if self.state in (DoIPConnectionState.TCP_CONNECTED, DoIPConnectionState.ROUTING_ACTIVATED):
            if self.state != DoIPConnectionState.ROUTING_ACTIVATED:
                self._transition(DoIPConnectionState.ROUTING_ACTIVATED)
        else:
            raise InvalidTransitionError(f"Cannot activate routing from {self.state.value}")

    def start_diagnostic(self):
        """Transition to DIAGNOSTIC_ACTIVE state on first diagnostic message."""
        self.update_activity()
        if self.state == DoIPConnectionState.ROUTING_ACTIVATED:
            self._transition(DoIPConnectionState.DIAGNOSTIC_ACTIVE)
        elif self.state == DoIPConnectionState.DIAGNOSTIC_ACTIVE:
            pass # Already active
        else:
            raise InvalidTransitionError(f"Cannot process diagnostic message in state {self.state.value}")

    def close(self):
        """Transition to CLOSED state."""
        if self.state != DoIPConnectionState.CLOSED:
            self._transition(DoIPConnectionState.CLOSED)

    def _transition(self, new_state: DoIPConnectionState):
        """Helper to explicitly perform and log the state transition."""
        old_state = self.state
        self.state = new_state
        logger.info(f"[{self.addr}] Transition: {old_state.value} -> {new_state.value}")
