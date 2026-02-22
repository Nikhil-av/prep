# Chat System — Complete Deep Dive

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
| 1 | **1:1 Messaging** | P0 | Send/receive text messages between two users |
| 2 | **Real-time Delivery** | P0 | Messages delivered instantly via WebSocket |
| 3 | **Message Ordering** | P0 | Messages appear in correct order |
| 4 | **Offline Delivery** | P0 | Messages delivered when user comes online |
| 5 | **Group Messaging** | P0 | Multi-user chat rooms |
| 6 | **Read Receipts** | P1 | Show when messages are read |
| 7 | **Delivery Receipts** | P1 | Show when messages are delivered |
| 8 | **Presence Status** | P1 | Online/offline/last seen |
| 9 | **Media Sharing** | P1 | Images, videos, documents |
| 10 | **Push Notifications** | P1 | Notify when app is closed |
| 11 | **Delete Message** | P2 | Delete for me / Delete for everyone |
| 12 | **Status/Stories** | P2 | 24-hour ephemeral content |
| 13 | **Typing Indicators** | P2 | Show when user is typing |
| 14 | **Multi-device Sync** | P1 | Same account on multiple devices |

---

# 2. NON-FUNCTIONAL REQUIREMENTS

## Latency

| Operation | Target | Rationale |
|-----------|--------|-----------|
| Message delivery (online) | < 100ms | Real-time feel |
| Message delivery (offline sync) | < 2 sec | On app open |
| Presence update | < 500ms | Acceptable delay |
| Media upload start | < 1 sec | Presigned URL generation |
| Search | < 200ms | Instant results |

## Throughput

| Metric | Target |
|--------|--------|
| Messages/day | 100 billion |
| Concurrent connections | 50 million |
| Messages/second (peak) | 5 million |

## Availability

| Component | Target | Strategy |
|-----------|--------|----------|
| Core messaging | 99.99% | Multi-region, no SPOF |
| Presence | 99.9% | Redis cluster |
| Media | 99.99% | S3 + CDN |

## Consistency

| Data Type | Consistency Level |
|-----------|-------------------|
| Messages | Eventual (within 1 sec) |
| Read receipts | Eventual |
| User profiles | Strong |
| Group membership | Strong |

## Storage Retention

| Data | Retention |
|------|-----------|
| Messages | Forever (or until deleted) |
| Media | Forever |
| Presence | Real-time only (no history) |
| Status/Stories | 24 hours |

---

# 3. CAPACITY PLANNING

## Step-by-Step Calculation Guide

### Step 1: Define User Base

```
Total Users:               500 million
Daily Active Users (DAU):  200 million (40% of total)
Concurrent Users:          50 million (25% of DAU at peak)
```

**Formula:**
```
DAU = Total Users × 0.4
Concurrent = DAU × 0.25
```

---

### Step 2: Message Volume (QPS)

```
Messages per user per day:  50 messages
Total messages/day:         200M × 50 = 10 billion messages

Messages per second (avg):  10B / 86400 = ~115,000 QPS
Peak QPS:                   115,000 × 3 = ~350,000 QPS

(Peak = 3× average is a common assumption)
```

**Formula:**
```
QPS_avg = (DAU × Messages_per_user) / 86400
QPS_peak = QPS_avg × 3
```

---

### Step 3: Storage Calculation

**Message Size:**
```
Average message size:  200 bytes
  - message_id:        16 bytes (UUID)
  - conversation_id:   16 bytes
  - sender_id:         16 bytes
  - content:           100 bytes (avg)
  - timestamp:         8 bytes
  - metadata:          ~44 bytes
```

**Daily Storage:**
```
Messages/day:          10 billion
Storage/day:           10B × 200 bytes = 2 TB/day
Storage/year:          2 TB × 365 = 730 TB/year
With 3x replication:   730 TB × 3 = 2.2 PB/year
```

**Formula:**
```
Storage_daily = Messages_daily × Avg_message_size
Storage_yearly = Storage_daily × 365 × Replication_factor
```

---

### Step 4: Media Storage

```
Users sharing media:   20% of DAU = 40 million
Media per user/day:    2 items
Average media size:    500 KB (compressed)

Media storage/day:     40M × 2 × 500KB = 40 TB/day
Media storage/year:    40 TB × 365 = 14.6 PB/year
```

