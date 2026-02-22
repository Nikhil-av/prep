# Rate Limiter - High Level Design

## 1. Problem Statement

Design a Rate Limiting service that:
- Limits the number of requests a client can make in a given time window
- Protects APIs from abuse, DDoS attacks, and overload
- Supports different limits for different user tiers (free, premium, enterprise)
- Scales to handle millions of requests per second

---

## 2. Functional Requirements

| Requirement | Description |
|-------------|-------------|
| **Rate Limit Enforcement** | Reject requests exceeding the limit |
| **Multi-Dimensional Limiting** | Limit by user_id, IP, API key, endpoint |
| **User Tiers** | Different limits for free/premium/enterprise |
| **Response Headers** | Return remaining quota and reset time |
| **Configurable Rules** | Update limits without redeployment |

---

## 3. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| **Latency** | < 5ms per rate limit check (P99) |
| **Availability** | 99.99% (critical infrastructure) |
| **Scalability** | Handle 1M+ requests/second |
| **Accuracy** | < 1% error in count accuracy |
| **Fault Tolerance** | Graceful degradation if Redis is down |

---

## 4. System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENTS                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      LOAD BALANCER                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  API GATEWAY / RATE LIMITER                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Instance 1  │  │  Instance 2  │  │  Instance 3  │          │
│  │ (Stateless)  │  │ (Stateless)  │  │ (Stateless)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       REDIS CLUSTER                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│  │ Shard 0 │  │ Shard 1 │  │ Shard 2 │  │ Shard 3 │            │
│  │ Primary │  │ Primary │  │ Primary │  │ Primary │            │
│  │  + Rep  │  │  + Rep  │  │  + Rep  │  │  + Rep  │            │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       API SERVERS                               │
└─────────────────────────────────────────────────────────────────┘
```

### Where to Place the Rate Limiter?

| Option | Pros | Cons |
|--------|------|------|
| **Load Balancer** | Simple, fast | Limited rules (IP only) |
| **API Gateway** ✅ | Flexible, centralized | Extra hop |
| **Application Code** | Full control | Inconsistent across services |

**Recommendation:** Use an **API Gateway** (Kong, Envoy, custom) for maximum flexibility.

---

## 5. Rate Limiting Algorithms

### Algorithm Comparison

| Algorithm | Burst Handling | Boundary Problem | Memory | Complexity |
|-----------|----------------|------------------|--------|------------|
| **Fixed Window** | ❌ No control | ❌ Yes | Low | Simple |
| **Sliding Window Log** | ✅ Yes | ✅ No | High | Medium |
| **Sliding Window Counter** | ✅ Partial | ✅ No | Low | Medium |
| **Token Bucket** ✅ | ✅ Controlled | ✅ No | Low | Medium |
| **Leaky Bucket** | ❌ Fixed rate | ✅ No | Low | Medium |

---

### Fixed Window (Simple but Flawed)

```
┌─────────────────────────────────────────┐
│         FIXED WINDOW COUNTER            │
│                                         │
│  Minute 1 (00:00-00:59): count = 0→100  │
│  Minute 2 (01:00-01:59): count resets   │
│                                         │
└─────────────────────────────────────────┘
```

**The Boundary Problem:**
```
User sends 100 requests at 00:59:59 ✅
User sends 100 requests at 01:00:01 ✅
→ 200 requests in 2 seconds! (Limit was 100/min)
```

**Redis Implementation:**
```python
def is_allowed_fixed_window(user_id, limit=100):
    key = f"rate:{user_id}:{current_minute()}"
    count = redis.incr(key)
    
    if count == 1:
        redis.expire(key, 60)
    
    return count <= limit
```

---

### Token Bucket (Recommended)

```
┌─────────────────────────┐
│  🪣 TOKEN BUCKET        │
│                         │
│  Capacity: 100 tokens   │
│  Refill: 100 tokens/min │
│  (~1.67 tokens/second)  │
│                         │
│  Current: 🟢🟢🟢 (75)   │
└─────────────────────────┘
```

**How it works:**
1. Bucket has maximum capacity (e.g., 100 tokens)
2. Tokens refill at a constant rate (e.g., 100/minute)
3. Each request consumes 1 token
4. If bucket is empty → Request rejected

**Why it's better:**
- Allows controlled bursts (up to capacity)
- No boundary problem (tokens refill continuously)
- Smooth rate limiting

**Redis Implementation (Atomic Lua Script):**
```lua
-- token_bucket.lua
local key = KEYS[1]
local capacity = tonumber(ARGV[1])      -- Max tokens
local refill_rate = tonumber(ARGV[2])   -- Tokens per second
local now = tonumber(ARGV[3])           -- Current timestamp

