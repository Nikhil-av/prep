# ⏱️ RATE LIMITER — LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design a **Rate Limiter** that limits the number of requests a client can make within a time window. Used to prevent abuse, protect APIs, and ensure fair usage.

---

## 🤔 THINK: Before Reading Further...
**What are the different ways to define "rate limit"?**

<details>
<summary>👀 Click to reveal</summary>

| Algorithm | Definition | Example |
|-----------|-----------|---------|
| **Fixed Window** | Max N requests per fixed time window | 100 req/min (resets every minute boundary) |
| **Sliding Window Log** | Max N requests in the last T seconds | 100 req in last 60 seconds |
| **Sliding Window Counter** | Hybrid of fixed + sliding | Weighted average of current + previous window |
| **Token Bucket** | Bucket holds N tokens, refills at rate R. Each request costs 1 token | 100 tokens, refill 10/sec |
| **Leaky Bucket** | Queue processes at fixed rate. Overflow = reject | Process 10 req/sec, queue up to 100 |

Each has different tradeoffs. **Token Bucket is the most commonly asked** — it's what AWS and Google use.

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | Limit requests per client (by user_id or IP) |
| 2 | Support multiple algorithms (Strategy pattern) |
| 3 | Return **allow/deny** for each incoming request |
| 4 | Thread-safe (concurrent requests from same client) |
| 5 | Configurable limits (requests per window, bucket size) |

---

## 🔥 ALGORITHM DEEP DIVE

### Algorithm 1: Token Bucket ⭐ (Most Asked)

### 🤔 THINK: Imagine a bucket with 10 marbles. You remove 1 marble per request. Marbles refill at a steady rate. What happens when the bucket is empty?

<details>
<summary>👀 Click to reveal</summary>

```python
class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity           # Max tokens in bucket
        self.tokens = capacity             # Current tokens
        self.refill_rate = refill_rate     # Tokens added per second
        self.last_refill_time = time.time()
    
    def allow_request(self) -> bool:
        self._refill()
        if self.tokens >= 1:
            self.tokens -= 1
            return True       # ✅ Allowed
        return False          # ❌ Rate limited
    
    def _refill(self):
        now = time.time()
        elapsed = now - self.last_refill_time
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill_time = now
```

**Example:** capacity=10, refill_rate=2/sec
- t=0: 10 tokens. 8 requests → 2 tokens left
- t=1: 2 + 2 (refill) = 4 tokens
- t=5: 4 + 10 (refill) = 10 tokens (capped at capacity)

**Why Token Bucket?**
- Allows **bursts** (up to capacity)
- Steady state rate = refill_rate
- Simple, efficient, O(1)

</details>

### Algorithm 2: Fixed Window Counter

### 🤔 THINK: What's the problem with resetting the counter every minute?

<details>
<summary>👀 Click to reveal</summary>

```python
class FixedWindowCounter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_count = 0
        self.window_start = time.time()
    
    def allow_request(self) -> bool:
        now = time.time()
        if now - self.window_start >= self.window_seconds:
            self.request_count = 0         # Reset!
            self.window_start = now
        
        if self.request_count < self.max_requests:
            self.request_count += 1
            return True
        return False
```

**The EDGE PROBLEM:**
```
Limit: 100 req/min

Window 1 (0:00-1:00): 50 req at 0:00, 50 req at 0:59 → OK
Window 2 (1:00-2:00): 50 req at 1:00, 50 req at 1:59 → OK

BUT: 50 (0:59) + 50 (1:00) = 100 req in 2 seconds! 💀
```
At the boundary, clients can effectively double the rate.

**Solution: Sliding Window** or **Token Bucket** instead.

</details>

### Algorithm 3: Sliding Window Log

<details>
<summary>👀 Click to reveal</summary>

```python
class SlidingWindowLog:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_log: list[float] = []  # Timestamps
    
    def allow_request(self) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        
        # Remove old timestamps
        self.request_log = [t for t in self.request_log if t > cutoff]
        
        if len(self.request_log) < self.max_requests:
            self.request_log.append(now)
            return True
        return False
```

**Problem:** Stores every timestamp → O(N) memory. Fine for LLD, bad for production with millions of requests.

</details>

---

## 💡 Strategy Pattern for Algorithms

### 🤔 THINK: How do you make the rate limiter algorithm swappable?

<details>
<summary>👀 Click to reveal</summary>

```python
class RateLimitStrategy(ABC):
    @abstractmethod
    def allow_request(self) -> bool:
        pass

class TokenBucketStrategy(RateLimitStrategy):
    # ... Token Bucket implementation

class FixedWindowStrategy(RateLimitStrategy):
    # ... Fixed Window implementation

class SlidingWindowStrategy(RateLimitStrategy):
    # ... Sliding Window implementation

class RateLimiter:
    def __init__(self):
        self.client_limiters: dict[str, RateLimitStrategy] = {}
    
    def is_allowed(self, client_id: str) -> bool:
        if client_id not in self.client_limiters:
            self.client_limiters[client_id] = TokenBucketStrategy(
                capacity=10, refill_rate=1
            )
        return self.client_limiters[client_id].allow_request()
```