---

### Step 5: Bandwidth Calculation

**Outbound (Read-heavy):**
```
Each message read by 1 recipient (avg)
Reads/second (peak):   350,000
Outbound bandwidth:    350,000 × 200 bytes = 70 MB/s = 560 Mbps

Media reads:           500 Gbps (CDN handles this)
```

**Inbound (Writes):**
```
Writes/second:         350,000
Inbound bandwidth:     70 MB/s = 560 Mbps
```

---

### Step 6: Server Estimation

**WebSocket Servers:**
```
Connections per server:  50,000 (with proper tuning)
Total connections:       50 million concurrent
Servers needed:          50M / 50K = 1,000 servers

With redundancy (2x):    2,000 WebSocket servers
```

**Message Service Servers:**
```
QPS per server:          10,000 (with async I/O)
Peak QPS:                350,000
Servers needed:          350K / 10K = 35 servers

With redundancy:         70 servers
```

**Formula:**
```
Servers = (Peak_load / Capacity_per_server) × Redundancy_factor
```

---

### Step 7: Database Sizing

**Cassandra Cluster (Messages):**
```
Storage needed:          2 PB (with replication)
Per node capacity:       2 TB (recommended)
Nodes needed:            2000 TB / 2 TB = 1,000 nodes

Across 3 data centers:   ~350 nodes per DC
```

**Redis Cluster (Presence/Sessions):**
```
Active users:            50 million concurrent
Data per user:           200 bytes (presence, server mapping)
Total memory:            50M × 200 = 10 GB

With overhead:           ~50 GB
Redis nodes:             10 nodes (5 GB each, with replication)
```

---

### Quick Reference: Capacity Cheat Sheet

