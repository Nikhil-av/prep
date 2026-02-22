# Chat System (WhatsApp/Slack) — High Level Design

## 1. Problem Statement

Design a real-time chat system like WhatsApp or Slack that supports:
- 1-on-1 and group messaging
- Real-time message delivery
- Offline message support
- Read receipts and presence indicators
- Media sharing (images, videos)
- Push notifications

---

## 2. Requirements

### Functional Requirements

| Feature | Description |
|---------|-------------|
| **1-on-1 Messaging** | Send/receive messages between two users |
| **Group Messaging** | Groups up to 500-1000 members |
| **Offline Delivery** | Deliver messages when user comes online |
| **Read Receipts** | ✓ Sent, ✓✓ Delivered, ✓✓ (blue) Read |
| **Presence** | Online/Offline, "Last seen" status |
| **Media Messages** | Images, videos with thumbnails |
| **Push Notifications** | Notify when app is closed |

### Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| **Latency** | < 100ms for message delivery |
| **Availability** | 99.99% uptime |
| **Scale** | 500M+ users, 100B+ messages/day |
| **Ordering** | Messages delivered in order per conversation |

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTS                                        │
│                    (iOS, Android, Web)                                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
            │   APNs/FCM  │  │     CDN     │  │     S3      │
            │   (Push)    │  │  (Media)    │  │  (Upload)   │
            └─────────────┘  └─────────────┘  └─────────────┘
                                    │
                         ┌─────────────────────┐
                         │   Load Balancer     │
                         └─────────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  WS Gateway 1   │      │  WS Gateway 2   │      │  WS Gateway 3   │
└─────────────────┘      └─────────────────┘      └─────────────────┘
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
              ┌─────────────────┐   ┌─────────────────┐
              │  Redis Cluster  │   │     Kafka       │
              └─────────────────┘   └─────────────────┘
                         │                     │
         ┌───────────────┴─────────────────────┴───────────────┐
         ▼               ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│   Message   │  │  Presence   │  │   Group     │  │Notification │
│   Service   │  │   Service   │  │   Service   │  │   Service   │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
         │               │               │               │
         └───────────────┼───────────────┴───────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌─────────────────────┐       ┌─────────────────────┐
│     Cassandra       │       │    PostgreSQL       │
└─────────────────────┘       └─────────────────────┘
```

---

## 4. Connection Types Comparison

| Method | Direction | Latency | Use Case |
|--------|-----------|---------|----------|
| **HTTP** | Request only | High | REST APIs |
| **Long Polling** | Request only | ~1 sec | Fallback |
| **SSE** | Server→Client | ~100ms | Notifications |
| **WebSocket** ✅ | Bidirectional | ~50ms | Chat, Gaming |
| **WebRTC** | P2P | ~10ms | Video calls |

**Why WebSocket for Chat:**
- Full duplex (both directions)
- Low latency (~50ms)
- Persistent connection (no reconnection overhead)
- Small headers after handshake

---

## 5. WebSocket Connection Flow

### Connection Establishment

```
User                          Server                         Redis
  │                              │                              │
  │  1. WebSocket Handshake     │                              │
  │  ─────────────────────────▶│                              │
  │                              │                              │
  │  2. Auth (JWT)              │                              │
  │  ─────────────────────────▶│                              │
  │                              │  3. SET presence:user_id    │
  │                              │  ─────────────────────────▶│
  │                              │     { server: "ws-1" }      │
  │                              │                              │
  │  4. Connected ✅            │                              │
  │◀─────────────────────────────                              │
```

### Heartbeat & TTL

```python
# Redis key with TTL
SET presence:{user_id} {server: "ws-1", last_heartbeat: ...}
EXPIRE presence:{user_id} 60  # Auto-delete if no heartbeat

