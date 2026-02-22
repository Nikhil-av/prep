# URL Shortener — Complete Deep Dive

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
| 1 | **Shorten URL** | P0 | Convert long URL to short code |
| 2 | **Redirect** | P0 | Redirect short URL to original |
| 3 | **High Availability** | P0 | 99.99% uptime for redirects |
| 4 | **Low Latency** | P0 | < 50ms redirect time |
| 5 | **Custom Aliases** | P1 | User-defined short codes |
| 6 | **Expiration** | P1 | URLs expire after time/clicks |
| 7 | **Analytics** | P1 | Click counts, referrers, geo |
| 8 | **API Access** | P1 | Programmatic URL creation |
| 9 | **QR Codes** | P2 | Generate QR for short URLs |
| 10 | **Link Preview** | P2 | Show destination before redirect |

---

# 2. NON-FUNCTIONAL REQUIREMENTS

## Latency

| Operation | Target | Rationale |
|-----------|--------|-----------|
| Redirect (cache hit) | < 10ms | Instant user experience |
| Redirect (cache miss) | < 50ms | Still fast |
| URL creation | < 100ms | OK for write operation |

## Throughput

| Metric | Target |
|--------|--------|
| Redirects/second | 100,000+ |
| URL creations/second | 1,000 |
| Read:Write ratio | 100:1 |

## Availability

| Component | Target | Strategy |
|-----------|--------|----------|
| Redirect service | 99.99% | Multi-region, CDN |
| Creation service | 99.9% | Can tolerate brief outages |

## Consistency

| Requirement | Level |
|-------------|-------|
| New URL availability | Eventually consistent (< 1 sec) |
| Analytics | Eventually consistent (minutes OK) |

---

# 3. CAPACITY PLANNING

## Step-by-Step Calculation Guide

### Step 1: Define Traffic

```
URL creations/month:    100 million
URL creations/day:      100M / 30 = 3.3 million
URL creations/second:   3.3M / 86400 = ~40 QPS

Redirects/day:          3 billion (100× more reads)
Redirects/second:       3B / 86400 = ~35,000 QPS
Peak redirects:         35K × 3 = 105,000 QPS
```

**Formula:**
```
Read_QPS = Write_QPS × Read_Write_Ratio
Peak_QPS = Average_QPS × 3
```

---

### Step 2: URL Code Space

**How many unique short codes do we need?**

```
URLs/year:              100M × 12 = 1.2 billion
URLs over 10 years:     12 billion total
Safety margin (10×):    120 billion unique codes needed
```

**Code design:**
```
Characters: [a-z, A-Z, 0-9] = 62 characters
Code length: 7 characters
Total combinations: 62^7 = 3.5 trillion ✅

(More than enough for 120 billion URLs)
```

---

### Step 3: Storage Calculation

**Per URL:**
```
short_code:     7 bytes
long_url:       200 bytes (average)
user_id:        8 bytes
created_at:     8 bytes
expires_at:     8 bytes
click_count:    8 bytes
metadata:       ~50 bytes
───────────────────────
Total:          ~300 bytes per URL
```

**Total Storage:**
```
URLs over 10 years:     12 billion
Storage:                12B × 300 bytes = 3.6 TB

With replication (3×):  10.8 TB
With indexes:           ~15 TB total
```

---

### Step 4: Cache Sizing (80/20 Rule)

```
80% of traffic hits 20% of URLs

Hot URLs:               12B × 0.2 = 2.4 billion
Cache size:             2.4B × 300 bytes = 720 GB

Practical cache:        1 TB (with overhead)
Redis nodes:            20 nodes × 50 GB each
```

---

### Step 5: Bandwidth Calculation

```
Redirect response size: ~500 bytes (301 + headers)
Peak redirects:         100,000/sec
Bandwidth:              100K × 500 = 50 MB/s = 400 Mbps
```

---

### Quick Reference: Capacity Cheat Sheet