```
┌────────────────────────────────────────────────────────────────────────┐
│                    CAPACITY CHEAT SHEET                                │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  USERS                                                                 │
│  • Total: 500M    DAU: 200M    Concurrent: 50M                        │
│                                                                        │
│  MESSAGES                                                              │
│  • 10B/day    350K QPS (peak)    200 bytes/msg                        │
│                                                                        │
│  STORAGE                                                               │
│  • Messages: 2 TB/day → 2.2 PB/year (with replication)                │
│  • Media: 40 TB/day → 15 PB/year                                      │
│                                                                        │
│  SERVERS                                                               │
│  • WebSocket: 2,000 servers (50K conn each)                           │
│  • Message Service: 70 servers                                         │
│  • Cassandra: 1,000 nodes                                             │
│  • Redis: 10 nodes                                                     │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

# 4. DETAILED HLD DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    CHAT SYSTEM - DETAILED ARCHITECTURE                              │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                           CLIENTS
                    ┌─────────────────────────────────────────────────────────┐
                    │      iOS App          Android App         Web App       │
                    │        │                   │                  │          │
                    └────────┼───────────────────┼──────────────────┼──────────┘
                             │                   │                  │
                             └───────────────────┼──────────────────┘
                                                 │
                                    ┌────────────▼────────────┐
                                    │     LOAD BALANCER       │
                                    │    (AWS ALB / Nginx)    │
                                    │   - Health checks       │
                                    │   - SSL termination     │
                                    │   - Sticky sessions     │
                                    └────────────┬────────────┘
                                                 │
          ┌──────────────────────────────────────┼──────────────────────────────────────┐
          │                                      │                                      │
          ▼                                      ▼                                      ▼
┌──────────────────┐                  ┌──────────────────┐                  ┌──────────────────┐
│  API GATEWAY     │                  │  WEBSOCKET       │                  │   CDN            │
│  (Kong/Zuul)     │                  │  GATEWAY         │                  │  (CloudFront)    │
│                  │                  │                  │                  │                  │
│  - Auth/JWT      │                  │  - 2000 servers  │                  │  - Media files   │
│  - Rate limiting │                  │  - 50K conn each │                  │  - 100+ PoPs     │
│  - Routing       │                  │  - Heartbeat 30s │                  │  - Edge caching  │
│                  │                  │  - Auto-scaling  │                  │                  │
│  [10 instances]  │                  │                  │                  │                  │
└────────┬─────────┘                  └────────┬─────────┘                  └────────┬─────────┘
         │                                     │                                     │
         ▼                                     ▼                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    MICROSERVICES LAYER                                              │
├─────────────────────┬─────────────────────┬─────────────────────┬───────────────────────────────────┤
│  MESSAGE SERVICE    │  PRESENCE SERVICE   │  GROUP SERVICE      │  NOTIFICATION SERVICE            │
│  [70 instances]     │  [30 instances]     │  [20 instances]     │  [40 instances]                  │
│                     │                     │                     │                                   │
│  - Store messages   │  - Track online     │  - Group CRUD       │  - APNs (Apple)                  │
│  - Route to users   │  - Last seen        │  - Membership       │  - FCM (Google)                  │
│  - Fan-out groups   │  - Subscribe/notify │  - Fan-out logic    │  - Rate limiting                 │
│  - Read receipts    │  - Privacy checks   │  - Admin controls   │  - Device tokens                 │
│                     │                     │                     │                                   │
│  Go / Java          │  Go                 │  Java               │  Java                            │
└─────────┬───────────┴─────────┬───────────┴─────────┬───────────┴───────────────────┬───────────────┘
          │                     │                     │                               │
          ▼                     ▼                     ▼                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    MESSAGE QUEUE LAYER                                              │
├─────────────────────────────────────────┬───────────────────────────────────────────────────────────┤
│              KAFKA CLUSTER              │              REDIS CLUSTER                                │
│                                         │                                                           │
│  Brokers: 50 nodes                      │  Nodes: 10 (5 masters + 5 replicas)                      │
│  Topics:                                │                                                           │
│   - messages (partition by conv_id)     │  Data:                                                   │
│     [500 partitions]                    │   - presence:{user_id} → {server, timestamp}             │
│   - group-fanout                        │   - seq:{conv_id} → sequence number                      │
│     [200 partitions]                    │   - active_devices:{user_id} → set of devices            │
│   - notifications                       │   - user_server:{user_id} → ws_server_id                 │
│     [100 partitions]                    │   - presence_subs:{user_id} → set of subscribers         │
│   - analytics                           │                                                           │
│     [100 partitions]                    │  TTL: 60 seconds for presence                            │
│                                         │  Memory: 50 GB total                                     │
│  Replication: 3                         │                                                           │
│  Retention: 7 days                      │                                                           │
└─────────────────────────────────────────┴───────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATABASE LAYER                                                   │
├─────────────────────────────────────────┬───────────────────────────────────────────────────────────┤
│          CASSANDRA CLUSTER              │              POSTGRESQL CLUSTER                          │
│          (Message Storage)              │              (User/Group Metadata)                       │
│                                         │                                                           │
│  Nodes: 1000 (across 3 DCs)            │  Primary: 1 node per region                              │
│  Replication Factor: 3                  │  Read Replicas: 5 per region                             │
│  Consistency: QUORUM                    │  Regions: 3                                               │
│                                         │                                                           │
│  Tables:                                │  Tables:                                                  │
│  ┌─────────────────────────────────┐   │  ┌───────────────────────────────────────┐               │
│  │ messages                        │   │  │ users (500M rows)                     │               │
│  │  - partition: conversation_id   │   │  │  - Sharded by user_id hash            │               │
│  │  - clustering: message_id DESC  │   │  │  - 50 shards                          │               │
│  │  - ~10B messages                │   │  └───────────────────────────────────────┘               │
│  └─────────────────────────────────┘   │                                                           │
│  ┌─────────────────────────────────┐   │  ┌───────────────────────────────────────┐               │
│  │ read_status                     │   │  │ groups (100M rows)                   │               │
│  │  - partition: conversation_id   │   │  │  - Sharded by group_id hash          │               │
│  │  - clustering: user_id          │   │  └───────────────────────────────────────┘               │
│  └─────────────────────────────────┘   │                                                           │
│  ┌─────────────────────────────────┐   │  ┌───────────────────────────────────────┐               │
│  │ user_updates                    │   │  │ group_members                        │               │
│  │  - partition: user_id           │   │  │  - Denormalized: by_group + by_user  │               │
│  │  - clustering: update_id DESC   │   │  └───────────────────────────────────────┘               │
│  └─────────────────────────────────┘   │                                                           │
└─────────────────────────────────────────┴───────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    STORAGE LAYER                                                    │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                         AWS S3                                                      │
│                                                                                                     │
│  Buckets:                                                                                           │
│   - chat-media-prod/                                                                                │
│       ├── images/{user_id}/{year}/{month}/{uuid}.jpg                                               │
│       ├── videos/{user_id}/{year}/{month}/{uuid}.mp4                                               │
│       ├── thumbnails/{uuid}_thumb.jpg                                                               │
│       └── voice/{uuid}.ogg                                                                          │
│                                                                                                     │
│   - chat-backups-prod/ (message backups)                                                           │
│                                                                                                     │
│  Total: ~15 PB/year                                                                                 │
│  Lifecycle: Glacier after 1 year for backups                                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 5. REQUEST FLOWS

## Flow 1: Send Message (1:1 Chat)

### Happy Path

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SEND MESSAGE FLOW - HAPPY PATH                                         │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Alice sends "Hey Bob!" to Bob (Bob is ONLINE)

1. CLIENT → WEBSOCKET GATEWAY
   ┌─────────────────────────────────────────────────────────┐
   │ {                                                       │
   │   "type": "send_message",                               │
   │   "conversation_id": "alice-bob",                       │
   │   "content": "Hey Bob!",                                │
   │   "client_msg_id": "uuid-123" (for deduplication)       │
   │ }                                                       │
   └─────────────────────────────────────────────────────────┘
                    │
                    ▼
2. WEBSOCKET GATEWAY validates & publishes
   • Validate JWT token
   • Rate limit check (100 msg/min per user)
   • Publish to Kafka topic "messages" (partition by conv_id)
                    │
                    ▼
3. MESSAGE SERVICE consumes from Kafka
   • Assign server sequence: INCR seq:alice-bob → 1042
   • Store in Cassandra:
     INSERT INTO messages (conv_id, msg_id, content, seq, ...)
   • Send ACK to Alice: { "status": "stored", "msg_id": 1042 }
                    │
                    ▼
4. ROUTE TO BOB
   • Redis lookup: GET user_server:bob → "ws-server-42"
   • If found → Publish to Kafka "delivery" partition for ws-server-42
                    │
                    ▼
5. WS-SERVER-42 delivers to Bob
   • Find Bob's WebSocket connection
   • Send: { "type": "new_message", "from": "alice", "content": "Hey Bob!" }
                    │
                    ▼
6. BOB's CLIENT sends delivery receipt
   • { "type": "delivered", "msg_id": 1042 }
   • Relayed to Alice
```

