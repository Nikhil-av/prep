# HLD MASTER PREP PLAN
## System Design Interview Mastery (Amazon SDE2 Level)

---

# 📅 3-Week Intensive Plan

Starting from core system designs (you already know concepts).

---

## Week 1: Foundation Systems

| Day | System | Time | Focus Areas |
|-----|--------|------|-------------|
| 1 | **URL Shortener** | 2 hrs | Hashing, Base62, Key-generation service |
| 2 | **Pastebin** | 2 hrs | Object storage, Expiry, Analytics |
| 3 | **Twitter/Feed** | 3 hrs | Fan-out strategies, Timeline, Caching |
| 4 | **Instagram** | 3 hrs | Image storage, CDN, News feed |
| 5 | **WhatsApp/Chat** | 3 hrs | WebSockets, Delivery guarantees, Presence |
| 6 | **Uber/Ride Sharing** | 3 hrs | Geolocation, Matching algorithm, ETA |
| 7 | **Mock Interview #1** | 1 hr | Full simulation with feedback |

---

## Week 2: Advanced Systems

| Day | System | Time | Focus Areas |
|-----|--------|------|-------------|
| 8 | **YouTube** | 3 hrs | Video processing, Transcoding, Streaming |
| 9 | **Netflix** | 3 hrs | Recommendation, Microservices, CDN |
| 10 | **Google Search** | 3 hrs | Crawling, Indexing, PageRank |
| 11 | **Rate Limiter (Distributed)** | 2 hrs | Redis, Token bucket at scale |
| 12 | **Notification System** | 2 hrs | Multi-channel, Prioritization, Templates |
| 13 | **Typeahead/Autocomplete** | 2 hrs | Trie, Prefix matching, Real-time |
| 14 | **Mock Interview #2** | 1 hr | Full simulation with feedback |

---

## Week 3: Expert Systems + Polish

| Day | System | Time | Focus Areas |
|-----|--------|------|-------------|
| 15 | **Distributed Cache** | 3 hrs | Consistent hashing, Eviction, Replication |
| 16 | **Distributed ID Generator** | 2 hrs | Snowflake, UUID, Clock synchronization |
| 17 | **Payment System** | 3 hrs | Idempotency, ACID, Reconciliation, PCI |
| 18 | **Google Docs** | 3 hrs | CRDT, Operational Transform, Conflict |
| 19 | **Ticketmaster** | 2 hrs | Inventory, Locking, Queue management |
| 20 | **Review All Systems** | 2 hrs | Quick walkthrough, key points |
| 21 | **Mock Interviews #3, #4** | 2 hrs | Back-to-back simulations |

---

# 📋 Per-System Study Template

For each system, cover these:

```
□ 1. REQUIREMENTS (5 min)
  □ Functional requirements
  □ Non-functional requirements
  □ Scale estimates (use cheat sheet!)

□ 2. API DESIGN (5 min)
  □ Core endpoints
  □ Request/Response format
  □ Authentication

□ 3. HIGH-LEVEL ARCHITECTURE (10 min)
  □ Draw the diagram
  □ Core components
  □ Data flow

□ 4. DATABASE DESIGN (10 min)
  □ Schema
  □ SQL vs NoSQL choice (with reasoning!)
  □ Indexing strategy
  □ Sharding key

□ 5. DEEP DIVE (15 min)
  □ Critical path
  □ Bottlenecks
  □ Caching strategy
  □ Scaling approach

□ 6. TRADE-OFFS
  □ Why this database?
  □ Why this cache?
  □ Consistency vs Availability?
```

---

# 🎯 System Summaries (Quick Reference)

## 1. URL Shortener

```
Requirements:
- Shorten URLs
- Redirect to original
- Analytics (optional)
- Custom aliases (optional)

Scale:
- 100M new URLs/day
- 10B reads/day (100:1 read:write)
- 5 years retention

Key Decisions:
- Base62 encoding (7 chars = 3.5 trillion combinations)
- Key Generation Service (pre-generate keys)
- NoSQL for speed (or SQL with cache)

Architecture:
Client → LB → App Servers → Cache (Redis) → Database
                                            ↓
                              Key Generation Service
```

---

## 2. Twitter/Feed System

```
Requirements:
- Post tweets
- Follow users
- Home timeline
- User timeline

Scale:
- 300M MAU, 100M DAU
- 500M tweets/day
- 10B timeline reads/day

Key Decisions:
- Fan-out on write (push to followers' timelines)
- Exception: Celebrities use fan-out on read
- Timeline in Redis (sorted set)

Architecture:
           ┌→ User Timeline DB
Tweet Post →┼→ Fan-out Service → Follower Timelines (Redis)
           └→ Tweet Storage

Timeline Read → Redis (O(1)) → Client
```