# Heartbeat every 30 seconds refreshes TTL
EXPIRE presence:{user_id} 60
```

**If server crashes:** No heartbeat → TTL expires → User marked offline automatically.

---

## 6. Message Routing

### User-to-Server Mapping in Redis

```
┌────────────────────────────────────────────────────────────────┐
│                      REDIS (Presence Store)                    │
│                                                                │
│  presence:alice → { server: "ws-server-1" }                   │
│  presence:bob   → { server: "ws-server-3" }                   │
│  presence:carol → { server: "ws-server-2" }                   │
└────────────────────────────────────────────────────────────────┘
```

### Message Flow (User Online)

```
1. Alice sends "Hi Bob" → Server 1
2. Server 1 queries Redis: "Where is Bob?" → Server 3
3. Server 1 publishes to Kafka/Redis Pub/Sub
4. Server 3 receives, pushes to Bob via WebSocket
```

### Message Flow (User Offline)

```
1. Alice sends "Hi Bob" → Server
2. Server queries Redis: Bob not found (offline)
3. Store message in DB with status = "pending"
4. (Later) Bob connects → Query pending messages → Deliver
```

---

## 7. Message Ordering

### The Problem

Alice sends 3 messages quickly. How to ensure Bob receives them in order?

### Solution: Server-Assigned Sequence Numbers

```python
# Per-conversation sequence number (Redis)
async def get_next_sequence(conversation_id):
    return await redis.incr(f"seq:{conversation_id}")
```

```json
{
    "message_id": "uuid-abc",
    "conversation_id": "alice-bob",
    "sequence": 1547,              // Server-assigned
    "sender": "alice",
    "text": "Hey",
    "server_timestamp": 1706998001
}
```

### Kafka Ordering

```python
# Partition by conversation_id = ordered delivery within conversation
await kafka.send(
    topic="chat-messages",
    key=conversation_id,  # All messages for this chat → same partition
    value=message
)
```

---

## 8. Database Design

### Why Cassandra for Messages?

| Feature | Why It Matters |
|---------|----------------|
| **Write-optimized** | Billions of messages/day |
| **Partition by conversation** | Fast retrieval |
| **Time-series ordering** | Built-in clustering |
| **Horizontal scaling** | Add nodes as needed |

### Cassandra Schema

```sql
CREATE TABLE messages (
    conversation_id UUID,
    message_id      TIMEUUID,
    sender_id       UUID,
    content         TEXT,
    content_type    TEXT,
    created_at      TIMESTAMP,
    PRIMARY KEY (conversation_id, message_id)
) WITH CLUSTERING ORDER BY (message_id DESC);
```

### PostgreSQL Schema (Relational Data)

```sql
-- Users
CREATE TABLE users (
    user_id     UUID PRIMARY KEY,
    phone       VARCHAR(20) UNIQUE,
    name        VARCHAR(255),
    created_at  TIMESTAMP
);

-- Groups
CREATE TABLE groups (
    group_id    UUID PRIMARY KEY,
    name        VARCHAR(255),
    created_by  UUID REFERENCES users(user_id),
    created_at  TIMESTAMP
);

-- Group Membership
CREATE TABLE group_members (
    group_id    UUID REFERENCES groups(group_id),
    user_id     UUID REFERENCES users(user_id),
    role        VARCHAR(20),
    joined_at   TIMESTAMP,
    PRIMARY KEY (group_id, user_id)
);

-- User Devices (for push notifications)
CREATE TABLE user_devices (
    user_id         UUID,
    device_id       VARCHAR(255),
    device_token    VARCHAR(255),
    platform        VARCHAR(10),    -- 'ios' or 'android'
    PRIMARY KEY (user_id, device_id)
);
```

### Redis Keys

```
presence:{user_id}           → { server, last_heartbeat, last_activity }
seq:{conversation_id}        → integer (message sequence)
active_devices:{user_id}     → Set of active device_ids
presence_subscribers:{user_id} → Set of users watching presence
```

---

## 9. Group Messaging

### Fan-Out on Write Pattern

```
Alice sends "Hello everyone!" to Group (500 members)
                    │
                    ▼
            ┌─────────────────┐
            │  Store message  │ (once in Cassandra)
            └─────────────────┘
                    │
                    ▼
            ┌─────────────────┐
            │  Kafka Fan-Out  │
            │  (delivery tasks)│
            └─────────────────┘
                    │
    ┌───────────────┼───────────────┐
    ▼               ▼               ▼
 Online?         Online?         Offline?
    │               │               │
    ▼               ▼               ▼
 WebSocket      WebSocket       Store pending
  push           push            in DB