### Edge Cases

#### Case: Bob is OFFLINE

```
Step 4 alternative:
   • Redis lookup: GET user_server:bob → NULL (not found)
   • Message stays in Cassandra with status = "pending"
   • Trigger push notification:
     - Lookup device tokens from PostgreSQL
     - Send via APNs/FCM

When Bob comes online:
   • Bob connects to WebSocket
   • Client sends: { "type": "sync", "last_seen_msg": 1040 }
   • Server queries: SELECT * FROM messages WHERE conv_id = 'alice-bob' AND msg_id > 1040
   • Returns pending messages
```

#### Case: Duplicate Message (Network Retry)

```
Alice's client retries due to network timeout:
   • Same client_msg_id: "uuid-123"

Message Service:
   • Check Redis: EXISTS dedup:uuid-123
   • If exists → Return cached response (don't store again)
   • If not → Store and SET dedup:uuid-123 EX 3600
```

#### Case: WebSocket Server Crashes

```
WS-Server-42 crashes while Bob is connected:
   • Redis key user_server:bob has TTL 60 sec
   • After 60 sec → Key expires automatically
   • Bob's client detects disconnect → Reconnects to different server
   • New server updates: SET user_server:bob "ws-server-57"
```

---

## Flow 2: Group Message (Fan-out)

### Happy Path (Small Group: 100 members)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              GROUP MESSAGE FLOW - FAN-OUT ON WRITE                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Alice sends "Hello everyone!" to group with 100 members

1. Validate Alice is member of group
2. Store message ONCE in Cassandra (group_messages table)
3. Get all group members from PostgreSQL (cached in Redis)
4. Batch by WebSocket server:
   
   ┌─────────────────────────────────────────────────────────┐
   │ Server ws-01: [bob, carol, dave]                        │
   │ Server ws-05: [eve, frank]                              │
   │ Server ws-12: [grace, ...]                              │
   │ Offline: [henry, ivan, ...]                             │
   └─────────────────────────────────────────────────────────┘
   