**Each client gets their own limiter instance!** Different clients don't share counters.

</details>

---

## 🧵 Thread Safety

### 🤔 THINK: Two requests from the same client arrive at the exact same time. What could go wrong?

<details>
<summary>👀 Click to reveal</summary>

```python
# Without locking:
Thread 1: check tokens=1 → tokens >= 1 ✅
Thread 2: check tokens=1 → tokens >= 1 ✅  (race condition!)
Thread 1: tokens -= 1 → tokens = 0
Thread 2: tokens -= 1 → tokens = -1  💀 (over-allowed)
```

**Fix: Lock per client**
```python
class RateLimiter:
    def __init__(self):
        self.locks: dict[str, threading.Lock] = {}
    
    def is_allowed(self, client_id: str) -> bool:
        if client_id not in self.locks:
            self.locks[client_id] = threading.Lock()
        
        with self.locks[client_id]:
            return self.client_limiters[client_id].allow_request()
```

</details>

---

## 🔗 Entity Relationships

```
RateLimiter (Singleton)
    └── client_limiters: dict[client_id, RateLimitStrategy]
            │
            ├── Client_A → TokenBucketStrategy(cap=100, rate=10/s)
            ├── Client_B → TokenBucketStrategy(cap=50, rate=5/s)
            └── Client_C → FixedWindowStrategy(max=1000, window=60s)
```

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How to implement distributed rate limiting?"

<details>
<summary>👀 Click to reveal</summary>

In-memory doesn't work across servers. Use **Redis**:
```python
# Redis Token Bucket (pseudocode)
def allow_request(client_id):
    key = f"rate_limit:{client_id}"
    tokens = redis.get(key) or capacity
    
    if tokens > 0:
        redis.decr(key)
        redis.expire(key, window_seconds)
        return True
    return False
```

Or use Redis `MULTI/EXEC` for atomic check-and-decrement.
Libraries: `redis-cell`, `nginx rate limiting`.

</details>

### Q2: "How to rate limit by different dimensions (IP, user, API endpoint)?"

<details>
<summary>👀 Click to reveal</summary>

Composite key:
```python
def get_limiter_key(self, request):
    return f"{request.ip}:{request.user_id}:{request.endpoint}"

# Or separate limiters per dimension:
ip_limiter.is_allowed(request.ip)       # 1000/min per IP
user_limiter.is_allowed(request.user)   # 100/min per user
api_limiter.is_allowed(request.path)    # 50/min per endpoint
# ALL must allow for request to proceed
```

</details>

### Q3: "What HTTP status code do you return?"

<details>
<summary>👀 Click to reveal</summary>

**429 Too Many Requests** with headers:
```
HTTP/1.1 429 Too Many Requests
Retry-After: 30
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1672531200
```

</details>

### Q4: "Token Bucket vs Leaky Bucket — when to use which?"

<details>
<summary>👀 Click to reveal</summary>

| Feature | Token Bucket | Leaky Bucket |
|---------|-------------|-------------|
| Burst handling | ✅ Allows bursts | ❌ Fixed rate only |
| Implementation | Counter-based | Queue-based |
| Use case | API rate limiting | Traffic shaping |
| Example | AWS API Gateway | Network routers |

**Token Bucket:** "You can do 100 requests, and then slow down"
**Leaky Bucket:** "I process exactly 10 requests/second, no more"

</details>

---

## ⚠️ Algorithm Comparison

| Algorithm | Memory | Accuracy | Burst | Complexity |
|-----------|--------|----------|-------|------------|
| Fixed Window | O(1) | ⚠️ Edge problem | ❌ | Simple |
| Sliding Window Log | O(N) | ✅ Accurate | ❌ | Medium |
| Sliding Window Counter | O(1) | ✅ Approximate | ❌ | Medium |
| **Token Bucket** | **O(1)** | **✅** | **✅ Allows** | **Simple** |
| Leaky Bucket | O(N) | ✅ | ❌ | Medium |

**Winner for most use cases: Token Bucket** ⭐

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "I'd implement rate limiting using the **Token Bucket algorithm** — a bucket holds N tokens, refills at rate R per second. Each request costs 1 token. If empty → reject (429). It allows **bursts** up to capacity while maintaining steady-state rate. Each client gets their own bucket via **Strategy pattern**. For thread safety, I'd use a **Lock per client**. The rate limiter is a **Singleton**. In production, I'd use **Redis** for distributed rate limiting across servers."

---

## ✅ Pre-Implementation Checklist

- [ ] RateLimitStrategy ABC
- [ ] TokenBucketStrategy (capacity, refill_rate, allow_request)
- [ ] FixedWindowStrategy (for comparison)
- [ ] SlidingWindowLogStrategy (for comparison)
- [ ] RateLimiter system (client → strategy mapping)
- [ ] Thread-safe with Lock per client
- [ ] Demo: burst of requests, show allow/deny
- [ ] Demo: wait for refill, show recovery

---

*Document created during LLD interview prep session*