```

### Optimization: Batch by Server

```python
# Instead of 500 Kafka messages, send ~10 (one per server)
server_to_members = group_members_by_server(members)
for server, member_list in server_to_members.items():
    await redis.publish(f"server:{server}", {
        "message": message,
        "recipients": member_list
    })
```

---

## 10. Read Receipts

### Three Message States

| State | Symbol | Meaning |
|-------|--------|---------|
| **Sent** | ✓ | Message reached server |
| **Delivered** | ✓✓ | Message on recipient's device |
| **Read** | ✓✓ (blue) | Recipient opened the chat |

### High Water Mark Pattern

Instead of storing read status per message:

```sql
-- ONE row per user per conversation
CREATE TABLE read_status (
    conversation_id UUID,
    user_id         UUID,
    last_read_msg   UUID,
    read_at         TIMESTAMP,
    PRIMARY KEY (conversation_id, user_id)
);
```

**"Is message 45 read by Bob?"** → Check if `last_read_msg >= msg_45`

### Flow

```
Bob opens chat, sees messages 1-50
        │
        ▼
Bob's phone sends:
{ type: "read", conversation_id: "abc", last_read_msg: "msg_50" }
        │
        ▼
Server updates read_status + notifies Alice (if online)
or queues receipt (if Alice offline)
```

---

## 11. Presence (Online/Offline Status)

### Tracking Strategy

| Type | Purpose | Update Frequency |
|------|---------|------------------|
| **Heartbeat** | "Is user online?" | Every 30 seconds |
| **Last Activity** | "Last seen 2:05 PM" | On user actions |

### Redis Structure

```python
presence:{user_id} = {
    "server": "ws-server-3",
    "last_heartbeat": 1706998200,
    "last_activity": 1706998195
}
TTL: 60 seconds
```

### Fetching Presence

- **On-demand:** Fetch when user opens a chat
- **Subscription:** While chat is open, subscribe to target's presence changes
- **Privacy:** Check privacy settings before revealing status

```python
async def get_presence(requester_id, target_id):
    # Check privacy
    if not can_see_presence(requester_id, target_id):
        return {"status": "hidden"}
    
    # Get from Redis
    presence = await redis.hgetall(f"presence:{target_id}")
    if is_online(presence):
        return {"status": "online"}
    return {"status": "last_seen", "time": presence["last_activity"]}
```

---

## 12. Media Messages

### Why Not Send Through WebSocket?

| Problem | Impact |
|---------|--------|
| **Blocking** | 50MB upload blocks all other messages |
| **Memory** | 10K users × 5MB = 50GB server memory |
| **No resume** | Failed at 90%? Start over |
| **No CDN** | Can't cache, slow global delivery |

### Media Upload Flow

```
1. Client requests presigned S3 URL
2. Client uploads directly to S3 (bypasses chat server)
3. Client sends message with media reference:
   {
       type: "image",
       media_url: "s3://bucket/abc.jpg",
       thumbnail: "base64..."  // ~10KB for instant display
   }
4. Recipient downloads from CDN (not chat server)
```

### Video Optimization

```
Upload: original_video.mp4 (100MB)
            │
            ▼
    ┌─────────────────┐
    │   Transcoding   │
    └─────────────────┘
            │
    ┌───────┼───────┐
    ▼       ▼       ▼
  240p    480p    720p   + HLS/DASH (streaming format)