```
┌────────────────────────────────────────────────────────────────────────┐
│                    URL SHORTENER CAPACITY CHEAT SHEET                  │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  TRAFFIC                                                               │
│  • Writes: 40 QPS    Reads: 100K QPS peak                             │
│  • Read:Write = 100:1                                                  │
│                                                                        │
│  SHORT CODES                                                           │
│  • Length: 7 chars    Characters: 62                                  │
│  • Total: 3.5 trillion possible codes                                 │
│                                                                        │
│  STORAGE                                                               │
│  • Per URL: 300 bytes    Total: 15 TB (10 years)                      │
│                                                                        │
│  CACHE                                                                 │
│  • Size: 1 TB    Nodes: 20 Redis nodes                                │
│  • Hit rate: 95%+                                                      │
│                                                                        │
│  SERVERS                                                               │
│  • Redirect: 30 servers    Creation: 5 servers                        │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

# 4. DETAILED HLD DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    URL SHORTENER - DETAILED ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                           CLIENTS
                    ┌─────────────────────────────────────────────────────────┐
                    │        Browser           Mobile App          API       │
                    └─────────────────────────────────────────────────────────┘
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    │                            │                            │
                    ▼                            ▼                            ▼
          ┌─────────────────┐          ┌─────────────────┐          ┌─────────────────┐
          │   DNS / GSLB    │          │    CDN EDGE     │          │    CDN EDGE     │
          │                 │          │   (US-East)     │          │   (EU-West)     │
          │ Routes to       │          │                 │          │                 │
          │ nearest region  │          │ Cache redirects │          │ Cache redirects │
          └────────┬────────┘          │ for hot URLs    │          │ 95%+ hit rate   │
                   │                   └────────┬────────┘          └────────┬────────┘
                   │                            │                            │
                   └────────────────────────────┼────────────────────────────┘
                                                │
                                    ┌───────────▼───────────┐
                                    │    LOAD BALANCER      │
                                    │   (AWS ALB/Nginx)     │
                                    └───────────┬───────────┘
                                                │
                    ┌───────────────────────────┼───────────────────────────┐
                    │ READ PATH                 │           WRITE PATH      │
                    ▼                           │                           ▼
          ┌─────────────────┐                   │                 ┌─────────────────┐
          │  REDIRECT SVC   │                   │                 │  SHORT URL SVC  │
          │                 │                   │                 │                 │
          │  [30 instances] │                   │                 │  [5 instances]  │
          │  Stateless      │                   │                 │  Stateless      │
          │  Auto-scaling   │                   │                 │                 │
          └────────┬────────┘                   │                 └────────┬────────┘
                   │                            │                          │
                   ▼                            │                          ▼
          ┌─────────────────────────────────────┴──────────────────────────────────────┐
          │                              REDIS CLUSTER                                 │
          │                                                                            │
          │   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐               │
          │   │ Shard 1 │    │ Shard 2 │    │ Shard 3 │    │ Shard N │               │
          │   │(Master) │    │(Master) │    │(Master) │    │(Master) │               │
          │   └────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘               │
          │        │              │              │              │                     │
          │   ┌────▼────┐    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐               │
          │   │ Replica │    │ Replica │    │ Replica │    │ Replica │               │
          │   └─────────┘    └─────────┘    └─────────┘    └─────────┘               │
          │                                                                            │
          │   Key pattern: short:{code} → long_url                                    │
          │   Total: 20 nodes, 1 TB memory                                            │
          │   TTL: None (or per-URL expiry)                                           │
          └─────────────────────────────────────────────────────────────────────────────┘
                   │                                                       │
                   │ Cache miss                                           │ Write-through
                   ▼                                                       ▼
          ┌─────────────────────────────────────────────────────────────────────────────┐
          │                              DATABASE LAYER                                │
          ├─────────────────────────────────────────────────────────────────────────────┤
          │                                                                            │
          │   MYSQL / POSTGRESQL                                                       │
          │   (Sharded by short_code hash)                                            │
          │                                                                            │
          │   ┌─────────────────────────────────────────────────────────────────────┐ │
          │   │  TABLE: urls                                                        │ │
          │   │  ───────────────────────────────────────────────────────────────── │ │
          │   │  short_code (PK, indexed)                                          │ │
          │   │  long_url                                                           │ │
          │   │  user_id (indexed)                                                  │ │
          │   │  created_at                                                         │ │
          │   │  expires_at (indexed for cleanup)                                   │ │
          │   │  click_count                                                        │ │
          │   └─────────────────────────────────────────────────────────────────────┘ │
          │                                                                            │
          │   Shards: 10 (based on short_code hash)                                   │
          │   Primary + 2 Read Replicas per shard                                     │
          │   Total: 30 database nodes                                                 │
          │                                                                            │
          └─────────────────────────────────────────────────────────────────────────────┘
                   │
                   │ Analytics events
                   ▼
          ┌─────────────────────────────────────────────────────────────────────────────┐
          │                              ANALYTICS PIPELINE                            │
          ├─────────────────────────────────────────────────────────────────────────────┤
          │                                                                            │
          │   KAFKA                    SPARK                    CLICKHOUSE            │
          │   (Events)                 (Processing)             (Analytics DB)        │
          │                                                                            │
          │   Topics:                  • Aggregate clicks        • Time-series data   │
          │   - click_events           • Geo distribution        • Fast OLAP queries  │
          │   - url_created            • Referrer analysis       • Real-time dashboard │
          │                                                                            │
          │   20 partitions            Batch every 5 min         1B rows/month        │
          │                                                                            │
          └─────────────────────────────────────────────────────────────────────────────┘
                   │
                   ▼
          ┌─────────────────────────────────────────────────────────────────────────────┐
          │                              ID GENERATION SERVICE                         │
          ├─────────────────────────────────────────────────────────────────────────────┤
          │                                                                            │
          │   Option A: Counter + Base62                                               │
          │   ┌─────────────┐    Counter: 1234567890                                  │
          │   │  Zookeeper  │ → Base62:  "1Ly7zT"                                     │
          │   │  Counter    │                                                          │
          │   └─────────────┘    Pre-fetch ranges for each server                     │
          │                                                                            │
          │   Option B: Random + Collision Check                                       │
          │                      Generate → Check DB → Retry if exists                │
          │                                                                            │
          │   Option C: MD5 Hash + Truncate                                           │
          │                      MD5(long_url) → First 7 chars                        │
          │                                                                            │
          └─────────────────────────────────────────────────────────────────────────────┘
```