5. Publish ONE message per server (not per user)
6. Each server delivers to its connected members
7. Offline members: Push notification + pending in DB
```

### Edge Case: Large Group (10,000+ members)

```
Switch to FAN-OUT ON READ:
   • Store message once
   • Push to online members only (~500)
   • Offline members fetch on sync (query group_messages table)
   • No pending queue per user
```

---

## Flow 3: Presence Status

### Coming Online

```
1. Client connects to WebSocket
2. WebSocket Gateway:
   • SET presence:bob { "server": "ws-42", "status": "online" } EX 60
   • SET user_server:bob "ws-42" EX 60
3. Start heartbeat timer (every 30 sec)
4. Notify subscribers:
   • GET presence_subs:bob → [alice, carol]
   • For each → Push presence update
```

### Checking Someone's Status

```
1. Alice opens chat with Bob
2. Client requests: GET /presence/bob
3. Server checks privacy:
   • If Bob allows → Return presence
   • If "contacts only" → Check if Alice is contact
   • If "nobody" → Return null
4. Subscribe for updates:
   • SADD presence_subs:bob alice
```

### Cold Start: App Opens After Long Time

```
1. Client fetches contacts list
2. For each contact → Batch presence query
3. Server returns map: { "bob": "online", "carol": "offline", ... }
4. Subscribe to active conversations only (not all contacts)
```

---

## Flow 4: Media Upload

### Upload Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              MEDIA UPLOAD FLOW                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

1. CLIENT requests presigned URL
   POST /media/upload-url
   { "filename": "photo.jpg", "size": 2000000 }
           │
           ▼
2. MEDIA SERVICE generates presigned URL
   • Validate file size (< 100MB)
   • Generate S3 key: images/{user_id}/2024/02/{uuid}.jpg
   • Create presigned PUT URL (expires in 15 min)
   • Return: { "upload_url": "https://s3...", "media_id": "uuid" }
           │
           ▼
3. CLIENT uploads directly to S3
   PUT https://s3.../images/alice/2024/02/uuid.jpg
   (Bypasses our servers entirely!)
           │
           ▼
4. CLIENT sends message with media reference
   {
     "type": "message",
     "content_type": "image",
     "media_id": "uuid",
     "thumbnail_base64": "..." (small preview)
   }
           │
           ▼
5. MESSAGE SERVICE stores metadata
   • Store message with media_url in Cassandra
   • Deliver to recipient with CDN URL
```

### Edge Case: Upload Fails Midway

```
• S3 multipart upload with resume capability
• Client retries from last successful part
• Presigned URL expires → Client requests new one
• Incomplete uploads cleaned by S3 lifecycle policy
```

---

## Flow 5: Read Receipts (High Water Mark)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              READ RECEIPTS FLOW                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Bob reads messages in conversation with Alice:

1. Bob scrolls and views messages up to msg_id 1050
2. Client sends (debounced, every 2 sec):
   { "type": "read", "conversation_id": "alice-bob", "last_read": 1050 }
           │
           ▼
3. Server updates Cassandra:
   UPDATE read_status 
   SET last_read_msg = 1050, read_at = now()
   WHERE conv_id = 'alice-bob' AND user_id = 'bob'
           │
           ▼
4. Notify Alice (if online):
   { "type": "read_receipt", "conversation_id": "alice-bob", 
     "reader": "bob", "last_read": 1050 }
           │
           ▼
5. Alice's UI: Show double blue ticks for messages ≤ 1050
```

---

## Flow 6: Sync After Offline

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              OFFLINE SYNC FLOW                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Bob was offline for 2 days, opens app:

1. CLIENT connects and requests sync
   { "type": "sync", "last_update_id": 847291 }
           │
           ▼
2. SERVER queries user_updates table:
   SELECT * FROM user_updates 
   WHERE user_id = 'bob' AND update_id > 847291
   LIMIT 1000
           │
           ▼
3. Returns summary:
   {
     "conversations_with_updates": [
       { "id": "alice-bob", "unread": 15, "last_preview": "Hey!" },
       { "id": "group-123", "unread": 150, "last_preview": "Meeting?" }
     ],
     "last_update_id": 849105
   }
           │
           ▼
4. CLIENT shows notification badges
5. When Bob opens specific conversation → Fetch those messages
6. Paginated: Fetch 50 messages at a time
```

