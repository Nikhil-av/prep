# SCALING ESTIMATION CHEAT SHEET
## The Complete Reference for System Design Interviews

---

# 📊 Quick Reference Numbers (MEMORIZE THESE!)

## Power of 2 Table

| Power | Exact | Approximate |
|-------|-------|-------------|
| 2^10 | 1,024 | **1 Thousand (KB)** |
| 2^20 | 1,048,576 | **1 Million (MB)** |
| 2^30 | 1,073,741,824 | **1 Billion (GB)** |
| 2^40 | | **1 Trillion (TB)** |

---

## Time Conversions

| Unit | Seconds | Minutes | Hours |
|------|---------|---------|-------|
| 1 minute | 60 | 1 | - |
| 1 hour | 3,600 | 60 | 1 |
| 1 day | **86,400** ≈ **100K** | 1,440 | 24 |
| 1 month | **2.5M** | 43,200 | 720 |
| 1 year | **31.5M** ≈ **30M** | 525,600 | 8,760 |

**Quick trick:** 1 day ≈ 100K seconds, 1 year ≈ 30M seconds

---

## Storage Sizes

| Type | Size |
|------|------|
| 1 char | 1 byte (ASCII) / 2 bytes (Unicode) |
| UUID | 128 bits = 16 bytes |
| Integer (int32) | 4 bytes |
| Integer (int64/long) | 8 bytes |
| Timestamp | 8 bytes |
| IPv4 address | 4 bytes |
| IPv6 address | 16 bytes |
| Average tweet | 200 bytes |
| Average URL | 100 bytes |
| Average JSON metadata | 500 bytes - 1 KB |
| Thumbnail image | 20-50 KB |
| Average image (compressed) | 200-500 KB |
| HD image | 1-2 MB |
| 1 minute HD video | 50-100 MB |
| 1 minute 4K video | 300-500 MB |

---

## User Base Scale

| Size | Users | Category |
|------|-------|----------|
| Small | 100K | Startup |
| Medium | 1-10M | Growing company |
| Large | 10-100M | Large company |
| Massive | 100M-1B | Tech giants |
| Global | 1B+ | Facebook, WhatsApp scale |

---

# 🧮 INSTANT CALCULATION TABLES

## Million/Billion Multiplication (Use This!)

| × | 100 bytes | 500 bytes | 1 KB | 10 KB | 100 KB | 1 MB |
|---|-----------|-----------|------|-------|--------|------|
| **1 Million** | 100 MB | 500 MB | 1 GB | 10 GB | 100 GB | 1 TB |
| **10 Million** | 1 GB | 5 GB | 10 GB | 100 GB | 1 TB | 10 TB |
| **100 Million** | 10 GB | 50 GB | 100 GB | 1 TB | 10 TB | 100 TB |
| **1 Billion** | 100 GB | 500 GB | 1 TB | 10 TB | 100 TB | 1 PB |
| **10 Billion** | 1 TB | 5 TB | 10 TB | 100 TB | 1 PB | 10 PB |

**How to use:** 
```
100 Million URLs × 500 bytes each = 50 GB
Just look up: 100 Million row × 500 bytes column = 50 GB ✓
```

---

## Daily → Yearly → 5-Year Calculator

| Daily | Monthly (×30) | Yearly (×365) | 5 Years |
|-------|---------------|---------------|---------|
| 1 GB | 30 GB | 365 GB | 1.8 TB |
| 5 GB | 150 GB | 1.8 TB | 9 TB |
| 10 GB | 300 GB | 3.6 TB | 18 TB |
| 50 GB | 1.5 TB | 18 TB | 90 TB |
| 100 GB | 3 TB | 36 TB | 180 TB |
| 500 GB | 15 TB | 182 TB | 910 TB |
| 1 TB | 30 TB | 365 TB | 1.8 PB |

**Quick Rule:** Daily × 400 ≈ Yearly, Yearly × 5 = 5-Year

---

## QPS Calculator (Actions/Day → QPS)

| Actions/Day | ÷ 100K = QPS | Peak (×3) |
|-------------|--------------|-----------|
| 1 Million | 10 QPS | 30 QPS |
| 10 Million | 100 QPS | 300 QPS |
| 100 Million | 1,000 QPS | 3,000 QPS |
| 1 Billion | 10,000 QPS | 30,000 QPS |
| 10 Billion | 100,000 QPS | 300,000 QPS |
| 100 Billion | 1,000,000 QPS | 3,000,000 QPS |

**Formula:** Actions per day ÷ 100,000 = QPS (approximately)

---

## Bandwidth Calculator (QPS × Size)