---

# 5. REQUEST FLOWS

## Flow 1: Create Short URL (Happy Path)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              CREATE SHORT URL FLOW                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User wants to shorten: https://example.com/very/long/path?param=value

1. CLIENT → API GATEWAY
   POST /api/shorten
   {
     "long_url": "https://example.com/very/long/path?param=value",
     "custom_alias": null,  // optional
     "expires_in": 86400    // optional, seconds
   }
           │
           ▼
2. VALIDATE INPUT
   • Is URL valid format?
   • Is URL reachable? (optional HEAD request)
   • Is user authenticated?
   • Rate limit check
           │
           ▼
3. CHECK FOR DUPLICATES
   • Query: SELECT short_code FROM urls WHERE long_url = ?
   • If exists AND same user → Return existing short code
           │
           ▼
4. GENERATE SHORT CODE
   
   Method A: Counter-based
   ┌────────────────────────────────────────────────────┐
   │ Get next ID from Zookeeper counter: 1234567890    │
   │ Convert to Base62: 1Ly7zT                         │
   │ Pad to 7 chars if needed                          │
   └────────────────────────────────────────────────────┘
   
   Method B: Random
   ┌────────────────────────────────────────────────────┐
   │ Generate random 7-char string: "Xk9pL2m"          │
   │ Check if exists in DB                             │
   │ If collision → Retry (rare with 3.5T combinations)│
   └────────────────────────────────────────────────────┘
           │
           ▼
5. STORE IN DATABASE
   INSERT INTO urls (short_code, long_url, user_id, created_at, expires_at)
   VALUES ('Xk9pL2m', 'https://example.com/...', 'user_123', NOW(), NOW() + 86400)
           │
           ▼
6. WRITE-THROUGH TO CACHE
   SET short:Xk9pL2m "https://example.com/..." EX 86400
           │
           ▼
7. RETURN RESPONSE
   {
     "short_url": "https://short.ly/Xk9pL2m",
     "long_url": "https://example.com/...",
     "expires_at": "2024-02-05T23:26:00Z"
   }
```

---

## Flow 2: Redirect (Happy Path)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              REDIRECT FLOW                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User visits: https://short.ly/Xk9pL2m

1. DNS resolves short.ly → CDN edge location
           │
           ▼
2. CDN EDGE checks cache
   • Cache HIT (95% of traffic) → Return 301 redirect immediately
   • Cache MISS → Forward to origin
           │
           ▼
3. REDIRECT SERVICE receives request
   GET /Xk9pL2m
           │
           ▼
4. CHECK REDIS CACHE
   GET short:Xk9pL2m
   
   If found → Jump to step 6
   If not found → Continue to step 5
           │
           ▼
5. QUERY DATABASE (cache miss)
   SELECT long_url FROM urls WHERE short_code = 'Xk9pL2m'
   
   If found:
     • Populate cache: SET short:Xk9pL2m "long_url"
     • Continue to step 6
   
   If not found:
     • Return 404 Not Found
           │
           ▼
6. RETURN REDIRECT
   HTTP/1.1 301 Moved Permanently
   Location: https://example.com/very/long/path?param=value
   Cache-Control: max-age=86400
           │
           ▼
7. ASYNC: LOG CLICK EVENT
   Publish to Kafka:
   {
     "short_code": "Xk9pL2m",
     "timestamp": "2024-02-04T23:26:00Z",
     "ip": "203.0.113.42",
     "user_agent": "Mozilla/5.0...",
     "referrer": "https://twitter.com/..."
   }
```