```

---

## 13. Push Notifications

### Why APNs/FCM?

Only Apple (APNs) and Google (FCM) can "wake up" a closed app.

### Flow

```
Alice sends message → Bob offline?
        │
        ▼
┌─────────────────┐
│ Push Service    │
└─────────────────┘
        │
        ├── iOS device → APNs → Bob's iPhone
        └── Android → FCM → Bob's Android
```

### Device Registration

```sql
-- Store on user login
INSERT INTO user_devices (user_id, device_id, device_token, platform)
VALUES ('bob', 'device123', 'apns_token_xyz', 'ios');
```

### Smart Notification

```python
async def send_push(user_id, message):
    devices = await db.get_user_devices(user_id)
    active_devices = await redis.smembers(f"active_devices:{user_id}")
    
    for device in devices:
        # Skip if user has active WebSocket on this device
        if device.device_id in active_devices:
            continue
        
        if device.platform == "ios":
            await send_apns(device.token, message)
        else:
            await send_fcm(device.token, message)
```

---

## 14. Scaling Strategies

### Database Scaling

| Component | Strategy |
|-----------|----------|
| **Cassandra** | Add nodes, partition by conversation_id |
| **PostgreSQL** | Read replicas, shard by user_id |
| **Redis Cluster** | Shard by user_id |

### WebSocket Scaling

- Horizontal scaling with sticky sessions
- User→server mapping in Redis
- Cross-server messaging via Kafka/Pub-Sub

### Handling Failure

| Failure | Handling |
|---------|----------|
| **Redis down** | Broadcast to all servers (fallback) |
| **Kafka down** | Direct HTTP between servers |
| **WS Server crash** | TTL expires, user reconnects to another server |
| **DB down** | Queue messages locally, retry |

---

## 15. Interview Talking Points

### "How do you ensure message ordering?"
> "Server-assigned sequence numbers per conversation, stored atomically in Redis. Kafka partitioned by conversation_id guarantees ordered delivery. Client buffers and reorders if needed."

### "Why Cassandra over PostgreSQL for messages?"
> "Write-optimized for billions of messages/day, partitioned by conversation_id for fast retrieval, time-based clustering for automatic ordering, horizontal scaling without single point of failure."

### "How do you handle offline users?"
> "Messages stored in Cassandra with status='pending'. On reconnect, client sends last_sync timestamp, server returns sync summary, client fetches messages on-demand. TTL cleanup for abandoned accounts."

### "How does fan-out work for group messages?"
> "Fan-out on write for small groups (<1000). Store message once, publish delivery tasks to Kafka. Workers check presence, push via WebSocket if online, mark pending if offline. Optimize by batching per server."

### "How do read receipts scale?"
> "High water mark pattern: store only last_read_message_id per user per conversation. One row instead of one-per-message. For exact timestamps, use TTL-based detailed storage for recent messages only."

---

## 16. Quick Reference Card

```
┌────────────────────────────────────────────────────────────────────────┐
│                    CHAT SYSTEM CHEAT SHEET                             │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  CONNECTIONS                                                           │
│  • WebSocket for real-time bidirectional messaging                     │
│  • Redis for user→server mapping with TTL                              │
│  • Heartbeat every 30s, TTL 60s = auto-offline detection               │
│                                                                        │
│  MESSAGE ROUTING                                                       │
│  • Online: Redis lookup → Kafka/Pub-Sub → Target server → WebSocket   │
│  • Offline: Store in Cassandra, deliver on reconnect                   │
│                                                                        │
│  ORDERING                                                              │
│  • Server-assigned sequence per conversation (Redis INCR)              │
│  • Kafka partition by conversation_id                                  │
│                                                                        │
│  DATABASES                                                             │
│  • Cassandra: Messages, read receipts (write-heavy, partitioned)       │
│  • PostgreSQL: Users, groups, settings (relational, ACID)              │
│  • Redis: Presence, sequences, sessions (real-time)                    │
│  • S3 + CDN: Media storage and delivery                                │
│                                                                        │
│  KEY PATTERNS                                                          │
│  • Fan-out on write for groups                                         │
│  • High water mark for read receipts                                   │
│  • On-demand + subscription for presence                               │
│  • Presigned URLs for media upload                                     │
│                                                                        │
│  SCALE NUMBERS                                                         │
│  • 500M+ users, 100B+ messages/day                                     │
│  • <100ms message delivery latency                                     │
│  • 99.99% availability                                                 │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 17. Delete Message Feature

