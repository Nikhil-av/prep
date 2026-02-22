# RATE LIMITER - Complete Implementation
# Patterns: Strategy (multiple algorithms)

from abc import ABC, abstractmethod
from collections import deque
import time
from typing import Dict

# ============ RATE LIMIT STRATEGY ============

class RateLimitStrategy(ABC):
    """Strategy interface for rate limiting algorithms."""
    
    @abstractmethod
    def is_allowed(self, client_id: str) -> bool:
        """Returns True if request is allowed, False if rate limited."""
        pass
    
    @abstractmethod
    def get_wait_time(self, client_id: str) -> float:
        """Returns seconds to wait before next allowed request."""
        pass


# ============ TOKEN BUCKET ALGORITHM ============

class TokenBucket:
    """Token bucket for a single client."""
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity          # Max tokens
        self.tokens = capacity            # Current tokens
        self.refill_rate = refill_rate    # Tokens per second
        self.last_refill = time.time()
    
    def _refill(self):
        """Add tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if successful."""
        self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def get_wait_time(self) -> float:
        """Returns seconds until 1 token is available."""
        self._refill()
        if self.tokens >= 1:
            return 0
        tokens_needed = 1 - self.tokens
        return tokens_needed / self.refill_rate


class TokenBucketStrategy(RateLimitStrategy):
    """
    Token Bucket Algorithm:
    - Each client has a bucket with N tokens
    - Tokens refill at a constant rate
    - Each request consumes 1 token
    - If no tokens, request is rejected
    
    Pros: Allows bursts up to bucket capacity
    Cons: Memory per client
    """
    
    def __init__(self, capacity: int = 10, refill_rate: float = 1.0):
        self.capacity = capacity          # Max tokens per client
        self.refill_rate = refill_rate    # Tokens per second
        self.buckets: Dict[str, TokenBucket] = {}
    
    def _get_bucket(self, client_id: str) -> TokenBucket:
        if client_id not in self.buckets:
            self.buckets[client_id] = TokenBucket(self.capacity, self.refill_rate)
        return self.buckets[client_id]
    
    def is_allowed(self, client_id: str) -> bool:
        bucket = self._get_bucket(client_id)
        allowed = bucket.consume(1)
        status = "✅ ALLOWED" if allowed else "❌ RATE LIMITED"
        print(f"[TokenBucket] {client_id}: {status} (tokens: {bucket.tokens:.1f})")
        return allowed
    
    def get_wait_time(self, client_id: str) -> float:
        return self._get_bucket(client_id).get_wait_time()


# ============ SLIDING WINDOW LOG ALGORITHM ============