---

## Flow 3: Custom Alias

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              CUSTOM ALIAS FLOW                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User wants: short.ly/my-brand-link

1. Request:
   POST /api/shorten
   {
     "long_url": "https://example.com/campaign",
     "custom_alias": "my-brand-link"
   }
           │
           ▼
2. VALIDATE ALIAS
   • Length: 3-30 characters
   • Allowed chars: [a-z, A-Z, 0-9, -]
   • Not reserved: ["api", "admin", "login", ...]
   • Not profanity filter match
           │
           ▼
3. CHECK AVAILABILITY
   SELECT 1 FROM urls WHERE short_code = 'my-brand-link'
   
   If exists → Return 409 Conflict: "Alias already taken"
           │
           ▼
4. STORE (same as regular flow)
   INSERT INTO urls (short_code, long_url, ...)
   VALUES ('my-brand-link', 'https://example.com/campaign', ...)
           │
           ▼
5. RETURN
   { "short_url": "https://short.ly/my-brand-link" }
```

---

## Edge Cases

### Case: URL Already Exists

```
Same user shortens same URL twice:
  → Return existing short code (don't create duplicate)

Different user shortens same URL:
  → Create new short code (each user owns their links)
```

### Case: Expired URL

```
1. User visits expired short URL
2. Check Redis → Found but expired (TTL passed)
3. Check DB → expires_at < NOW()
4. Return 410 Gone OR redirect to "link expired" page
5. Don't cache expired URLs at CDN
```

### Case: Malicious URL Detection

```
1. Before creating short URL:
   • Check against Google Safe Browsing API
   • Check internal blocklist
   
2. If malicious:
   • Reject with 400: "URL flagged as unsafe"
   
3. Periodic scan:
   • Scan existing URLs periodically
   • Disable if flagged later
```

### Case: Counter Exhaustion

```
Using counter-based IDs:
  • Counter approaches max value
  • Solution: Switch to longer codes (8 chars)
  • Or: Use multi-counter (counter_1, counter_2)
  
With 7 chars Base62: 3.5 trillion URLs
  → At 100M/month = 35,000 months = 2,900 years
  → Not a real concern!
```

### Case: Hot URL (Viral Link)

```
short.ly/viral-link gets 1M clicks/minute

1. CDN handles 99% of traffic
2. Cache-Control: max-age=3600 at CDN
3. Don't hit origin for each request
4. Analytics: Batch/sample, don't log every click

Result: Origin sees < 1000 QPS even for viral content
```

---

## ID Generation Strategies Comparison

| Strategy | Pros | Cons |
|----------|------|------|
| **Counter + Base62** | Sequential, no collisions | Need coordination (Zookeeper) |
| **Random** | Simple, no coordination | Collision possible, need check |
| **Hash(URL)** | Same URL = same code | Need full URL for lookup |
| **UUID + Truncate** | Simple, low collision | Not as short |

**Recommended:** Counter + Base62 for high scale, Random for simplicity

---

## 301 vs 302 Redirect

| Code | Meaning | Use When |
|------|---------|----------|
| **301** | Permanent | URL won't change, caching OK |
| **302** | Temporary | URL might change, no caching |

**Recommendation:** Use 301 for permanent links (better SEO, less load)

---

## Error Handling Summary

| Scenario | Handling |
|----------|----------|
| Invalid URL format | 400 Bad Request |
| URL not reachable | 400 or accept (user choice) |
| Alias taken | 409 Conflict |
| Short code not found | 404 Not Found |
| Expired URL | 410 Gone |
| Rate limit exceeded | 429 Too Many Requests |
| Malicious URL | 400 Forbidden |
| Database down | 503 (create), serve from cache (redirect) |