### Two Types of Delete

| Type | Server Involved? | Affects Others? |
|------|------------------|-----------------|
| **Delete for Me** | ❌ No (local only) | No |
| **Delete for Everyone** | ✅ Yes | Yes (within time limit) |

### Delete for Everyone Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    DELETE FOR EVERYONE FLOW                         │
└─────────────────────────────────────────────────────────────────────┘

1. Alice taps "Delete for Everyone"
        │
        ▼
2. Server validates:
   - Is Alice the sender?
   - Is message within 60-minute window?
        │
        ▼
3. Server marks message in Cassandra:
   UPDATE messages SET is_deleted = true WHERE message_id = 'xyz'
        │
        ▼
4. Server sends delete command to all recipients:
   {
       type: "delete_message",
       message_id: "xyz",
       conversation_id: "group_abc",
       deleted_by: "alice"
   }
        │
        ▼
5. Recipients' phones:
   - Online: Delete from local storage immediately
   - Offline: Receive command on next sync
```

### Why Time Limit (60 minutes)?

| Reason | Explanation |
|--------|-------------|
| **Already seen** | Old messages already read by everyone |
| **Screenshots** | People may have taken screenshots |
| **Storage cleanup** | Old delete commands would pile up |
| **User expectation** | Recent mistake = undo, old = history |

---

## 18. Status (Stories) Feature

### Status vs Messages

| Aspect | Messages | Status |
|--------|----------|--------|
| **Audience** | Specific person/group | All contacts |
| **Lifetime** | Forever | 24 hours |
| **Delivery** | Must be instant | User checks when they want |
| **Storage** | Permanent | Auto-delete with TTL |

### Fan-Out Strategy: Read (not Write)

For Status, use **Fan-out on Read** because:
- No urgent delivery needed
- Same content for all viewers
- Auto-expires in 24 hours

```python
# When Bob opens Status tab
async def get_statuses_for_user(bob_id):
    # 1. Get Bob's contacts
    contacts = await get_contacts(bob_id)
    
    # 2. Check who has active statuses (Redis)
    active_posters = await redis.smembers("users_with_status")
    relevant_contacts = contacts & active_posters
    
    # 3. Fetch only those statuses
    statuses = []
    for contact_id in relevant_contacts:
        statuses.extend(await db.get_statuses(contact_id))
    return statuses
```

### Status Storage

```sql
-- Cassandra with TTL
CREATE TABLE statuses (
    user_id     UUID,
    status_id   TIMEUUID,
    media_url   TEXT,
    created_at  TIMESTAMP,
    PRIMARY KEY (user_id, status_id)
) WITH default_time_to_live = 86400;  -- Auto-delete after 24hr
```

### Tracking Active Posters (Redis)

```python
# When Alice posts a status
await redis.sadd("users_with_status", alice_id)
await redis.expire("users_with_status", 86400)  # 24hr
```

### View Tracking (Client-Side Storage)

WhatsApp uses **client-side storage** for privacy:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    STATUS VIEW TRACKING                             │
└─────────────────────────────────────────────────────────────────────┘

1. Bob views Alice's status
        │
        ▼
2. Bob's phone sends view receipt:
   { type: "status_view", status_id: "xyz", viewer: "bob" }
        │
        ▼
3. Server RELAYS to Alice (doesn't store permanently!)
        │
        ▼
4. Alice's phone stores locally: "Bob viewed at 2:30 PM"
```

