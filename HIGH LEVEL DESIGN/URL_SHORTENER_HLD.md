# URL Shortener - High Level Design

## 1. Problem Statement

Design a URL shortening service (like bit.ly) that:
- Takes a long URL and returns a short URL
- Redirects short URLs to the original long URL
- Handles massive scale (millions of URLs, billions of redirects)

---

## 2. Functional Requirements

| Requirement | Description |
|-------------|-------------|
| **Shorten URL** | Given a long URL, generate a unique short URL |
| **Redirect** | Given a short URL, redirect to the original long URL |
| **Custom Alias** | (Optional) Allow users to specify custom short codes |
| **Expiration** | (Optional) URLs can have an expiry date |
| **Analytics** | (Optional) Track click counts, referrers, etc. |

---

## 3. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| **Availability** | 99.99% uptime (URL shortener is a critical redirect service) |
| **Latency** | < 100ms for redirects (P99) |
| **Scalability** | Handle 100M+ URLs, 10K+ redirects/second |
| **Durability** | Never lose a URL mapping |

---

## 4. Capacity Estimation

### Assumptions
- 100 million URLs created per month
- Read:Write ratio = 100:1 (reads dominate)
- Average long URL size = 500 bytes
- Short code length = 7 characters (Base62)

### Storage
```
100M URLs/month × 12 months × 5 years = 6 billion URLs

Each record:
- short_code: 7 bytes
- long_url: 500 bytes
- metadata: 100 bytes
- Total: ~600 bytes

Storage = 6B × 600 bytes = 3.6 TB
```

### Bandwidth
```
Writes: 100M / (30 × 24 × 3600) ≈ 40 URLs/second
Reads:  40 × 100 = 4,000 redirects/second (average)
Peak:   10,000+ redirects/second
```

### Short Code Space
```
Base62 (a-z, A-Z, 0-9) with 7 characters:
62^7 = 3.5 trillion unique codes ✅ (More than enough)
```

---

## 5. System Architecture

```
                                    ┌─────────────────────┐
                                    │   URL Shortener     │
                                    │   Architecture      │
                                    └─────────────────────┘

┌──────────┐     ┌──────────────┐     ┌─────────────────┐     ┌─────────────┐
│  Client  │────▶│ Load Balancer│────▶│  App Servers    │────▶│   Cache     │
│ (Browser)│     │   (L7/ALB)   │     │  (Stateless)    │     │  (Redis)    │
└──────────┘     └──────────────┘     └─────────────────┘     └─────────────┘
                                              │                      │
                                              │                      │
                                              ▼                      ▼
                                      ┌─────────────────┐     ┌─────────────┐
                                      │   Database      │     │  Analytics  │
                                      │ (DynamoDB/SQL)  │     │  (Kafka →   │
                                      └─────────────────┘     │  ClickHouse)│
                                              ▲               └─────────────┘
                                              │
                                      ┌─────────────────┐
                                      │   Zookeeper     │
                                      │ (ID Generation) │
                                      └─────────────────┘
```

---

## 6. API Design

### Create Short URL
```http
POST /api/shorten
Content-Type: application/json

Request:
{
    "long_url": "https://example.com/very/long/path?query=value",
    "custom_alias": "my-link",      // Optional
    "expires_at": "2026-12-31T23:59:59Z"  // Optional
}

Response:
{
    "short_url": "https://short.url/abc123",
    "short_code": "abc123",
    "expires_at": "2026-12-31T23:59:59Z"
}
```

### Redirect
```http
GET /{short_code}
→ HTTP 301/302 Redirect to long_url

GET /abc123
→ 301 Redirect: Location: https://example.com/very/long/path?query=value
```

### 301 vs 302 Redirect

| Code | Type | Use Case |
|------|------|----------|
| **301** | Permanent | Browser caches redirect; reduces server load; bad for analytics |
| **302** | Temporary | Every click hits server; good for analytics; more load |