---

## 3. Chat System (WhatsApp)

```
Requirements:
- 1:1 messaging
- Group messaging
- Delivery status (sent, delivered, read)
- Online presence

Scale:
- 500M DAU
- 25B messages/day
- Real-time delivery

Key Decisions:
- WebSocket connections
- Message queue for offline delivery
- HBase/Cassandra for message storage

Architecture:
Client ↔ WebSocket Servers ↔ Message Broker (Kafka)
                                    ↓
                            Message Storage (Cassandra)
                                    ↓
                            Presence Service (Redis)
```

---

## 4. YouTube

```
Requirements:
- Upload videos
- Stream videos
- Search videos
- Recommendations

Scale:
- 100M DAU
- 100K uploads/day
- 1B video views/day

Key Decisions:
- Async video processing (transcode to multiple resolutions)
- CDN for video delivery
- DASH/HLS for adaptive streaming

Architecture:
Upload → Object Storage (S3) → Transcoding Pipeline
                                     ↓
                              Multiple Resolutions
                                     ↓
                                   CDN
                                     ↓
                                  Client
```

---

## 5. Distributed Rate Limiter

```
Requirements:
- Limit requests per user/IP
- Multiple algorithms
- Distributed (multiple servers)

Scale:
- 10M QPS across system
- Sub-millisecond latency

Key Decisions:
- Redis for centralized counting
- Lua scripts for atomicity
- Token bucket algorithm

Architecture:
Request → Rate Limit Middleware → Redis Check → Allow/Deny
                                       ↓
                              Token Bucket per user
```

---

# 🏗️ Architecture Patterns

## Pattern 1: Read-Heavy Systems (10:1 or more)

```
Use:
- Caching (Redis/Memcached)
- CDN for static content
- Read replicas
- Denormalization

Examples: Twitter, Instagram, News sites
```

## Pattern 2: Write-Heavy Systems

```
Use:
- Message queues (Kafka)
- CQRS (Command Query Separation)
- Event sourcing
- NoSQL for writes

Examples: Analytics, Logging, IoT
```

## Pattern 3: Real-Time Systems

```
Use:
- WebSocket connections
- Pub/Sub (Redis, Kafka)
- In-memory processing
- Long polling fallback

Examples: Chat, Gaming, Live updates
```

## Pattern 4: Search Systems

```
Use:
- Elasticsearch
- Inverted index
- Ranking algorithms
- Caching top queries

Examples: Google, E-commerce search
```

---

# ❓ Common Interview Questions

## Database Questions

| Question | Answer Framework |
|----------|-----------------|
| SQL vs NoSQL? | Structured/ACID → SQL. Scale/Flexibility → NoSQL |
| When to shard? | > 1TB data or > 5K write QPS |
| Sharding key? | Even distribution + query pattern |
| Hot partition? | Add hash prefix or time-bucket |

## Scaling Questions

| Question | Answer Framework |
|----------|-----------------|
| Handle 10x traffic? | Cache, LB, horizontal scale, CDN |
| Single point of failure? | Replicate, multi-region, failover |
| Slow queries? | Index, cache, denormalize, async |
| Data loss prevention? | Replication, backups, write-ahead log |

## Trade-off Questions

| Question | Answer Framework |
|----------|-----------------|
| Consistency vs Availability? | Depends on use case. Banking = CP, Social = AP |
| Push vs Pull? | Push = real-time, need resources. Pull = on-demand |
| Sync vs Async? | Sync = simple, blocking. Async = scalable, complex |

---

# 📚 Resources

## Must-Read

1. **Designing Data-Intensive Applications** (DDIA) - Martin Kleppmann
2. **System Design Interview Vol 1 & 2** - Alex Xu
3. **Grokking System Design** - Educative

## Practice Platforms

1. **Educative.io** - System Design Course
2. **YouTube** - System Design Primer channels
3. **GitHub** - System Design Primer repo

---

# ✅ Daily Checklist

```
Morning (30 min):
□ Review yesterday's system (key points only)
□ Read today's system overview

Afternoon (2-3 hrs):
□ Deep dive into today's system
□ Draw architecture diagram from memory
□ Write down trade-offs

Evening (30 min):
□ Practice explaining out loud (5 min timer)
□ Review scaling cheat sheet
□ Identify weak areas
```

---

# 🎤 Mock Interview Format

## Self-Practice (30 min)

1. Random system (use random picker)
2. Set 30-minute timer
3. Talk out loud (record yourself!)
4. Review and identify gaps

## With Partner (45 min)

1. Requirements clarification (5 min)
2. High-level design (10 min)
3. Deep dive (20 min)
4. Q&A and trade-offs (10 min)

---

*Follow this plan religiously. By Day 21, you'll be system design ready!*