**If Alice is offline:** Server queues view receipt temporarily, delivers when Alice comes online.

### Status Architecture Summary

```
POST STATUS:
  Upload media → S3
  Save metadata → Cassandra (TTL 24hr)
  Add to "users_with_status" → Redis

VIEW STATUSES:
  Get contacts → Intersect with active posters
  Fetch from Cassandra → Media from CDN

TRACK VIEWS:
  Viewer sends receipt → Server relays → Poster's phone stores
```

---

## 19. Component Summary

| Component | Technology | Purpose |
|-----------|------------|---------|
| **WebSocket Gateway** | Node.js/Go | Persistent connections |
| **Message Service** | Java/Go | Store, route, deliver |
| **Presence Service** | Go | Online/offline tracking |
| **Group Service** | Java | Membership, fan-out |
| **Notification Service** | Java | Push via APNs/FCM |
| **Media Service** | Python | Presigned URLs, transcoding |
| **Redis Cluster** | Redis | Presence, sessions, sequences |
| **Kafka** | Kafka | Message routing, events |
| **Cassandra** | Cassandra | Message storage |
| **PostgreSQL** | PostgreSQL | User/group metadata |
| **S3 + CloudFront** | AWS | Media storage + CDN |

---

## 20. Deep Dive: Database Strategy (Polyglot Persistence)

We use **different databases for different purposes** based on their strengths.

### Database Selection Summary

| Data Type | Database | Reason |
|-----------|----------|--------|
| **Users, Groups, Settings** | PostgreSQL | Relational, ACID, JOINs |
| **Messages** | Cassandra | Write-heavy, partitioned, scale |
| **User Updates Timeline** | Cassandra | Append-only, fast sync |
| **Read Receipts** | Cassandra | Per-user, TTL |
| **Statuses (Stories)** | Cassandra | TTL auto-delete |
| **Presence** | Redis | Real-time, TTL, fast |
| **Sessions** | Redis | Temporary, fast lookup |
| **Sequences** | Redis | Atomic INCR |
| **Images/Videos** | S3 | Large files, cheap |
| **Message Routing** | Kafka | Ordered, reliable |

### PostgreSQL — Relational Data

**Store:** Users, Groups, Settings, Privacy, Device Tokens, Contacts

| ✅ Pros | ❌ Cons |
|---------|---------|
| ACID transactions | Harder to scale horizontally |
| Complex queries (JOINs) | Single master bottleneck |
| Data integrity (foreign keys) | Slower for high write throughput |

**Scale Strategy:** Read replicas, shard by user_id for very large scale.

### Cassandra — Message Storage

**Store:** Messages, User Updates Timeline, Read Receipts, Statuses

| ✅ Pros | ❌ Cons |
|---------|---------|
| Write-optimized (LSM tree) | No JOINs |
| Horizontal scaling (add nodes) | Limited query flexibility |
| Built-in TTL | Eventual consistency |
| Partition by conversation = fast reads | |

### Redis — Real-Time Data

**Store:** Presence, Sessions, Sequences, Active Devices, Pub/Sub

| ✅ Pros | ❌ Cons |
|---------|---------|
| In-memory = ultra fast | Limited to RAM |
| Pub/Sub for real-time | Data loss on crash |
| Atomic operations, TTL | Not for permanent storage |

**Rule:** Use Redis for data you can afford to lose or rebuild.

### S3 — Media Storage

**Store:** Images, Videos, Voice Messages, Documents, Thumbnails

| ✅ Pros | ❌ Cons |
|---------|---------|
| 99.999999999% durability | Not a database (no queries) |
| Infinite scale, cheap | Need CDN for speed |

---

## 21. Partition Keys in Cassandra

### What is a Partition Key?

The partition key determines **which node stores the data**.