**Recommendation:** Use **302** if you need click tracking, **301** for pure shortening.

---

## 7. Database Design

### Schema (SQL)
```sql
CREATE TABLE short_urls (
    short_code   VARCHAR(10) PRIMARY KEY,
    long_url     TEXT NOT NULL,
    user_id      BIGINT,
    created_at   TIMESTAMP DEFAULT NOW(),
    expires_at   TIMESTAMP,
    click_count  BIGINT DEFAULT 0
);

-- Index for duplicate detection (optional)
CREATE INDEX idx_long_url_hash ON short_urls (MD5(long_url));
```

### Schema (DynamoDB)
```
Table: short_urls
- Partition Key: short_code (String)
- Attributes: long_url, user_id, created_at, expires_at
- TTL Attribute: expires_at (for automatic expiration)

GSI (for user's URLs):
- Partition Key: user_id
- Sort Key: created_at
```

### SQL vs NoSQL Decision

| Factor | SQL (PostgreSQL) | NoSQL (DynamoDB) |
|--------|------------------|------------------|
| **Scale** | Vertical (limited) | Horizontal (unlimited) |
| **Schema** | Fixed, ACID | Flexible, eventual consistency |
| **Cost at Scale** | Higher (provisioned) | Pay-per-request |
| **Joins** | Supported | Not supported |
| **Best For** | < 10M URLs | > 100M URLs |

**Recommendation:** Use **DynamoDB** for massive scale, **PostgreSQL** for simpler setups with analytics needs.

---

## 8. Short Code Generation

### Option 1: Counter + Base62 Encoding (Recommended)

```python
def generate_short_code(counter_value):
    """Convert integer to Base62 string"""
    chars = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    result = []
    while counter_value > 0:
        result.append(chars[counter_value % 62])
        counter_value //= 62
    return ''.join(reversed(result)).zfill(7)

# Example: 123456789 → "8M0kX"
```

### Distributed Counter with Zookeeper

```
┌─────────────────────────────────────────────────────────┐
│                       ZOOKEEPER                         │
│          (Stores: next_available_range = 3001)          │
└─────────────────────────────────────────────────────────┘
        │                    │                    │
        ▼                    ▼                    ▼
   ┌─────────┐         ┌─────────┐         ┌─────────┐
   │Server 1 │         │Server 2 │         │Server 3 │
   │Range:   │         │Range:   │         │Range:   │
   │1-1000   │         │1001-2000│         │2001-3000│
   └─────────┘         └─────────┘         └─────────┘
```

**Flow:**
1. Server requests a range from Zookeeper (e.g., 1-1000)
2. Server generates codes locally from that range
3. When exhausted, requests a new range
4. Zookeeper ensures no overlapping ranges

### Comparison of Approaches

| Approach | Pros | Cons |
|----------|------|------|
| **Counter + Zookeeper** | Guaranteed unique, compact codes | Needs coordination service |
| **Random String** | Simple, no coordination | Must check for collisions |
| **Hash (MD5/SHA)** | Deterministic | Collisions possible; predictable |
| **Snowflake ID** | No coordination, unique | Larger (64-bit), complex |

---

## 9. Caching Strategy

### Cache Placement
```
User → Load Balancer → App Server → [REDIS CACHE] → Database
```

### Read Flow (Redirect)
```
1. User requests: GET /abc123
2. App Server checks Redis: "Do you have abc123?"
3. Cache Hit? → Return long_url (fast, ~1ms)
4. Cache Miss? → Query Database
                → Write to Redis (with TTL)
                → Return long_url
```

### Cache Configuration

```python
# Redis TTL Strategy
def get_cache_ttl(expires_at):
    if expires_at is None:
        return 24 * 60 * 60  # 24 hours for permanent URLs
    else:
        remaining = expires_at - now()
        return min(remaining, 24 * 60 * 60)  # min(expiry, 24h)
```