-- Get current state
local data = redis.call('HMGET', key, 'tokens', 'last_update')
local tokens = tonumber(data[1]) or capacity
local last_update = tonumber(data[2]) or now

-- Calculate tokens to add since last request
local elapsed = now - last_update
local tokens_to_add = elapsed * refill_rate
tokens = math.min(capacity, tokens + tokens_to_add)

-- Try to consume 1 token
if tokens >= 1 then
    tokens = tokens - 1
    redis.call('HMSET', key, 'tokens', tokens, 'last_update', now)
    redis.call('EXPIRE', key, 120)
    return 1  -- Allowed
else
    return 0  -- Blocked
end
```

**Python Usage:**
```python
def is_allowed(user_id, capacity=100, refill_rate=1.67):
    result = redis.eval(
        BUCKET_SCRIPT,
        1,
        f"bucket:{user_id}",
        capacity,
        refill_rate,
        time.time()
    )
    return result == 1
```

---

### Sliding Window Counter (Alternative)

Combines current and previous window with weights:

```
Current minute weight:  (seconds elapsed / 60)
Previous minute weight: (1 - current weight)

Effective count = (prev_count × prev_weight) + (curr_count × curr_weight)
```

**Example at 01:15 (15 seconds into minute 2):**
```
Previous minute (00:00-00:59): 80 requests
Current minute  (01:00-01:59): 30 requests

Weight: current = 15/60 = 0.25, previous = 0.75
Effective = (80 × 0.75) + (30 × 0.25) = 60 + 7.5 = 67.5

If limit = 100 → Still allowed ✅
```

---

## 6. Redis Data Structure

### Token Bucket State

```
Key: "bucket:{user_id}" or "bucket:{ip}"

┌─────────────────────────────────────────┐
│  Hash Fields:                           │
│                                         │
│  tokens: 75.5        (current count)    │
│  last_update: 1706998083.456 (timestamp)│
└─────────────────────────────────────────┘
```

### Multi-Dimensional Keys

```
Global limit per endpoint:
  "bucket:global:/api/search"

Per-user limit:
  "bucket:user:12345:/api/search"

Per-IP limit:
  "bucket:ip:192.168.1.1:/api/search"

Per-API-key limit:
  "bucket:apikey:sk_live_xxxxx:/api/payments"
```

---

## 7. Multi-Dimensional Rate Limiting

### Checking Multiple Limits

```python
def is_allowed(request):
    user_id = request.user_id
    ip = request.ip_address
    endpoint = request.path
    
    checks = []
    
    # 1. Global limit (protect the system)
    checks.append(
        check_bucket(f"bucket:global:{endpoint}", capacity=10000, rate=166)
    )
    
    # 2. Per-User limit (fair usage)
    if user_id:
        tier = get_user_tier(user_id)  # free/premium/enterprise
        limits = TIER_LIMITS[tier]
        checks.append(
            check_bucket(f"bucket:user:{user_id}:{endpoint}", **limits)
        )
    
    # 3. Per-IP limit (prevent anonymous abuse)
    checks.append(
        check_bucket(f"bucket:ip:{ip}:{endpoint}", capacity=50, rate=0.83)
    )
    
    # ALL checks must pass
    if all(checks):
        return True
    else:
        return False  # Return 429
```

### Tier-Based Limits

```python
TIER_LIMITS = {
    "free": {
        "capacity": 100,
        "rate": 1.67  # 100 per minute
    },
    "premium": {
        "capacity": 1000,
        "rate": 16.67  # 1000 per minute
    },
    "enterprise": {
        "capacity": 10000,
        "rate": 166.67  # 10000 per minute
    }
}
```

---

## 8. Why Redis (Not Database)?

### Speed Comparison

| Operation | Redis | PostgreSQL |
|-----------|-------|------------|
| Read 1 key | ~0.5ms | ~5-20ms |
| Write 1 key | ~0.5ms | ~10-50ms |
| Atomic INCR | ~0.3ms | ~15ms |
| Throughput | 100K+ ops/sec | 5K-10K ops/sec |

### Why Redis is Faster

| Feature | Benefit |
|---------|---------|
| **In-Memory** | No disk I/O |
| **Single-Threaded** | No lock contention |
| **Atomic Commands** | INCR, DECR are single operations |
| **Lua Scripts** | Complex logic runs atomically |
| **Simple Data Model** | No query parsing, no joins |

### Why Not Database?

```sql
-- Database rate limiting (SLOW)
BEGIN;
SELECT count FROM rate_limits WHERE user_id = 123 FOR UPDATE;  -- Lock!
UPDATE rate_limits SET count = count + 1 WHERE user_id = 123;
COMMIT;
-- 3 round trips + disk sync = Too slow for per-request checks
```

---

## 9. Redis Atomicity (No Locks Needed)

### The Race Condition Problem

```
Without atomicity:
  Server 1: READ tokens = 5
  Server 2: READ tokens = 5
  Server 1: WRITE tokens = 4
  Server 2: WRITE tokens = 4
  Result: 4 (should be 3!) ❌