| QPS | × 100 B | × 1 KB | × 10 KB | × 100 KB | × 1 MB |
|-----|---------|--------|---------|----------|--------|
| 100 | 10 KB/s | 100 KB/s | 1 MB/s | 10 MB/s | 100 MB/s |
| 1,000 | 100 KB/s | 1 MB/s | 10 MB/s | 100 MB/s | 1 GB/s |
| 10,000 | 1 MB/s | 10 MB/s | 100 MB/s | 1 GB/s | 10 GB/s |
| 100,000 | 10 MB/s | 100 MB/s | 1 GB/s | 10 GB/s | 100 GB/s |

**Convert to Mbps:** × 8 (1 MB/s = 8 Mbps)

---

## Server Calculator

| Peak QPS | ÷ 1K QPS/server | ÷ 10K QPS/server |
|----------|-----------------|------------------|
| 1,000 | 1 server | 1 server |
| 10,000 | 10 servers | 1 server |
| 100,000 | 100 servers | 10 servers |
| 1,000,000 | 1,000 servers | 100 servers |

**Add 50% for redundancy!**

---

## Read:Write Ratio Impact

| System Type | Read:Write | Example |
|-------------|------------|---------|
| Read-heavy | 100:1 to 1000:1 | URL shortener, CDN, News |
| Balanced | 1:1 to 10:1 | Social media posts |
| Write-heavy | 1:10 to 1:100 | Logging, Analytics, IoT |

**Key Insight:**
- Read-heavy → Cache aggressively, read replicas
- Write-heavy → Message queues, sharding

---

# 🔢 QUICK MENTAL MATH TRICKS

## Shortcut: Seconds in a Day

```
86,400 seconds ≈ 100,000 (for easy division)

So: 100 Million / day ÷ 100K = 1,000 QPS
```

## Shortcut: Storage Multipliers

```
Bytes → KB: ÷ 1,000
KB → MB: ÷ 1,000
MB → GB: ÷ 1,000
GB → TB: ÷ 1,000

Quick: 1 Million × 1KB = 1 GB
       1 Billion × 1KB = 1 TB
```

## Shortcut: Common Record Sizes

| Record Type | Typical Size | Use This |
|-------------|--------------|----------|
| Short text (tweet, message) | 100-200 bytes | 200 B |
| URL record | 200-500 bytes | 500 B |
| User profile | 500 bytes - 1 KB | 1 KB |
| JSON document | 1-5 KB | 2 KB |
| Thumbnail | 20-50 KB | 50 KB |
| Image (compressed) | 200-500 KB | 500 KB |
| HD Image | 1-2 MB | 2 MB |
| 1 min video | 50-100 MB | 100 MB |

---

# 📋 FILL-IN-THE-BLANK TEMPLATE

Copy this and fill in during interview:

```
SYSTEM: _______________________

SCALE:
├─ DAU/Users: _______ 
├─ Actions/user/day: _______
└─ Total actions/day: _______ × _______ = _______

QPS:
├─ Write QPS: _______ ÷ 100K = _______
├─ Read:Write ratio: _______:1
├─ Read QPS: _______ × _______ = _______
└─ Peak QPS: _______ × 3 = _______

STORAGE:
├─ Record size: _______ bytes
├─ Daily: _______ × _______ = _______ GB
├─ Yearly: _______ × 365 = _______ TB
└─ 5-year: _______ × 5 = _______ TB

BANDWIDTH:
├─ Read: _______ QPS × _______ = _______ MB/s
└─ Write: _______ QPS × _______ = _______ MB/s

SERVERS:
├─ Peak QPS: _______
├─ QPS/server: _______ (assume 10K)
└─ Servers: _______ ÷ _______ × 1.5 = _______
```

---

# 🧮 THE ESTIMATION FORMULAS

## Step 1: Daily Active Users (DAU)

```
Given: Monthly Active Users (MAU)
DAU = MAU × 0.2 to 0.5 (depending on engagement)

Example:
MAU = 100 million
DAU = 100M × 0.3 = 30 million
```

## Step 2: Queries Per Second (QPS)

```
QPS = (DAU × queries per user per day) / seconds per day

QPS = (DAU × actions) / 86,400
    ≈ (DAU × actions) / 100,000  (for easy math)

Example:
DAU = 30 million
Average user reads 10 tweets/day
Read QPS = (30M × 10) / 100K = 3,000 QPS

Peak QPS = QPS × 2 to 3 (traffic spikes)
Peak QPS = 3,000 × 3 = 9,000 QPS
```

## Step 3: Storage Estimation

