from enum import Enum
from datetime import datetime
from abc import ABC, abstractmethod
import threading


# ═══════════════════════════════════════════════════════════════
#                        ENUMS & ENTITIES
# ═══════════════════════════════════════════════════════════════

class LogLevel(Enum):
    DEBUG = 1      # Least severe
    INFO = 2
    WARN = 3
    ERROR = 4
    FATAL = 5      # Most severe


class LogMessage:
    def __init__(self, level: LogLevel, message: str):
        self.level = level
        self.message = message
        self.timestamp = datetime.now()

    def __str__(self):
        return f"[{self.timestamp.strftime('%H:%M:%S')}] [{self.level.name}] {self.message}"


# ═══════════════════════════════════════════════════════════════
#                  CHAIN OF RESPONSIBILITY
# ═══════════════════════════════════════════════════════════════

class LogHandler(ABC):
    """
    Base handler — owns the chain logic.
    
    Subclasses only override write(), NOT handle().
    handle() checks level + passes to next — lives here ONCE.
    """
    def __init__(self, min_level: LogLevel):
        self.min_level = min_level     # Configurable, not hardcoded!
        self.next = None

    def set_next(self, handler):
        self.next = handler
        return handler    # ← Enables fluent chaining: a.set_next(b).set_next(c)

    def handle(self, log: LogMessage):
        """Chain logic in base class — NOT repeated in each subclass."""
        if log.level.value >= self.min_level.value:
            self.write(log)
        if self.next:
            self.next.handle(log)

    @abstractmethod
    def write(self, log: LogMessage):
        """Each subclass implements only this — the actual writing logic."""
        pass


class ConsoleHandler(LogHandler):
    def __init__(self, min_level=LogLevel.DEBUG):
        super().__init__(min_level)

    def write(self, log: LogMessage):
        print(f"  🖥️  [CONSOLE] {log}")


class FileHandler(LogHandler):
    def __init__(self, min_level=LogLevel.WARN):
        super().__init__(min_level)

    def write(self, log: LogMessage):
        print(f"  📄 [FILE]    {log}")


class DatabaseHandler(LogHandler):
    def __init__(self, min_level=LogLevel.ERROR):
        super().__init__(min_level)

    def write(self, log: LogMessage):
        print(f"  🗄️  [DB]      {log}")


# ═══════════════════════════════════════════════════════════════
#                     LOGGER (SINGLETON)
# ═══════════════════════════════════════════════════════════════

class Logger:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.chain_head = None
        self._lock = threading.Lock()

    def add_handler(self, handler: LogHandler):
        """Append handler to end of chain."""
        if not self.chain_head:
            self.chain_head = handler
        else:
            current = self.chain_head
            while current.next:
                current = current.next
            current.set_next(handler)

    def log(self, level: LogLevel, message: str):
        """Thread-safe logging — sends log through the chain."""
        log_message = LogMessage(level, message)
        with self._lock:
            if self.chain_head:
                self.chain_head.handle(log_message)

    # Convenience methods
    def debug(self, msg): self.log(LogLevel.DEBUG, msg)
    def info(self, msg):  self.log(LogLevel.INFO, msg)
    def warn(self, msg):  self.log(LogLevel.WARN, msg)
    def error(self, msg): self.log(LogLevel.ERROR, msg)
    def fatal(self, msg): self.log(LogLevel.FATAL, msg)


# ═══════════════════════════════════════════════════════════════
#                        DEMO
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 55)
    print("     LOGGING FRAMEWORK - LLD DEMO")
    print("=" * 55)

    # --- Setup Logger with Chain ---
    logger = Logger()

    console = ConsoleHandler(min_level=LogLevel.DEBUG)
    file_handler = FileHandler(min_level=LogLevel.WARN)
    db_handler = DatabaseHandler(min_level=LogLevel.ERROR)

    # Build chain: Console → File → DB
    console.set_next(file_handler).set_next(db_handler)
    logger.chain_head = console

    # --- Test 1: DEBUG → Console only ---
    print("\n─── Test 1: DEBUG message ───")
    logger.debug("Variable x = 42")

    # --- Test 2: INFO → Console only ---
    print("\n─── Test 2: INFO message ───")
    logger.info("User logged in")

    # --- Test 3: WARN → Console + File ---
    print("\n─── Test 3: WARN message ───")
    logger.warn("Memory usage at 85%")

    # --- Test 4: ERROR → Console + File + DB ---
    print("\n─── Test 4: ERROR message ───")
    logger.error("Database connection failed")

    # --- Test 5: FATAL → Console + File + DB ---
    print("\n─── Test 5: FATAL message ───")
    logger.fatal("System crash — out of memory!")

    # --- Test 6: Singleton check ---
    print("\n─── Test 6: Singleton ───")
    logger2 = Logger()
    print(f"  logger is logger2: {logger is logger2} ✓")

    # --- Summary ---
    print("\n─── Summary ───")
    print("  DEBUG → Console only")
    print("  INFO  → Console only")
    print("  WARN  → Console + File")
    print("  ERROR → Console + File + DB")
    print("  FATAL → Console + File + DB")

    print("\n" + "=" * 55)
    print("     ALL TESTS COMPLETE! 🎉")
    print("=" * 55)