### Cold Start Optimization

```
If offline for > 7 days:
   • Don't sync all updates
   • Return conversation list with unread counts
   • Fetch messages only when conversation opened
   • Mark very old conversations as "Load more..."
```

---

## Flow 7: Delete Message

### Delete for Me

```
• Client-side only
• Mark message as hidden locally
• No server call needed
• Lost if app reinstalled
```

### Delete for Everyone

```
1. Alice requests delete within 60 min:
   { "type": "delete", "msg_id": 1042, "for_everyone": true }
           │
           ▼
2. Server validates:
   • Is Alice the sender?
   • Is it within time limit?
           │
           ▼
3. Update Cassandra:
   UPDATE messages SET is_deleted = true, content = null
   WHERE conv_id = 'alice-bob' AND msg_id = 1042
           │
           ▼
4. Broadcast delete command to all participants:
   { "type": "message_deleted", "msg_id": 1042 }
           │
           ▼
5. Each client removes/hides the message
```

### Edge Case: Recipient Already Saw Message

```
• Too late! They may have screenshot
• Server can't unsend from their brain
• This is why there's a time limit (60 min)
• Shows "This message was deleted" placeholder
```

---

## Error Handling Summary

| Scenario | Handling |
|----------|----------|
| Network timeout | Client retries with same client_msg_id |
| Server overload | Rate limiting at gateway (429 response) |
| Database down | Queue in Kafka, process when recovered |
| Invalid token | 401 Unauthorized, force re-login |
| Message too large | 413 Payload Too Large, client compresses |
| Rate limit exceeded | 429 with Retry-After header |
| WebSocket disconnect | Auto-reconnect with exponential backoff |

---

# 6. WHATSAPP vs TELEGRAM ARCHITECTURE

## Key Differences

| Feature | WhatsApp | Telegram |
|---------|----------|----------|
| **Message Storage** | Device (phone) | Cloud (server) |
| **Multi-Device** | Limited (phone must be on) | Full sync across all devices |
| **New Device Login** | No history (unless backup) | Full chat history available |
| **Max Group Size** | 1,024 members | 200,000 members |
| **Channels** | ❌ No | ✅ Broadcast to millions |
| **E2E Encryption** | ✅ Always | Optional (Secret Chats) |

---

## Telegram Multi-Device Sync

### The Problem

Bob logs into Telegram on Phone, Tablet, Desktop, Web. Alice sends a message.
All 4 devices need to show it instantly.

### Solution: Per-User Updates Timeline

```sql
-- Global updates table (per user)
CREATE TABLE user_updates (
    user_id     UUID,
    update_id   BIGINT,           -- Monotonically increasing per user
    update_type VARCHAR(20),      -- 'message', 'invite', 'reaction', etc.
    payload     JSONB,            -- The actual data
    created_at  TIMESTAMP,
    PRIMARY KEY (user_id, update_id)
);

-- Device sync state
CREATE TABLE device_sync (
    user_id         UUID,
    device_id       UUID,
    last_sync_id    BIGINT,
    PRIMARY KEY (user_id, device_id)
);
```

### Sync Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              TELEGRAM MULTI-DEVICE SYNC                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Bob opens app on Desktop after being offline:

1. CLIENT → "Sync me. Last I saw: update_id 5847291"
           │
           ▼
2. SERVER queries ONE table:
   SELECT * FROM user_updates 
   WHERE user_id = 'bob' AND update_id > 5847291
   ORDER BY update_id ASC LIMIT 1000
           │
           ▼
3. Returns ALL updates (messages, reactions, invites):
   {
     "updates": [
       { "id": 5847292, "type": "message", "conv": "alice-bob", ... },
       { "id": 5847293, "type": "reaction", "conv": "group-123", ... },
       { "id": 5847294, "type": "invite", "group": "New Project", ... }
     ],
     "last_update_id": 5847353
   }
           │
           ▼
4. REAL-TIME: If device has active WebSocket → Push new updates immediately
```

### How it works when Alice sends Bob a message:

```python
# 1. Store the message in messages table
message_id = store_message(conversation_id, content, ...)

# 2. Get Bob's next update_id  
next_update_id = redis.incr(f"update_seq:{bob_id}")