```

### How Redis Solves It

1. **Single-Threaded Execution**: Commands run one at a time
2. **Atomic Commands**: INCR is a single operation
3. **Lua Scripts**: Multi-step logic runs atomically

```
Redis queue:
  1. INCR user:123 → 5 → 4
  2. INCR user:123 → 4 → 3
  Result: 3 ✅
```

---

## 10. Redis Cluster (Scaling)

### Sharding by User ID

```
                    ┌──────────────────┐
                    │  Rate Limiter    │
                    └──────────────────┘
                            │
              hash(user_id) % num_shards
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
   ┌───────────┐      ┌───────────┐      ┌───────────┐
   │  Redis 0  │      │  Redis 1  │      │  Redis 2  │
   │ (users    │      │ (users    │      │ (users    │
   │  A-H)     │      │  I-P)     │      │  Q-Z)     │
   └───────────┘      └───────────┘      └───────────┘
```

### Sharding Implementation

```python
def get_redis_shard(user_id):
    shard_id = hash(user_id) % NUM_SHARDS
    return redis_cluster[shard_id]

def is_allowed(user_id):
    redis = get_redis_shard(user_id)
    return token_bucket_check(redis, user_id)
```

### Scaling Numbers

| Metric | Single Redis | 10-Node Cluster |
|--------|--------------|-----------------|
| Throughput | ~100K ops/sec | ~1M ops/sec |
| Memory | 64 GB max | 640 GB total |
| Failure Impact | 100% down | 10% users affected |

---

## 11. Redis Replication

### Replica Setup

```
┌─────────────────┐
│  Redis Primary  │ ← All writes + reads (for accuracy)
└─────────────────┘
         │
   Async replication
         │
   ┌─────┴─────┐
   ▼           ▼
┌──────┐   ┌──────┐
│ Rep1 │   │ Rep2 │  ← Standby for failover
└──────┘   └──────┘
```

### Replication Lag Problem

```
Time    Primary             Replica (1ms behind)
T1      INCR → 99           (still 98)
T2      INCR → 100          (still 99)
T3      (limit hit!)        (shows 99, allows!) ❌
```

### Best Practice

| Scenario | Read From |
|----------|-----------|
| Strict limits (payments) | Primary only |
| Soft limits (API throttle) | Replica OK (slight over-limit acceptable) |
| Failover | Replicas for HA, promote on failure |

---

## 12. Failure Handling

### What If Redis Is Down?

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=30)
def redis_check(user_id):
    return redis.hgetall(f"bucket:{user_id}")

def is_allowed(user_id):
    try:
        bucket = redis_check(user_id)
        return check_tokens(bucket)
    except CircuitBreakerError:
        # Redis is down - use local fallback
        log.warning("Redis unavailable, using local rate limit")
        return local_rate_limit(user_id)
```

### Fallback Options

| Option | Behavior | Use Case |
|--------|----------|----------|
| **Block all** | Deny requests | Ultra-sensitive (payments) |
| **Allow all** | Allow requests | Never recommended |
| **Local fallback** ✅ | In-memory rate limit per server | Most APIs |

### Local Fallback Limitation

```
Server 1: local_limit = 50
Server 2: local_limit = 50
User hits both: 100 requests allowed (over limit!)
```

**Mitigation:** Set local limit = global_limit / num_servers

---

## 13. API Response

### Success (Under Limit)

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 75
X-RateLimit-Reset: 1706998200
```

### Rate Limited (Over Limit)

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 30
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1706998200

{
    "error": "rate_limit_exceeded",
    "message": "Rate limit exceeded. Please retry after 30 seconds.",
    "retry_after": 30
}
```

### Header Descriptions

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Max requests allowed in window |
| `X-RateLimit-Remaining` | Requests left in current window |
| `X-RateLimit-Reset` | Unix timestamp when limit resets |
| `Retry-After` | Seconds to wait before retrying |

---

## 14. Distributed Rate Limiting Challenges

### Challenge 1: Clock Skew

Different servers may have slightly different clocks.

**Solution:** Use NTP synchronization; design algorithms tolerant to small clock differences.

### Challenge 2: Network Partitions

Some servers can't reach Redis.

**Solution:** Circuit breaker + local fallback.

### Challenge 3: Hot Keys