```
Daily Storage = DAU × writes per user × size per write

Example: Twitter
DAU = 30 million
10% users post tweets = 3M posts/day
Average tweet = 200 bytes + metadata = 500 bytes

Daily storage = 3M × 500 bytes = 1.5 GB/day

Yearly storage = 1.5 GB × 365 = 550 GB/year
5-year storage = 550 GB × 5 = 2.75 TB
```

## Step 4: Bandwidth Estimation

```
Bandwidth = QPS × request/response size

Read Bandwidth = Read QPS × average response size
Write Bandwidth = Write QPS × average request size

Example:
Read QPS = 3,000
Average tweet response = 1 KB (tweet + user info + metadata)
Read Bandwidth = 3,000 × 1 KB = 3 MB/sec = 24 Mbps

For images/videos, multiply accordingly!
```

---

# 📝 QUICK FORMULAS CARD

```
┌─────────────────────────────────────────────────────────────┐
│                    SCALING QUICK FORMULAS                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  DAU = MAU × 0.3                                           │
│                                                             │
│  QPS = (DAU × actions/day) / 100,000                       │
│                                                             │
│  Peak QPS = QPS × 3                                        │
│                                                             │
│  Daily Storage = writes/day × size per write               │
│                                                             │
│  Bandwidth = QPS × size                                    │
│                                                             │
│  Servers needed = Peak QPS / QPS per server                │
│  (assume 1 server handles 1,000-10,000 QPS)                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

# 🎯 COMMON SYSTEM ESTIMATES

## URL Shortener (like bit.ly)

| Metric | Calculation | Result |
|--------|-------------|--------|
| **New URLs/day** | 100M × 0.1 = 10M | 10 million |
| **Write QPS** | 10M / 100K | 100 QPS |
| **Read:Write ratio** | 100:1 (reads dominate) | |
| **Read QPS** | 100 × 100 | 10,000 QPS |
| **URL storage** | short_url(7) + long_url(100) + metadata | ~200 bytes |
| **Daily storage** | 10M × 200 bytes | 2 GB/day |
| **5-year storage** | 2 GB × 365 × 5 | 3.65 TB |

---

## Twitter/Feed System

| Metric | Calculation | Result |
|--------|-------------|--------|
| **MAU** | Given | 300 million |
| **DAU** | 300M × 0.3 | 100 million |
| **Tweets/day** | 100M × 0.05 (5% tweet) | 5 million |
| **Write QPS** | 5M / 86,400 | ~60 QPS |
| **Read QPS** | 100M × 10 reads / 86,400 | ~12,000 QPS |
| **Tweet size** | text + metadata | 1 KB |
| **Daily storage** | 5M × 1 KB | 5 GB/day |
| **With media** | 5 GB × 10 (images) | 50 GB/day |

---

## Chat System (WhatsApp)

| Metric | Calculation | Result |
|--------|-------------|--------|
| **DAU** | | 500 million |
| **Messages/user/day** | | 50 |
| **Total messages/day** | 500M × 50 | 25 billion |
| **Write QPS** | 25B / 86,400 | ~300,000 QPS |
| **Message size** | | 100 bytes |
| **Daily storage** | 25B × 100 bytes | 2.5 TB/day |
| **Yearly** | 2.5 TB × 365 | ~900 TB = 0.9 PB |
| **Concurrent connections** | DAU × 0.1 | 50 million |

---

## Video Streaming (YouTube)

| Metric | Calculation | Result |
|--------|-------------|--------|
| **DAU** | | 100 million |
| **Videos watched/user** | | 5 |
| **Read QPS (video requests)** | 100M × 5 / 86,400 | ~6,000 QPS |
| **Video uploads/day** | 100M × 0.001 | 100,000 |
| **Write QPS** | 100K / 86,400 | ~1 QPS |
| **Avg video size** | 5 min × 50 MB/min | 250 MB |
| **Daily upload storage** | 100K × 250 MB | 25 TB/day |
| **Bandwidth (streaming)** | 6000 × 5 Mbps | 30 Gbps |

---

## E-commerce (Amazon)

| Metric | Calculation | Result |
|--------|-------------|--------|
| **DAU** | | 50 million |
| **Product views/user** | | 20 |
| **Read QPS** | 50M × 20 / 86,400 | ~12,000 QPS |
| **Orders/day** | 50M × 0.02 (2% convert) | 1 million |
| **Write QPS (orders)** | 1M / 86,400 | ~12 QPS |
| **Peak (Black Friday)** | Normal × 10 | 120,000 QPS |

---

# 🖥️ SERVER CAPACITY ESTIMATES

## Single Server Capacity

| Resource | Typical Limit |
|----------|---------------|
| **CPU cores** | 8-64 |
| **RAM** | 32-256 GB |
| **SSD storage** | 1-4 TB |
| **Network** | 1-10 Gbps |

## QPS Capacity per Server

| Application Type | QPS per Server |
|------------------|----------------|
| Static content | 10,000-50,000 |
| Simple API | 5,000-20,000 |
| Database reads | 10,000-50,000 |
| Database writes | 1,000-10,000 |
| Complex computation | 100-1,000 |
| ML inference | 10-100 |

## How Many Servers?

```
Servers = Peak QPS / QPS per server