### Cache Sizing
```
Top 20% of URLs get 80% of traffic (Pareto principle)
Cache 20% of 6B URLs = 1.2B entries

Each entry: ~600 bytes
Cache size: 1.2B × 600 = 720 GB

Use Redis Cluster with sharding across multiple nodes.
```

---

## 10. URL Expiration Handling

### Two-Pronged Approach

#### 1. Lazy Deletion (Read-Time Check)
```python
def redirect(short_code):
    url_data = cache.get(short_code) or db.get(short_code)
    
    if url_data.expires_at and url_data.expires_at < now():
        return 404  # URL expired
    
    return redirect_to(url_data.long_url)
```

#### 2. Active Cleanup (Background Job)
```python
# Runs every hour via cron/Lambda
def cleanup_expired_urls():
    while True:
        # Delete in small batches to avoid DB locks
        deleted = db.execute("""
            DELETE FROM short_urls 
            WHERE expires_at < NOW() 
            LIMIT 1000
        """)
        
        if deleted == 0:
            break
        
        sleep(0.1)  # Rate limit to prevent DB overload
```

### NoSQL Native Expiration

| Database | Expiration Method |
|----------|-------------------|
| **DynamoDB** | TTL attribute (auto-deletes within 48 hours) |
| **Cassandra** | TTL on INSERT (`USING TTL 2592000`) |
| **MongoDB** | TTL Index on `expires_at` field |
| **Redis** | Built-in EXPIRE/TTL commands |

---

## 11. NoSQL Partitioning Deep Dive

### How Partitioning Works

```
┌──────────────────────────────────────────────────────┐
│                    YOUR APPLICATION                  │
└──────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │    NoSQL Cluster      │
              │   (Router / Proxy)    │
              └───────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
   ┌───────────┐    ┌───────────┐    ┌───────────┐
   │Partition 0│    │Partition 1│    │Partition 2│
   │ hash 0-33 │    │ hash 34-66│    │ hash 67-99│
   └───────────┘    └───────────┘    └───────────┘
```

### Partition Key Selection

| Access Pattern | Partition Key | Sort Key |
|----------------|---------------|----------|
| Redirect: `GET /abc123` | `short_code` | (none) |
| User's URLs: `GET /users/42/urls` | `user_id` | `created_at` |

### Hot Partition Problem

**Bad:** Partition by `country` → India gets 60% traffic  
**Good:** Partition by `short_code` → Random distribution ✅

### Consistent Hashing
```
hash("abc123") → 42 → Partition (42 % 3) = 0 → Server A
hash("xyz789") → 97 → Partition (97 % 3) = 1 → Server B
```

---

## 12. Duplicate URL Handling

### Option 1: Deduplicate (Same URL = Same Short Code)

```python
def create_short_url(long_url):
    # Check if already exists
    existing = db.query_by_index("long_url_hash", hash(long_url))
    if existing:
        return existing.short_code
    
    # Create new
    short_code = generate_new_code()
    db.insert(short_code, long_url)
    return short_code
```

| Pros | Cons |
|------|------|
| Saves storage | Needs secondary index on `long_url` |
| Unified analytics | Users can't have "private" links |

### Option 2: Always New (Different Users = Different Codes)

```python
def create_short_url(long_url, user_id):
    short_code = generate_new_code()  # Always new
    db.insert(short_code, long_url, user_id)
    return short_code
```

| Pros | Cons |
|------|------|
| No secondary index | Duplicate storage |
| User-specific analytics | More complex aggregation |

**Recommendation:** 
- **Consumer product:** Deduplicate
- **Enterprise/campaign tracking:** Always new

---