One user generates massive traffic.

**Solution:** Sharding ensures hot users are distributed.

---

## 15. Rate Limiting Strategies by Use Case

| Use Case | Strategy | Limits |
|----------|----------|--------|
| **Public API** | User-based | 100/min free, 1000/min paid |
| **Login Endpoint** | IP + Username | 5 failures/5min per IP/user |
| **Search API** | User + Global | User: 10/min, Global: 1000/min |
| **Webhook Delivery** | Per-endpoint | 100/sec per destination |
| **DDoS Protection** | IP-based | 1000/sec per IP |

---

## 16. Monitoring & Alerting

### Key Metrics

| Metric | Alert Threshold |
|--------|-----------------|
| Rate limit hits (429s) | > 1% of requests |
| Redis latency | P99 > 10ms |
| Redis memory usage | > 80% |
| Circuit breaker trips | Any |

### Logging

```python
def is_allowed(user_id):
    allowed = check_rate_limit(user_id)
    
    if not allowed:
        log.info(f"Rate limited: user={user_id}, "
                 f"endpoint={endpoint}, "
                 f"tier={tier}")
        metrics.increment("rate_limit.blocked", tags={"tier": tier})
    
    return allowed
```

---

## 17. Interview Talking Points

### Must Mention

1. **Placement:** API Gateway, not Load Balancer
2. **Algorithm:** Token Bucket (handles bursts, no boundary problem)
3. **Storage:** Redis (fast, atomic operations)
4. **Multi-dimensional:** User, IP, API key, endpoint
5. **Failure handling:** Local fallback with circuit breaker

### Bonus Points

1. **Lua scripts** for atomicity
2. **Redis Cluster** for horizontal scaling
3. **Consistent hashing** for sharding
4. **Response headers** (429, Retry-After, X-RateLimit-*)
5. **Tier-based limits** (free vs premium)

### Common Follow-Up Questions

| Question | Key Points |
|----------|------------|
| "Why not database?" | Too slow (10-20ms vs 0.5ms), lock contention |
| "What if Redis is down?" | Circuit breaker + local fallback |
| "How do you handle 1M req/sec?" | Redis Cluster with sharding |
| "Fixed window vs Token Bucket?" | Token Bucket avoids boundary problem |
| "How to prevent race conditions?" | Redis single-threaded + Lua scripts |

---

## 18. Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│                   RATE LIMITER CHEAT SHEET                      │
├─────────────────────────────────────────────────────────────────┤
│ Placement: API Gateway (between LB and app servers)             │
│ Algorithm: Token Bucket (capacity + refill rate)                │
│ Storage: Redis (in-memory, atomic, ~0.5ms latency)              │
├─────────────────────────────────────────────────────────────────┤
│ Redis Data:                                                     │
│   Key: "bucket:{user_id}:{endpoint}"                            │
│   Hash: { tokens: 75.5, last_update: 1706998083.456 }           │
├─────────────────────────────────────────────────────────────────┤
│ Multi-Dimensional:                                              │
│   1. Global:   "bucket:global:/api/search"    (10K/min)         │
│   2. Per-User: "bucket:user:123:/api/search"  (100/min)         │
│   3. Per-IP:   "bucket:ip:1.2.3.4:/api/search" (50/min)         │
├─────────────────────────────────────────────────────────────────┤
│ Scaling: Redis Cluster (sharding by user_id)                    │
│ HA: Primary + Replicas (read from Primary for accuracy)         │
│ Fallback: Local in-memory limit if Redis is down                │
├─────────────────────────────────────────────────────────────────┤
│ Response: 429 Too Many Requests                                 │
│   Headers: Retry-After, X-RateLimit-Limit/Remaining/Reset       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 19. Complete Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                          REQUEST FLOW                                │
└──────────────────────────────────────────────────────────────────────┘

   Client Request
        │
        ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                    API GATEWAY                              │
   │                                                             │
   │  1. Extract: user_id, IP, API_key, endpoint                │
   │  2. Get user tier (cached or User Service)                 │
   │  3. Build Redis keys for each limit type                   │
   └─────────────────────────────────────────────────────────────┘
        │
        ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                    REDIS CHECK                              │
   │                                                             │
   │  For each limit (global, user, IP):                        │
   │    - Run Token Bucket Lua script                           │
   │    - Check if tokens available                             │
   │    - Consume 1 token if allowed                            │
   └─────────────────────────────────────────────────────────────┘
        │
        ├─── All pass? ───▶ Forward to API Server ───▶ 200 OK
        │
        └─── Any fail? ───▶ Return 429 Too Many Requests
                           + Retry-After header
                           + X-RateLimit-* headers
```

---

*Last Updated: February 2026*
