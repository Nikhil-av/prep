# Rate Limiter — Complete Deep Dive

> Interview-ready documentation with all details

---

# 1. FUNCTIONAL REQUIREMENTS

## Priority Levels
- **P0** = Must have (core functionality)
- **P1** = Should have (important features)
- **P2** = Nice to have (enhancements)

## Feature List

| # | Feature | Priority | Description |
|---|---------|----------|-------------|
| 1 | **Request Limiting** | P0 | Limit requests per user/IP/API key |
| 2 | **Multiple Algorithms** | P0 | Token bucket, sliding window, fixed window |
| 3 | **Distributed** | P0 | Work across multiple servers |
| 4 | **Low Latency** | P0 | < 1ms overhead per request |
| 5 | **Clear Headers** | P1 | Return remaining quota, reset time |
| 6 | **Configurable Limits** | P1 | Set different limits per endpoint |
| 7 | **Graceful Degradation** | P1 | Work even if Redis is down |
| 8 | **Multi-tier Limits** | P2 | Minute + hour + day limits |
| 9 | **Analytics** | P2 | Track blocked requests |

---

# 2. NON-FUNCTIONAL REQUIREMENTS

## Latency

| Operation | Target | Rationale |
|-----------|--------|-----------|
| Rate check | < 1ms | Must not slow down API |
| Header injection | < 0.1ms | Trivial overhead |

## Throughput

| Metric | Target |
|--------|--------|
| Checks/second | 10 million+ |
| Concurrent keys | 100 million |

## Availability

| Component | Target | Strategy |
|-----------|--------|----------|
| Rate limiter | 99.99% | Redis cluster, fallback |
| Fail-open | Yes | Allow if Redis down |

## Consistency

| Requirement | Level |
|-------------|-------|
| Exact count | Approximate OK (±5%) |
| Fairness | Best effort |

---

# 3. CAPACITY PLANNING

## Step-by-Step Calculation Guide

### Step 1: Define Traffic

```
API requests/second:    100,000 QPS
Unique users:           10 million active
Rate limit:             100 requests/minute per user
```

---

### Step 2: Storage Calculation

**Per User:**
```
Token bucket data:      24 bytes
  - user_id:            8 bytes
  - tokens:             8 bytes (double)
  - last_refill:        8 bytes (timestamp)
```

**Total:**
```
Active users:           10 million
Storage:                10M × 24 bytes = 240 MB

With overhead:          ~500 MB (Redis overhead, cluster)
```

---

### Step 3: Redis Operations

```
Each request:           2 operations (GET + INCR/SET)
QPS:                    100,000
Redis ops/sec:          200,000

Per Redis node:         100,000 ops/sec capacity
Nodes needed:           2-3 (with replication: 6)
```

---

### Step 4: Network Bandwidth

```
Request size:           ~100 bytes (key + value)
Response size:          ~50 bytes
Per operation:          150 bytes

Bandwidth:              200K ops × 150 bytes = 30 MB/s = 240 Mbps
```

---

### Quick Reference: Capacity Cheat Sheet