class SlidingWindowLogStrategy(RateLimitStrategy):
    """
    Sliding Window Log Algorithm:
    - Store timestamp of each request
    - Count requests in last N seconds
    - If count >= limit, reject
    
    Pros: Accurate, no boundary issues
    Cons: Memory (stores all timestamps)
    """
    
    def __init__(self, max_requests: int = 10, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_logs: Dict[str, deque] = {}
    
    def _get_log(self, client_id: str) -> deque:
        if client_id not in self.request_logs:
            self.request_logs[client_id] = deque()
        return self.request_logs[client_id]
    
    def _clean_old_requests(self, log: deque, now: float):
        """Remove requests outside the window."""
        window_start = now - self.window_seconds
        while log and log[0] < window_start:
            log.popleft()
    
    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        log = self._get_log(client_id)
        self._clean_old_requests(log, now)
        
        if len(log) < self.max_requests:
            log.append(now)
            print(f"[SlidingWindow] {client_id}: ✅ ALLOWED ({len(log)}/{self.max_requests})")
            return True
        else:
            print(f"[SlidingWindow] {client_id}: ❌ RATE LIMITED ({len(log)}/{self.max_requests})")
            return False
    
    def get_wait_time(self, client_id: str) -> float:
        now = time.time()
        log = self._get_log(client_id)
        self._clean_old_requests(log, now)
        
        if len(log) < self.max_requests:
            return 0
        
        # Wait until oldest request expires
        oldest = log[0]
        wait = (oldest + self.window_seconds) - now
        return max(0, wait)


# ============ FIXED WINDOW COUNTER ============

class FixedWindowStrategy(RateLimitStrategy):
    """
    Fixed Window Counter:
    - Divide time into fixed windows (e.g., each minute)
    - Count requests per window
    - Reset counter at window boundary
    
    Pros: Simple, low memory
    Cons: Burst at window boundaries
    """
    
    def __init__(self, max_requests: int = 10, window_seconds: float = 60.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.counters: Dict[str, tuple] = {}  # client_id -> (window_start, count)
    
    def _get_current_window(self) -> float:
        """Get the start time of current window."""
        now = time.time()
        return now - (now % self.window_seconds)
    
    def is_allowed(self, client_id: str) -> bool:
        current_window = self._get_current_window()
        
        if client_id not in self.counters:
            self.counters[client_id] = (current_window, 0)
        
        window_start, count = self.counters[client_id]
        
        # Reset if new window
        if window_start != current_window:
            count = 0
            window_start = current_window
        
        if count < self.max_requests:
            self.counters[client_id] = (window_start, count + 1)
            print(f"[FixedWindow] {client_id}: ✅ ALLOWED ({count + 1}/{self.max_requests})")
            return True
        else:
            print(f"[FixedWindow] {client_id}: ❌ RATE LIMITED ({count}/{self.max_requests})")
            return False
    
    def get_wait_time(self, client_id: str) -> float:
        current_window = self._get_current_window()
        next_window = current_window + self.window_seconds
        return next_window - time.time()


# ============ LEAKY BUCKET ALGORITHM ============

class LeakyBucket:
    """Leaky bucket for a single client."""
    def __init__(self, capacity: int, leak_rate: float):
        self.capacity = capacity      # Max queue size
        self.leak_rate = leak_rate    # Requests processed per second
        self.water = 0.0              # Current water level (requests in queue)
        self.last_leak = time.time()
    
    def _leak(self):
        """Remove water based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_leak
        leaked = elapsed * self.leak_rate
        self.water = max(0, self.water - leaked)
        self.last_leak = now
    
    def add_drop(self) -> bool:
        """Try to add a request. Returns True if accepted (space in bucket)."""
        self._leak()
        if self.water < self.capacity:
            self.water += 1
            return True
        return False  # Bucket overflow!
    
    def get_wait_time(self) -> float:
        """Returns seconds until bucket has space for 1 more request."""
        self._leak()
        if self.water < self.capacity:
            return 0
        overflow = self.water - self.capacity + 1
        return overflow / self.leak_rate


class LeakyBucketStrategy(RateLimitStrategy):
    """
    Leaky Bucket Algorithm:
    - Requests fill a bucket (queue)
    - Bucket "leaks" (processes) at a fixed rate
    - If bucket overflows, request is rejected
    
    Difference from Token Bucket:
    - Token Bucket: Controls RATE of incoming requests
    - Leaky Bucket: SMOOTHS traffic by processing at fixed rate
    
    Pros: Smooths burst traffic, consistent processing rate
    Cons: Can cause delays even when system is idle
    """
    
    def __init__(self, capacity: int = 10, leak_rate: float = 1.0):
        self.capacity = capacity      # Max bucket size per client
        self.leak_rate = leak_rate    # Requests leaked per second
        self.buckets: Dict[str, LeakyBucket] = {}
    
    def _get_bucket(self, client_id: str) -> LeakyBucket:
        if client_id not in self.buckets:
            self.buckets[client_id] = LeakyBucket(self.capacity, self.leak_rate)
        return self.buckets[client_id]
    
    def is_allowed(self, client_id: str) -> bool:
        bucket = self._get_bucket(client_id)
        allowed = bucket.add_drop()
        status = "✅ ALLOWED" if allowed else "❌ RATE LIMITED (overflow)"
        print(f"[LeakyBucket] {client_id}: {status} (level: {bucket.water:.1f}/{bucket.capacity})")
        return allowed
    
    def get_wait_time(self, client_id: str) -> float:
        return self._get_bucket(client_id).get_wait_time()


# ============ RATE LIMITER (Facade) ============

class RateLimiter:
    """
    Main Rate Limiter facade.
    Uses Strategy pattern for different algorithms.
    """
    
    def __init__(self, strategy: RateLimitStrategy = None):
        self.strategy = strategy or TokenBucketStrategy()
    
    def set_strategy(self, strategy: RateLimitStrategy):
        self.strategy = strategy
        print(f"🔧 Strategy changed to: {strategy.__class__.__name__}")
    
    def is_allowed(self, client_id: str) -> bool:
        """Check if request from client is allowed."""
        return self.strategy.is_allowed(client_id)
    
    def get_wait_time(self, client_id: str) -> float:
        """Get wait time in seconds for client."""
        return self.strategy.get_wait_time(client_id)
    
    def try_request(self, client_id: str) -> tuple:
        """
        Attempt a request.
        Returns: (allowed: bool, wait_time: float)
        """
        allowed = self.is_allowed(client_id)
        wait_time = 0 if allowed else self.get_wait_time(client_id)
        return allowed, wait_time


# ============ DEMO ============

if __name__ == "__main__":
    print("=" * 60)
    print("RATE LIMITER - DEMO")
    print("=" * 60)
    
    # Demo 1: Token Bucket (5 tokens, refill 1/second)
    print("\n--- Token Bucket Strategy ---")
    print("Config: 5 tokens max, 1 token/second refill\n")
    
    limiter = RateLimiter(TokenBucketStrategy(capacity=5, refill_rate=1))
    
    # Make 7 rapid requests (first 5 allowed, next 2 rejected)
    for i in range(7):
        limiter.is_allowed("user_123")
    
    # Wait and try again
    print("\n*Waiting 2 seconds for tokens to refill*\n")
    time.sleep(2)
    
    for i in range(3):
        limiter.is_allowed("user_123")
    
    # Demo 2: Sliding Window (3 requests per 5 seconds)
    print("\n" + "=" * 60)
    print("--- Sliding Window Log Strategy ---")
    print("Config: 3 requests per 5 seconds\n")
    
    limiter.set_strategy(SlidingWindowLogStrategy(max_requests=3, window_seconds=5))
    
    for i in range(5):
        limiter.is_allowed("user_456")
    
    # Demo 3: Different clients
    print("\n" + "=" * 60)
    print("--- Multiple Clients ---\n")
    
    limiter.set_strategy(TokenBucketStrategy(capacity=3, refill_rate=1))
    
    # Each client has their own bucket
    limiter.is_allowed("alice")
    limiter.is_allowed("alice")
    limiter.is_allowed("bob")
    limiter.is_allowed("alice")  # Alice's 3rd
    limiter.is_allowed("alice")  # Alice rate limited
    limiter.is_allowed("bob")    # Bob's 2nd - still allowed
    
    # Demo 4: Leaky Bucket
    print("\n" + "=" * 60)
    print("--- Leaky Bucket Strategy ---")
    print("Config: capacity=5, leak_rate=2/second\n")
    
    limiter.set_strategy(LeakyBucketStrategy(capacity=5, leak_rate=2))
    
    # Rapid requests - bucket fills up
    for i in range(7):
        limiter.is_allowed("user_789")
    
    # Wait for bucket to leak
    print("\n*Waiting 2 seconds for bucket to leak*\n")
    time.sleep(2)
    
    for i in range(3):
        limiter.is_allowed("user_789")
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETED!")
    print("=" * 60)