## 13. Analytics Pipeline

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ App Server  │───▶│   Kafka     │───▶│  Consumer   │───▶│ ClickHouse  │
│ (Log click) │    │  (Buffer)   │    │ (Process)   │    │ (Analytics) │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Click Event Schema
```json
{
    "short_code": "abc123",
    "long_url": "https://...",
    "timestamp": "2026-01-15T10:30:00Z",
    "user_agent": "Mozilla/5.0...",
    "ip_address": "192.168.1.1",
    "referrer": "https://twitter.com",
    "country": "India"
}
```

---

## 14. High Availability & Fault Tolerance

### Database Replication
```
┌────────────┐     ┌────────────┐     ┌────────────┐
│  Primary   │────▶│  Replica 1 │     │  Replica 2 │
│  (Writes)  │     │   (Reads)  │     │   (Reads)  │
└────────────┘     └────────────┘     └────────────┘
```

### Multi-Region Deployment
```
┌─────────────────┐          ┌─────────────────┐
│   US-East       │◀────────▶│   EU-West       │
│ (Primary)       │   Sync   │ (Secondary)     │
└─────────────────┘          └─────────────────┘
```

### Failure Scenarios

| Failure | Solution |
|---------|----------|
| App server crash | Load balancer routes to healthy servers |
| Redis crash | Read from database; Redis Cluster failover |
| Database crash | Failover to replica; promote to primary |
| Zookeeper crash | Zookeeper quorum (3+ nodes); leader election |

---

## 15. Security Considerations

| Threat | Mitigation |
|--------|------------|
| **Malicious URLs** | Scan with Google Safe Browsing API before creation |
| **Enumeration Attack** | Random codes (not sequential); rate limiting |
| **DDoS** | Rate limiting; CDN (CloudFlare); captcha for creation |
| **Private URL Guessing** | Longer codes (10+ chars) for sensitive links |

---

## 16. Interview Talking Points

### Must Mention
1. **Scale estimation** (100M URLs, 10K RPS reads)
2. **Short code generation** (Counter + Base62 + Zookeeper)
3. **Caching** (Redis between app and DB)
4. **Read vs Write path** (302 redirect flow)
5. **Expiration handling** (Lazy + Active cleanup)

### Bonus Points
1. **Consistent hashing** for NoSQL partitioning
2. **301 vs 302** trade-off
3. **Analytics pipeline** with Kafka
4. **Multi-region** for low latency
5. **Security** (malicious URL scanning)

### Common Follow-Up Questions

| Question | Key Points |
|----------|------------|
| "How do you handle 100M expired URLs?" | Batched deletes, table partitioning, NoSQL TTL |
| "What if Zookeeper is down?" | Pre-fetch ranges; fallback to random with collision check |
| "How do you prevent duplicate short codes?" | Zookeeper range allocation; unique constraint in DB |
| "What if same URL is shortened twice?" | Dedupe with hash index OR always new (use case dependent) |

---

## 17. Quick Reference Card

```
┌─────────────────────────────────────────────────────────────┐
│                    URL SHORTENER CHEAT SHEET                │
├─────────────────────────────────────────────────────────────┤
│ Scale: 100M URLs, 10K reads/sec, 40 writes/sec              │
│ Storage: ~3.6 TB for 5 years                                │
│ Short Code: 7 chars Base62 = 3.5 trillion unique codes      │
├─────────────────────────────────────────────────────────────┤
│ WRITE: User → LB → App → Zookeeper (get ID) → DB → Cache    │
│ READ:  User → LB → App → Cache (hit?) → DB → 302 Redirect   │
├─────────────────────────────────────────────────────────────┤
│ DB: DynamoDB (Partition Key: short_code, TTL: expires_at)   │
│ Cache: Redis Cluster (TTL = min(expiry, 24h))               │
│ ID Gen: Zookeeper range allocation + Base62 encoding        │
├─────────────────────────────────────────────────────────────┤
│ Expiry: Lazy check on read + Background cleanup job         │
│ Analytics: Kafka → ClickHouse for click tracking            │
└─────────────────────────────────────────────────────────────┘
```

---

*Last Updated: February 2026*