Example:
Peak QPS = 100,000
QPS per server = 10,000
Servers needed = 100,000 / 10,000 = 10 servers

Add redundancy: 10 × 1.5 = 15 servers
```

---

# 💾 DATABASE ESTIMATES

## Single Database Limits

| Database | Connections | QPS | Storage |
|----------|-------------|-----|---------|
| MySQL/PostgreSQL | 1,000-5,000 | 10,000-50,000 | 1-2 TB |
| MongoDB | 10,000+ | 50,000+ | 1-2 TB |
| Redis (cache) | 10,000+ | 100,000+ | 64-256 GB |
| Cassandra (per node) | N/A | 10,000-50,000 | 1-2 TB |

## When to Shard?

| Condition | Action |
|-----------|--------|
| > 1 TB data | Consider sharding |
| > 5,000 QPS writes | Shard or replicate |
| > 50,000 QPS reads | Add read replicas |
| > 5,000 connections | Connection pooling |

---

# 📡 LATENCY NUMBERS (MEMORIZE!)

| Operation | Time |
|-----------|------|
| L1 cache access | 1 ns |
| L2 cache access | 4 ns |
| RAM access | 100 ns |
| SSD read | 100 μs (0.1 ms) |
| HDD read | 10 ms |
| Same datacenter round trip | 0.5 ms |
| Cross-continent (US→EU) | 100-150 ms |
| Inter-continental (US→Asia) | 200-300 ms |

## Network Latency Rules

```
Same datacenter: < 1 ms
Same region: 1-10 ms
Cross-region: 50-100 ms
Cross-continent: 100-300 ms
```

---

# 🔄 REPLICATION & SHARDING

## Replication (for reads)

```
Read QPS too high?
→ Add read replicas

Formula:
Replicas needed = (Total Read QPS) / (QPS per replica)

Example:
Read QPS = 100,000
QPS per replica = 20,000
Replicas = 100,000 / 20,000 = 5 replicas
```

## Sharding (for writes/data size)

```
Data too big for one DB?
→ Shard by key

Formula:
Shards needed = Total Data Size / Size per Shard

Example:
Total data = 10 TB
Max per shard = 1 TB
Shards = 10 TB / 1 TB = 10 shards
```

---

# ✅ ESTIMATION INTERVIEW TEMPLATE

Use this template every time:

```
1. CLARIFY REQUIREMENTS
   □ MAU/DAU given or assume?
   □ Read-heavy or write-heavy?
   □ What's the read:write ratio?
   □ Data retention period?

2. ESTIMATE USERS
   □ MAU = ___
   □ DAU = MAU × 0.3 = ___
   □ Peak concurrent = DAU × 0.1 = ___

3. ESTIMATE QPS
   □ Writes/day = DAU × write_rate = ___
   □ Write QPS = writes/day / 100K = ___
   □ Read:Write = ___:1
   □ Read QPS = Write QPS × ratio = ___
   □ Peak QPS = Normal × 3 = ___

4. ESTIMATE STORAGE
   □ Object size = ___ bytes
   □ Daily storage = writes/day × size = ___
   □ Yearly storage = daily × 365 = ___
   □ 5-year storage = yearly × 5 = ___

5. ESTIMATE BANDWIDTH
   □ Read bandwidth = Read QPS × response size = ___
   □ Write bandwidth = Write QPS × request size = ___

6. ESTIMATE SERVERS
   □ Servers = Peak QPS / QPS per server = ___
   □ With redundancy = servers × 1.5 = ___
```

---

# 🎓 PRACTICE PROBLEMS

Try estimating these yourself:

1. **Instagram**: 1 billion MAU, 2 photos/day per active user
2. **Uber**: 50M DAU, 10 rides per user per month
3. **Slack**: 10M DAU, 100 messages per user per day
4. **Dropbox**: 500M users, 2 GB average storage per user

---

*Print this sheet and practice until the numbers become automatic!*