```
┌────────────────────────────────────────────────────────────────────────┐
│                    RATE LIMITER CAPACITY CHEAT SHEET                   │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  TRAFFIC                                                               │
│  • QPS: 100K    Users: 10M    Limit: 100 req/min                      │
│                                                                        │
│  STORAGE                                                               │
│  • Per user: 24 bytes    Total: 500 MB                                │
│                                                                        │
│  REDIS                                                                 │
│  • 200K ops/sec    3 masters + 3 replicas                             │
│                                                                        │
│  LATENCY                                                               │
│  • Overhead: < 1ms    Network RTT: < 0.5ms                            │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

# 4. DETAILED HLD DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    RATE LIMITER - DETAILED ARCHITECTURE                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                           CLIENTS
                    ┌─────────────────────────────────────────────────────────┐
                    │        Mobile App         Web App         API Client   │
                    └─────────────────────────────────────────────────────────┘
                                                 │
                                    ┌────────────▼────────────┐
                                    │     LOAD BALANCER       │
                                    │    (AWS ALB / Nginx)    │
                                    └────────────┬────────────┘
                                                 │
          ┌──────────────────────────────────────┼──────────────────────────────────────┐
          │                                      │                                      │
          ▼                                      ▼                                      ▼
┌──────────────────┐                  ┌──────────────────┐                  ┌──────────────────┐
│  API GATEWAY 1   │                  │  API GATEWAY 2   │                  │  API GATEWAY N   │
│                  │                  │                  │                  │                  │
│  ┌────────────┐  │                  │  ┌────────────┐  │                  │  ┌────────────┐  │
│  │RATE LIMITER│  │                  │  │RATE LIMITER│  │                  │  │RATE LIMITER│  │
│  │ MIDDLEWARE │  │                  │  │ MIDDLEWARE │  │                  │  │ MIDDLEWARE │  │
│  └─────┬──────┘  │                  │  └─────┬──────┘  │                  │  └─────┬──────┘  │
│        │         │                  │        │         │                  │        │         │
│  [50 instances]  │                  │                  │                  │                  │
└────────┼─────────┘                  └────────┼─────────┘                  └────────┼─────────┘
         │                                     │                                     │
         └─────────────────────────────────────┼─────────────────────────────────────┘
                                               │
                                               ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │                    REDIS CLUSTER                        │
                    │                                                         │
                    │   ┌─────────┐    ┌─────────┐    ┌─────────┐            │
                    │   │ Master 1│    │ Master 2│    │ Master 3│            │
                    │   │(Shard 1)│    │(Shard 2)│    │(Shard 3)│            │
                    │   └────┬────┘    └────┬────┘    └────┬────┘            │
                    │        │              │              │                  │
                    │   ┌────▼────┐    ┌────▼────┐    ┌────▼────┐            │
                    │   │Replica 1│    │Replica 2│    │Replica 3│            │
                    │   └─────────┘    └─────────┘    └─────────┘            │
                    │                                                         │
                    │   Data:                                                 │
                    │   - rate:user:{id}:minute → token count                │
                    │   - rate:ip:{ip}:minute → request count                │
                    │   - rate:api:{key}:minute → request count              │
                    │                                                         │
                    │   Total Memory: 500 MB                                  │
                    │   TTL: 60 seconds (auto-cleanup)                       │
                    │                                                         │
                    └─────────────────────────────────────────────────────────┘
                                               │
                                               │ If allowed
                                               ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │                   BACKEND SERVICES                      │
                    │                                                         │
                    │   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
                    │   │ User Service│  │Order Service│  │Search Service│   │
                    │   └─────────────┘  └─────────────┘  └─────────────┘    │
                    │                                                         │
                    └─────────────────────────────────────────────────────────┘
```

---

# 5. REQUEST FLOWS

## Flow 1: Token Bucket Algorithm

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              TOKEN BUCKET FLOW                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User sends API request

1. MIDDLEWARE extracts identifier
   • user_id from JWT token
   • OR IP address
   • OR API key from header
           │
           ▼
2. REDIS Lua script (atomic):
   
   local key = "rate:" .. user_id
   local tokens = redis.call("GET", key)
   local last_refill = redis.call("GET", key .. ":time")
   
   -- Calculate tokens to add (refill rate: 10/sec)
   local now = ARGV[1]
   local elapsed = now - last_refill
   local new_tokens = min(100, tokens + elapsed * 10)
   
   if new_tokens >= 1 then
       -- Allow request
       redis.call("SET", key, new_tokens - 1)
       redis.call("SET", key .. ":time", now)
       return {1, new_tokens - 1}  -- allowed, remaining
   else
       -- Reject request
       return {0, 0}  -- rejected
   end
           │
           ▼
3. MIDDLEWARE processes result
   If allowed:
     • Add headers: X-RateLimit-Remaining: 45
     • Forward to backend
   
   If rejected:
     • Return 429 Too Many Requests
     • Add headers: Retry-After: 6