```sql
CREATE TABLE messages (
    conversation_id UUID,    -- ← PARTITION KEY
    message_id      TIMEUUID,
    content         TEXT,
    PRIMARY KEY (conversation_id, message_id)
);

-- PRIMARY KEY (partition_key, clustering_key)
--              ↑               ↑
--         Which node      Order within partition
```

### How It Works

```
                    hash(conversation_id)
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
         ┌─────────┐   ┌─────────┐   ┌─────────┐
         │ Node 1  │   │ Node 2  │   │ Node 3  │
         │ conv A  │   │ conv B  │   │ conv C  │
         │ conv D  │   │ conv E  │   │ conv F  │
         └─────────┘   └─────────┘   └─────────┘

All messages for conversation A stored on Node 1!
```

### Query with Partition Key

```sql
SELECT * FROM messages 
WHERE conversation_id = 'A' 
LIMIT 50;

-- 1. Hash conversation_id → Node 1
-- 2. Query ONLY Node 1 (not all nodes!)
-- 3. Return sorted by message_id (clustering key)
```

**Result:** Single-node query = FAST ✅

### Good vs Bad Partition Keys

| Partition Key | Query | Speed |
|---------------|-------|-------|
| `conversation_id` ✅ | "Messages in conv A" | Fast (single node) |
| `sender_id` ❌ | "Messages in conv A" | Slow (all nodes) |

---

## 22. Sharding PostgreSQL (Groups Challenge)

### The Problem

Groups have relationships — sharding is tricky:

```
Query 1: "Which groups is Bob in?"
  → Shard by user_id → Fast ✅

Query 2: "Who are all members of Group X?"
  → Shard by user_id → Slow (members scattered) ❌
```

### Solution: Denormalization (Two Tables)

```sql
-- Table 1: Sharded by group_id
CREATE TABLE group_members_by_group (
    group_id    UUID,
    user_id     UUID,
    PRIMARY KEY (group_id, user_id)
);

-- Table 2: Sharded by user_id
CREATE TABLE group_members_by_user (
    user_id     UUID,
    group_id    UUID,
    PRIMARY KEY (user_id, group_id)
);
```

**Write to both tables** when someone joins a group.

---

## 23. Telegram vs WhatsApp Architecture

### Key Differences

| Feature | WhatsApp | Telegram |
|---------|----------|----------|
| **Storage** | Device (E2E encrypted) | Cloud (server-side) |
| **Multi-device** | Limited | Full sync |
| **Max group size** | 1,024 | 200,000 |
| **Channels** | ❌ No | ✅ Yes (broadcast) |
| **Message history** | Lost on new device | Full history |

### Telegram's Sync Protocol

Telegram uses a **global update_id** per user:

```python
# When Bob syncs after being offline
SELECT * FROM user_updates 
WHERE user_id = 'bob' 
AND update_id > 5847291  -- Bob's last seen update
ORDER BY update_id ASC;
```

**One query → all updates (DMs, groups, channels, reactions)!**

### Large Groups (200K members)

| Group Size | Fan-out Strategy |
|------------|------------------|
| Small (< 1000) | Write (insert into each timeline) |
| Large (> 10000) | Read (store once, fetch on open) |

### Channel Notifications (10M subscribers)

```
CNN posts → 10 million subscribers

  ├── 8M notifications OFF → No push
  └── 2M notifications ON
        ├── 1.8M offline → APNs/FCM
        └── 200K online → WebSocket
```

---

## 24. Interview Answer: Database Strategy

> "We use **polyglot persistence** — different databases for different needs:
> - **PostgreSQL** for users, groups, settings (relational, ACID)
> - **Cassandra** for messages (write-optimized, partitioned by conversation)
> - **Redis** for presence and sessions (real-time, TTL)
> - **S3** for media (infinite scale, cheap)
> - **Kafka** for message routing and events (ordered delivery)
>
> The key insight is partition key design — by partitioning messages by conversation_id, we ensure all messages for a conversation are on the same Cassandra node, making queries fast."