# 3. Insert into Bob's updates timeline
INSERT INTO user_updates (user_id, update_id, update_type, payload)
VALUES (bob_id, next_update_id, 'message', {
    "conversation_id": "alice-bob",
    "message_id": message_id,
    "sender": "alice",
    "preview": "Hey Bob!"
})

# 4. Push to all Bob's connected devices via WebSocket
```

---

## Large Groups (200,000 members)

### The Problem

Fan-out on Write for 200K members = 200K database writes per message!

### Solution: Hybrid Approach

| Group Size | Strategy | Why |
|------------|----------|-----|
| **Small (< 1000)** | Fan-out on Write | Real-time delivery important |
| **Large (> 10,000)** | Fan-out on Read | Too expensive to write 200K entries |

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              LARGE GROUP MESSAGE FLOW                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Alice posts in "Crypto News" group (200,000 members)

1. Store message ONCE:
   INSERT INTO group_messages (group_id, message_id, content, ...)
           │
           ▼
2. Notify ONLINE members only (real-time):
   • Check who has active WebSocket in this group
   • Push to ~5,000 online users (small subset)
           │
           ▼
3. OFFLINE members fetch on open:
   • Bob opens app → "What's new in groups I'm in?"
   • Server returns messages since Bob's last_sync per group
```

### Large Group Storage Schema

```sql
-- Messages stored per group (not per user)
CREATE TABLE group_messages (
    group_id    UUID,
    message_id  BIGINT,
    content     TEXT,
    sender_id   UUID,
    PRIMARY KEY (group_id, message_id)
);

-- Each user's position per group
CREATE TABLE user_group_sync (
    user_id         UUID,
    group_id        UUID,
    last_read_msg   BIGINT,
    PRIMARY KEY (user_id, group_id)
);
```

---

## Channels (Broadcast to Millions)

### Channel like @CNN with 10 million subscribers

**Question:** Push to all 10M when CNN posts?

**Answer:** C - Push only to "notifications enabled" + online users

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              CHANNEL POST FLOW                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

@CNN posts breaking news:

1. Store message ONCE in channel timeline:
   INSERT INTO channel_messages (channel_id, ...)
           │
           ▼
2. Push Notifications (subset only):
   • Get users with notifications enabled (~500K of 10M)
   • Further filter: online or recent activity (~100K)
   • Send push via APNs/FCM
           │
           ▼
3. Real-time delivery:
   • Only to users currently viewing channel
   • Or have active WebSocket with channel subscribed
           │
           ▼
4. Offline users:
   • See new posts when they open channel
   • Query: SELECT * FROM channel_messages WHERE message_id > last_seen

No per-user storage! No 10M writes!
```

---

## Storage Comparison

| | WhatsApp Approach | Telegram Approach |
|---|-------------------|-------------------|
| **Message Storage** | Minimal server storage | Full cloud storage |
| **DM Storage** | Device only | Server (user_updates table) |
| **Group Messages** | Fan-out on Write | Hybrid (small: write, large: read) |
| **Channels** | N/A | Fan-out on Read |
| **Server Cost** | Lower | Higher |
| **Offline Sync** | Limited | Full history |

---

## Interview Question: The Duplication Problem

**Q:** If a group has 1000 members, do you insert 1000 rows into `user_updates`?

**A:** Yes for small groups! But for large groups, switch to per-group storage.

```
Small Group (100 members):
  1 message → 100 entries in user_updates ✅

Large Group (200,000 members):  
  1 message → 1 entry in group_messages ✅
  Each user queries group_messages on sync
```

---

## WhatsApp Backup vs Telegram Cloud

### WhatsApp: Optional Backup

```
Messages on phone → User-initiated backup → Google Drive/iCloud
                                              │
                                              ▼
                                    Encrypted (or not)
                                    Restore on new phone
```

### Telegram: Always in Cloud

```
Messages → Telegram Servers → Encrypted at rest
                              │
                              ▼
                    Available on any device instantly
                    No backup needed
```

---

## Summary: When to Use Each Approach

| Requirement | Approach |
|-------------|----------|
| Privacy-first (E2E) | WhatsApp model (device storage) |
| Multi-device sync | Telegram model (cloud storage) |
| Large groups/channels | Fan-out on Read |
| Small groups | Fan-out on Write |
| Real-time critical | WebSocket + fallback to push |