```

---

## Flow 2: Sliding Window Log

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SLIDING WINDOW LOG FLOW                                                │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Limit: 100 requests per minute

1. Store each request timestamp in sorted set
   ZADD rate:user:123 <timestamp> <request_id>

2. Remove old entries (outside window)
   ZREMRANGEBYSCORE rate:user:123 0 (now - 60)

3. Count entries in window
   ZCARD rate:user:123

4. Decision:
   If count < 100 → Allow
   If count >= 100 → Reject (429)

Trade-offs:
  ✅ Most accurate
  ❌ Higher memory (stores all timestamps)
  ❌ More operations per request
```

---

## Flow 3: Sliding Window Counter (Hybrid)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SLIDING WINDOW COUNTER FLOW                                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Combines fixed windows with sliding logic:

Current time: 1:15:30 (second 30 of minute 15)
Limit: 100 requests/minute

1. Get counts for current and previous window
   current_window (1:15) = 40 requests
   previous_window (1:14) = 80 requests

2. Calculate weighted count
   weight = (60 - 30) / 60 = 0.5  (30 sec into current minute)
   
   estimated = (previous × (1 - weight)) + current
   estimated = (80 × 0.5) + 40 = 40 + 40 = 80

3. Decision:
   80 < 100 → Allow request
   Increment current window: INCR rate:user:123:1:15

Trade-offs:
  ✅ Memory efficient (only 2 counters)
  ✅ Smooth limiting (no edge bursts)
  ❌ Approximate (not exact)
```

---

## Flow 4: Fixed Window Counter (Simple)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              FIXED WINDOW COUNTER FLOW                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

1. Create key with minute granularity
   key = "rate:user:123:2024-02-04-23:26"

2. Atomic increment with TTL
   count = INCR key
   EXPIRE key 60

3. Decision:
   If count <= 100 → Allow
   If count > 100 → Reject (429)

Trade-offs:
  ✅ Simple, fast
  ✅ Low memory
  ❌ Edge case: 200 requests in 2 seconds
     (100 at 1:59:59 + 100 at 2:00:01)
```

---

## Edge Cases

### Case: Redis Down (Fail-Open Strategy)

```
1. Rate limiter tries Redis → Timeout or connection error

2. Fallback options:
   A) ALLOW all requests (fail-open)
      - Protects user experience
      - Risk: Can overwhelm backend
   
   B) DENY all requests (fail-closed)
      - Protects backend
      - Risk: Blocks legitimate users
   
   C) LOCAL rate limiting (in-memory)
      - Each server limits independently
      - Less accurate but better than nothing

Best practice: Option A with monitoring alerts
```

### Case: Burst Tolerance

```
User config:
  - Rate: 100 requests/minute (1.67/sec)
  - Burst: 20 requests allowed

Token bucket implementation:
  - Capacity: 20 tokens (max burst)
  - Refill rate: 1.67 tokens/sec
  
User behavior:
  - Can send 20 requests instantly (uses burst)
  - Then must wait for refill
  - Still averages 100/minute over time
```

### Case: Distributed Sync Lag

```
Problem:
  - User hits Server A: count = 99
  - User hits Server B: count = 99 (before sync)
  - Both allow → User made 200 requests!

Solutions:
  1. Redis Cluster (shared state) ← Recommended
  2. Accept approximate limiting (±5%)
  3. Sticky sessions (same user → same server)
```

---

## Algorithm Comparison

| Algorithm | Memory | Accuracy | Complexity | Best For |
|-----------|--------|----------|------------|----------|
| **Token Bucket** | Low | High | Medium | Burst + avg rate |
| **Leaky Bucket** | Low | High | Medium | Smooth output |
| **Fixed Window** | Very Low | Low | Low | Simple APIs |
| **Sliding Log** | High | Highest | High | Billing/critical |
| **Sliding Counter** | Low | High | Medium | General use |

---

## Response Headers

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1707082080  (Unix timestamp)

--OR--

HTTP/1.1 429 Too Many Requests
Retry-After: 30  (seconds)
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1707082080
```

---

## Error Handling Summary

| Scenario | Handling |
|----------|----------|
| Redis timeout | Fail-open (allow request) |
| Key expired | Create new with SETNX |
| Race condition | Use Lua scripts (atomic) |
| Clock skew | Use Redis TIME command |
| Memory pressure | TTL ensures auto-cleanup |
