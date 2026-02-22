# Instagram — Complete Deep Dive

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
| 1 | **Photo/Video Upload** | P0 | Users post images and videos |
| 2 | **News Feed** | P0 | Show posts from followed users |
| 3 | **Follow/Unfollow** | P0 | Social graph management |
| 4 | **Like & Comment** | P0 | Engagement on posts |
| 5 | **Stories** | P1 | 24-hour ephemeral content |
| 6 | **Reels** | P1 | Short-form video content |
| 7 | **Direct Messages** | P1 | Private messaging |
| 8 | **Search** | P1 | Find users, hashtags, places |
| 9 | **Notifications** | P1 | Likes, comments, follows |
| 10 | **Explore/Discover** | P2 | Personalized content discovery |

---

# 2. NON-FUNCTIONAL REQUIREMENTS

## Latency

| Operation | Target | Rationale |
|-----------|--------|-----------|
| Load feed | < 200ms | First impression |
| Upload post | < 3 sec | User waiting |
| Like/comment | < 100ms | Must feel instant |
| Search | < 200ms | Interactive typing |
| Story load | < 150ms | Fast transitions |

## Throughput

| Metric | Target |
|--------|--------|
| Daily Active Users | 500 million |
| Posts uploaded/day | 100 million |
| Photos viewed/day | 50 billion |
| Likes/day | 5 billion |
| Stories/day | 500 million |

## Availability

| Component | Target | Strategy |
|-----------|--------|----------|
| Feed service | 99.99% | Multi-region |
| Upload service | 99.9% | Queue-based |
| Messaging | 99.99% | Critical path |

## Consistency

| Data Type | Consistency Level |
|-----------|-------------------|
| Posts | Eventual (seconds OK) |
| Likes count | Eventual (approximate OK) |
| Follow relationships | Strong |
| Messages | Strong |
| Payments | Strong |

---

# 3. CAPACITY PLANNING

## Step-by-Step Calculation

### Step 1: Define Scale

```
Daily Active Users:          500 million
Posts uploaded/day:          100 million
Average post size:           2 MB (compressed)
Likes/day:                   5 billion
Comments/day:                500 million
```

---

### Step 2: Storage Calculation

**Media Storage (S3):**
```
Posts/day:                   100 million
Average size:                2 MB
Daily storage:               100M × 2 MB = 200 TB/day
Yearly storage:              200 TB × 365 = 73 PB/year

With multiple resolutions (4×): ~300 PB/year
```

**Post Metadata (Cassandra):**
```
Per post:                    ~500 bytes
Posts/day:                   100 million
Daily:                       50 GB/day
Yearly:                      18 TB/year
```

**Feed Cache (Redis):**
```
Users:                       500 million
Post IDs per feed:           500
Per post ID:                 8 bytes
Per user feed:               4 KB
Total:                       500M × 4 KB = 2 TB

Only cache active users (20%): 400 GB
```

---

### Step 3: Server Estimation

**API Servers:**
```
Requests/sec (peak):         500,000
Per server:                  10,000 req/sec
Servers needed:              50 servers
With redundancy:             100 API servers
```

**Feed Service:**
```
Feed requests/sec:           100,000
Processing per request:      50ms
Servers (peak):              50 servers
```

**Upload Service:**
```
Uploads/sec:                 1,200
Processing per upload:       2 seconds
Servers:                     30 servers
```

---

### Quick Reference: Capacity Cheat Sheet

```
┌────────────────────────────────────────────────────────────────────────┐
│                    INSTAGRAM CAPACITY CHEAT SHEET                      │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  SCALE                                                                 │
│  • DAU: 500M    Posts/day: 100M    Likes/day: 5B                      │
│                                                                        │
│  STORAGE                                                               │
│  • Media (S3): 200 TB/day, 73 PB/year                                 │
│  • Metadata (Cassandra): 50 GB/day                                    │
│  • Feed Cache (Redis): 400 GB active users                            │
│                                                                        │
│  SERVERS                                                               │
│  • API: 100 servers                                                    │
│  • Feed: 50 servers                                                    │
│  • Upload: 30 servers                                                  │
│  • WebSocket (DMs): 100 servers                                        │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

# 4. DETAILED HLD DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    INSTAGRAM - DETAILED ARCHITECTURE                                │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                           CLIENTS
                    ┌─────────────────────────────────────────────────────────┐
                    │      iOS App              Android App          Web      │
                    │         │                       │                │      │
                    └─────────┼───────────────────────┼────────────────┼──────┘
                              │                       │                │
                              ▼                       ▼                ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │                    CDN (Akamai/CloudFront)              │
                    │                                                         │
                    │   - Static assets (JS, CSS)                             │
                    │   - Cached images/videos                                │
                    │   - Edge locations worldwide                            │
                    └─────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │                    LOAD BALANCER                        │
                    │                   (AWS ALB / Nginx)                     │
                    │                                                         │
                    │   - Health checks        - SSL termination              │
                    │   - Geographic routing   - Rate limiting                │
                    └─────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┼──────────────────────────────────────────────┐
           │                  │                                              │
           ▼                  ▼                                              ▼
┌──────────────────┐ ┌──────────────────┐                         ┌──────────────────┐
│  API GATEWAY     │ │  WEBSOCKET       │                         │  UPLOAD SERVICE  │
│                  │ │  GATEWAY         │                         │                  │
│  [100 instances] │ │  [100 instances] │                         │  [30 instances]  │
│                  │ │                  │                         │                  │
│  - Auth/JWT      │ │  - DMs           │                         │  - Media upload  │
│  - Rate limiting │ │  - Notifications │                         │  - Transcoding   │
│  - Routing       │ │  - Typing status │                         │  - Thumbnails    │
└────────┬─────────┘ └────────┬─────────┘                         └────────┬─────────┘
         │                    │                                            │
         └────────────────────┼────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    MICROSERVICES LAYER                                              │
├─────────────────────┬─────────────────────┬─────────────────────┬───────────────────────────────────┤
│  FEED SERVICE       │  POST SERVICE       │  USER SERVICE       │  SOCIAL GRAPH SERVICE            │
│  [50 instances]     │  [30 instances]     │  [20 instances]     │  [20 instances]                  │
│                     │                     │                     │                                   │
│  - Feed generation  │  - Create post      │  - Profiles         │  - Follow/unfollow               │
│  - Hybrid push/pull │  - Like/comment     │  - Settings         │  - Followers list                │
│  - Ranking          │  - Delete           │  - Auth             │  - Suggestions                   │
│  - Pagination       │  - Report           │  - Privacy          │  - Mutual friends                │
├─────────────────────┼─────────────────────┼─────────────────────┼───────────────────────────────────┤
│  STORY SERVICE      │  REELS SERVICE      │  SEARCH SERVICE     │  NOTIFICATION SERVICE            │
│  [20 instances]     │  [30 instances]     │  [20 instances]     │  [15 instances]                  │
│                     │                     │                     │                                   │
│  - 24h expiry       │  - Video processing │  - Elasticsearch    │  - Push notifications            │
│  - View tracking    │  - Recommendations  │  - Users/hashtags   │  - In-app notifications          │
│  - Story tray       │  - Discovery feed   │  - Autocomplete     │  - Batching                      │
├─────────────────────┼─────────────────────┴─────────────────────┴───────────────────────────────────┤
│  DM SERVICE         │  MESSAGING INFRASTRUCTURE                                                     │
│  [25 instances]     │                                                                               │
│                     │  - 1:1 and group chats                                                        │
│  - Send/receive     │  - Message persistence                                                        │
│  - Read receipts    │  - Media sharing                                                              │
│  - Typing indicator │  - Encryption                                                                 │
└─────────────────────┴───────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    REDIS CLUSTER                                                    │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│   FEED CACHE:                              COUNTERS:                                               │
│   feed:{user_id} = [P1, P2, P3, ...]       post:{id}:like_count = 1234                            │
│   (Just post IDs!)                          post:{id}:comment_count = 56                           │
│                                             user:{id}:follower_count = 10000                       │
│   SESSION/AUTH:                                                                                     │
│   session:{token} = {user_id, ...}         RATE LIMITING:                                          │
│                                             rate:{user_id}:{action} = count                        │
│   USER CACHE:                                                                                       │
│   user:{id}:profile = {...}                ONLINE STATUS:                                          │
│   user:{id}:following = {U1, U2, ...}      user:{id}:last_seen = timestamp                        │
│                                                                                                     │
│   STORY STATE:                                                                                      │
│   user:{id}:seen_stories = {S1, S2}        users_with_active_stories = {U1, U2, ...}              │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATABASE LAYER                                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│   ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐                      │
│   │   CASSANDRA         │   │     MYSQL           │   │  ELASTICSEARCH      │                      │
│   │   (Posts, Likes)    │   │   (Users, Social)   │   │  (Search)           │                      │
│   ├─────────────────────┤   ├─────────────────────┤   ├─────────────────────┤                      │
│   │                     │   │                     │   │                     │                      │
│   │ • posts_by_user     │   │ • users             │   │ • users index       │                      │
│   │ • likes_by_post     │   │ • following         │   │ • hashtags index    │                      │
│   │ • likes_by_user     │   │ • followers         │   │ • locations index   │                      │
│   │ • comments_by_post  │   │ • blocks            │   │                     │                      │
│   │ • stories_by_user   │   │ • close_friends     │   │ WHY:                │                      │
│   │ • messages          │   │                     │   │ • Full-text search  │                      │
│   │                     │   │ WHY:                │   │ • Fuzzy matching    │                      │
│   │ WHY:                │   │ • ACID for social   │   │ • Autocomplete      │                      │
│   │ • Massive scale     │   │ • Complex queries   │   │                     │                      │
│   │ • Write-heavy       │   │ • Transactions      │   │                     │                      │
│   └─────────────────────┘   └─────────────────────┘   └─────────────────────┘                      │
│                                                                                                     │
│   SHARDING STRATEGY:                                                                                │
│   ┌───────────────────────┬──────────────────────┬────────────────────────────────────────────────┐ │
│   │  DATA TYPE            │  SHARD KEY           │  WHY                                           │ │
│   ├───────────────────────┼──────────────────────┼────────────────────────────────────────────────┤ │
│   │  Posts                │  user_id             │  "Get user's posts" = single partition        │ │
│   │  Users                │  hash(user_id)       │  Uniform distribution                         │ │
│   │  Likes by post        │  post_id             │  "Who liked this?" = single partition         │ │
│   │  Likes by user        │  user_id             │  "What did I like?" = single partition        │ │
│   │  Messages             │  conversation_id     │  Chat history = single partition              │ │
│   │  Feed cache           │  user_id             │  User's feed = single lookup                  │ │
│   └───────────────────────┴──────────────────────┴────────────────────────────────────────────────┘ │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    ASYNC PROCESSING (KAFKA)                                         │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│   TOPICS:                                     CONSUMERS:                                           │
│                                                                                                     │
│   post-events                                 Feed Fanout Service                                  │
│     - New post created                          - Push to followers' feeds                         │
│     - Post deleted                                                                                  │
│                                               Notification Service                                  │
│   engagement-events                             - Push notifications (APNs/FCM)                    │
│     - Likes, comments                           - In-app notifications                             │
│     - Shares, saves                                                                                 │
│                                               Analytics Service                                     │
│   social-events                                 - Engagement metrics                               │
│     - Follow/unfollow                           - Content performance                              │
│     - Blocks                                                                                        │
│                                               Search Indexer                                        │
│   story-events                                  - Update Elasticsearch                             │
│     - Story created/expired                                                                         │
│     - Story viewed                            Recommendation Service                               │
│                                                 - ML model training                                │
│   message-events                                - Explore page                                     │
│     - New message                                                                                   │
│     - Read receipt                                                                                  │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    MEDIA STORAGE                                                    │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│   S3 STRUCTURE:                               CDN CACHING:                                         │
│                                                                                                     │
│   /media/{user_id}/{post_id}/                 Popular content → Edge cached                        │
│     ├── original.jpg                          TTL: 24 hours for posts                              │
│     ├── thumb_150.jpg                         TTL: 1 hour for Stories                              │
│     ├── medium_640.jpg                                                                              │
│     └── large_1080.jpg                        VIDEO TRANSCODING:                                   │
│                                                 - Multiple resolutions (360p, 720p, 1080p)         │
│   /stories/{user_id}/{story_id}/                - Adaptive bitrate streaming (HLS)                 │
│     ├── video.mp4                               - Thumbnail extraction                             │
│     └── thumbnail.jpg                                                                               │
│                                                                                                     │
│   /reels/{user_id}/{reel_id}/                 LIFECYCLE POLICIES:                                  │
│     └── video.mp4                               - Stories: Delete after 24h                        │
│                                                 - Posts: Keep forever                              │
│                                                 - Move to Glacier after 1 year (cold storage)     │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 5. REQUEST FLOWS

## Flow 1: Upload Post

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              UPLOAD POST FLOW                                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User creates post with photo and caption
           │
           ▼
1. CLIENT UPLOADS MEDIA
   
   a) Request presigned S3 URL from server
   b) Upload directly to S3 (bypass server)
   c) Get media_url back
           │
           ▼
2. CREATE POST RECORD
   
   POST /api/posts
   { caption, media_urls, location, tagged_users }
   
   Insert into Cassandra: posts_by_user
           │
           ▼
3. PUBLISH TO KAFKA
   Topic: "post-events"
   { type: "created", post_id, user_id, timestamp }
           │
           ▼
4. KAFKA CONSUMERS (Async)
   
   ├──► Feed Fanout Service
   │      - Get user's followers
   │      - Push post_id to each follower's feed cache
   │      - Skip celebrities (> 10K followers) - pull model
   │
   ├──► Notification Service
   │      - Notify tagged users
   │      - "@nikhil tagged you in a post"
   │
   ├──► Search Indexer
   │      - Index hashtags
   │      - Index location
   │
   └──► Analytics
         - Track upload metrics

Response to user: Immediate (after POST record created)
Feed fanout happens async!
```

---

## Flow 2: Load News Feed

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              LOAD FEED FLOW                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User opens app
           │
           ▼
1. CHECK FEED CACHE (Redis)
   
   LRANGE feed:U123 0 19
   
   Result: [P789, P456, P123, ...]  ← Just post IDs
   
   Cache HIT → Continue to hydration
   Cache MISS → Generate feed (see below)
           │
           ▼
2. HYDRATE POSTS (Parallel queries)
   
   a) Post data: Cassandra multi-get
   b) Author data: Redis cache (fallback: MySQL)
   c) Like status: Cassandra batch query
   d) Save status: Cassandra batch query
           │
           ▼
3. MERGE CELEBRITY POSTS (Hybrid model)
   
   Get celebrities user follows
   Query their latest posts (pull model)
   Merge with cached feed posts
   Sort by ranking score
           │
           ▼
4. RANK & RETURN
   
   Ranking factors:
     - Recency
     - Engagement (likes, comments)
     - Relationship (close friends)
     - Content type preference
   
   Return top 20 posts


CACHE MISS → GENERATE FEED:

1. Get users I follow (MySQL)
2. Get their recent posts (Cassandra)
3. Rank and store in Redis
4. Return top 20
```

---

## Flow 3: Like a Post

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              LIKE POST FLOW                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User taps ❤️ on post P123
           │
           ▼
1. CHECK DUPLICATE (Cassandra)
   
   SELECT * FROM likes_by_user 
   WHERE user_id = U456 AND post_id = P123
   
   Already liked → Return (idempotent)
           │
           ▼
2. WRITE TO CASSANDRA (Source of Truth)
   
   a) INSERT INTO likes_by_post (post_id, user_id, ts)
   b) INSERT INTO likes_by_user (user_id, post_id, ts)
   c) UPDATE post_counters SET like_count = like_count + 1
           │
           ▼
3. UPDATE REDIS CACHE
   
   INCR post:P123:like_count
           │
           ▼
4. PUBLISH TO KAFKA
   Topic: "engagement-events"
   { type: "like", post_id, liker_id, author_id }
           │
           ▼
5. CONSUMERS
   
   ├──► Notification Service
   │      - Notify post author
   │      - Batch: "X and 99 others liked your post"
   │
   └──► Analytics
         - Track engagement


Response: Immediate (optimistic UI)
Backend processing is async
```

---

## Flow 4: Follow User

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              FOLLOW FLOW                                                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

U123 follows U456
           │
           ▼
1. VALIDATION
   - Not already following?
   - Not blocked by U456?
   - Is U456 private?
           │
           ├─── If private → Create follow REQUEST (pending)
           │
           ▼
2. WRITE TO MYSQL (Both tables!)
   
   INSERT INTO following (user_id=U123, following_id=U456)
   INSERT INTO followers (user_id=U456, follower_id=U123)
           │
           ▼
3. UPDATE COUNTERS
   
   a) MySQL: Increment counts
   b) Redis: INCR user:U456:follower_count
             INCR user:U123:following_count
           │
           ▼
4. UPDATE REDIS CACHE
   
   SADD user:U123:following U456
   SADD user:U456:followers U123
           │
           ▼
5. PUBLISH TO KAFKA
   Topic: "social-events"
           │
           ├──► Feed Service
           │      - Add U456's recent posts to U123's feed
           │
           ├──► Notification Service
           │      - "U123 started following you"
           │
           └──► Suggestions Service
                 - Update "people you may know"
```

---

## Flow 5: Stories

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              STORY FLOW                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

USER UPLOADS STORY:

1. Upload media to S3 (with 24h expiry lifecycle)
2. Create story record in Cassandra
3. Add user to "users_with_active_stories" set (Redis)
4. Notify close friends if enabled


USER VIEWS STORY TRAY:

1. Get users I follow with active stories
   
   Redis: SINTER user:U123:following users_with_active_stories
   Result: [U456, U789]
           │
           ▼
2. For each, check "Have I seen all their stories?"
   
   Redis: user:U123:seen_stories
           │
           ▼
3. Sort by:
   - Unseen first
   - Close friends first
   - Recency
           │
           ▼
4. Return story tray


USER TAPS STORY:

1. Load stories for that user (Cassandra)
2. Stream video from CDN
3. On view complete:
   - Record view in Cassandra (story_views table)
   - Add to user:U123:seen_stories (Redis, 24h TTL)


STORY EXPIRY:

Background job every minute:
1. Find stories where expires_at < now()
2. Remove from users_with_active_stories
3. Delete media from S3 (or let lifecycle do it)
4. Archive to cold storage if needed
```

---

## Flow 6: Reels

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              REELS FLOW                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

REELS ARE DIFFERENT FROM STORIES:
  - Permanent (not 24h)
  - Discoverable by anyone (not just followers)
  - Algorithm-driven feed (not chronological)


USER VIEWS REELS TAB:

1. RECOMMENDATION ENGINE
   
   Input: User's interests, watch history, engagement
   Output: Ranked list of reel_ids
   
   Factors:
     - Watch time percentage
     - Likes/comments/shares
     - Following vs not following
     - Content category (dance, comedy, food)
     - Recency
           │
           ▼
2. DEDUPLICATION
   
   Use Bloom filter: user:U123:seen_reels_bloom
   Filter out already-seen reels
           │
           ▼
3. RETURN BATCH (20 reels)
   
   Client preloads next 2-3 videos
   Infinite scroll


VIEW TRACKING:

As user watches reel:
1. Track watch duration
2. If > 3 seconds → Count as view
3. Update engagement metrics (Kafka)
4. Add to Bloom filter (seen)


REEL RECOMMENDATION:

Pre-computed by ML pipeline:
1. Collaborative filtering (users with similar tastes)
2. Content-based (video features, hashtags)
3. Real-time signals (trending, viral)

Stored per user:
  user:U123:reel_recommendations = [R1, R2, R3, ...]
  Refreshed every few hours
```

---

## Flow 7: Direct Messages

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              DIRECT MESSAGES FLOW                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

U123 sends message to U456
           │
           ▼
1. GET/CREATE CONVERSATION
   
   conversation_id = hash(min(U123, U456), max(U123, U456))
   
   Or for groups: unique conversation_id
           │
           ▼
2. WRITE MESSAGE TO CASSANDRA
   
   INSERT INTO messages (
     conversation_id,
     message_id,
     sender_id,
     content,
     timestamp
   )
           │
           ▼
3. UPDATE CONVERSATION METADATA
   
   Redis: conversation:{id}:last_message = "Hey!"
          conversation:{id}:last_timestamp = now
          conversation:{id}:unread:U456 = +1
           │
           ▼
4. DELIVER VIA WEBSOCKET
   
   Find U456's WebSocket connection
   Push message in real-time
   
   If offline → Queue for later
           │
           ▼
5. PUSH NOTIFICATION (if offline)
   
   APNs/FCM: "U123: Hey!"


READ RECEIPTS:

U456 reads message:
1. Mark as read in Redis
2. Send "read" status to U123 via WebSocket
3. Write to Cassandra async


TYPING INDICATOR:

U123 is typing:
1. Send via WebSocket only (not persisted)
2. Debounced (every 2 seconds)
3. Auto-expires after 5 seconds
```

---

## Flow 8: Search

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SEARCH FLOW                                                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User types "travel" in search
           │
           ▼
1. AUTOCOMPLETE (As user types)
   
   Query Elasticsearch:
     - Users with "travel" in username/name
     - Hashtags starting with "travel"
     - Locations containing "travel"
   
   Return top 5 of each
           │
           ▼
2. FULL SEARCH (On submit)
   
   Elasticsearch queries:
   
   a) Users index:
      { "match": { "name": "travel" } }
      Boost: verified accounts, follower count
   
   b) Hashtags index:
      { "prefix": { "tag": "travel" } }
      Sort by post count
   
   c) Locations index:
      { "match": { "name": "travel" } }
           │
           ▼
3. PERSONALIZATION
   
   Re-rank results based on:
     - Users you might know
     - Hashtags you've used
     - Locations you've been
           │
           ▼
4. RETURN COMBINED RESULTS
   
   {
     "users": [...],
     "hashtags": [...],
     "places": [...]
   }


HASHTAG SEARCH:

User taps #travel:
1. Get posts with hashtag (Cassandra, paginated)
2. Top posts (most engagement)
3. Recent posts (chronological)
```

---

## Flow 9: Notifications

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              NOTIFICATIONS FLOW                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

NOTIFICATION TYPES:
  - Likes on your posts
  - Comments on your posts
  - New followers
  - Mentions (@username)
  - Story mentions
  - DM notifications


GENERATION:

Event (like, comment, follow) → Kafka
           │
           ▼
Notification Service:
           │
           ├──► DETERMINE RECIPIENTS
           │      - Post author for likes/comments
           │      - Mentioned users
           │      - Tagged users
           │
           ├──► CHECK PREFERENCES
           │      - Notifications enabled?
           │      - This type enabled?
           │      - Muted this user?
           │
           ├──► AGGREGATE/BATCH
           │      - Don't send 100 "X liked your post"
           │      - Batch into "X and 99 others..."
           │      - Rate limit: max 1 per type per minute
           │
           └──► DELIVER
                  - WebSocket (if online) → In-app
                  - Push notification (if offline) → APNs/FCM


STORAGE:

Cassandra: notifications
┌────────────────────────────────────────────────────────────────────────────┐
│ user_id (PK) │ notification_id │ type │ data │ created_at │ read │       │
├──────────────┼─────────────────┼──────┼──────┼────────────┼──────┤       │
│ U456         │ N001            │ like │ {...}│ 10:00      │ false│       │
│ U456         │ N002            │ follow│{...}│ 10:05      │ false│       │
└────────────────────────────────────────────────────────────────────────────┘

Partition by user_id → Fast "get my notifications"


MARK AS READ:

User opens notification tab:
1. Return unread notifications
2. Mark all as read (batch update)
3. Update unread badge count
```

---

# 6. "DID I LIKE THIS?" — Complete Flow

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              CHECKING LIKE STATUS                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

When displaying a post, we need to show:
  - ❤️ if user liked it
  - 🤍 if user hasn't liked it

THIS IS NOT STORED IN THE FEED TABLE!

Separate table: likes_by_user

┌────────────────────────────────────────────────────────────────────────────┐
│ user_id (PK) │ post_id       │ liked_at                                   │
├──────────────┼───────────────┼────────────                                 │
│ U123         │ P789          │ 2024-02-01                                  │
│ U123         │ P456          │ 2024-02-02                                  │
│ U123         │ P100          │ 2024-02-03                                  │
└────────────────────────────────────────────────────────────────────────────┘


FLOW:

1. Load feed: get post_ids [P789, P456, P123, P100]
           │
           ▼
2. BATCH QUERY for like status:
   
   SELECT post_id FROM likes_by_user 
   WHERE user_id = U123 AND post_id IN (P789, P456, P123, P100)
   
   Result: [P789, P456, P100]  ← These are liked
           │
           ▼
3. BUILD RESPONSE:
   
   posts = [
     { id: P789, ..., is_liked: true },
     { id: P456, ..., is_liked: true },
     { id: P123, ..., is_liked: false },
     { id: P100, ..., is_liked: true }
   ]


OPTIMIZATION: Cache recent likes in Redis

Redis: user:U123:recent_likes = {P789, P456, P100}
       TTL: 1 hour
       Max 1000 entries

Check Redis first, fallback to Cassandra
```

---

# 7. EDGE CASES & ERROR HANDLING

## Celebrity Follow (Millions of Followers)

```
Problem: Taylor Swift has 400M followers
         - Can't push to 400M feed caches
         - Can't load 400M follower list

Solution:
  1. Pull model for celebrities (> 10K followers)
  2. Paginated follower list
  3. Show "sampled" followers: "Followed by friend1, friend2, and 400M others"
```

---

## Double Tap Race Condition

```
Problem: User rapidly taps like twice

Solution:
  1. Check existence before write
  2. Idempotent operations
  3. Unique constraint on (post_id, user_id)
```

---

## Feed Cache Expired

```
Problem: User inactive for days, cache expired

Solution:
  1. Cache miss → Generate feed on-the-fly
  2. Limit to last 24-48 hours of posts
  3. Async: Rebuild full cache in background
```

---

## Viral Post (Millions of Likes)

```
Problem: Post goes viral, millions of like events

Solution:
  1. Rate limit notifications to author
  2. Batch into "X and 999,999 others..."
  3. Sample for "who liked" list
  4. Use approximate count (HyperLogLog)
```

---

## Story View Tracking at Scale

```
Problem: Celebrity story viewed by millions

Solution:
  1. Don't show full viewer list
  2. Show sample + count
  3. Write views async via Kafka
  4. Aggregate counts, not individual rows
```

---

# 8. TECHNOLOGY STACK

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    TECHNOLOGY SUMMARY                                   │
└─────────────────────────────────────────────────────────────────────────┘

│ Component         │ Technology        │ Why                            │
├───────────────────┼───────────────────┼────────────────────────────────┤
│ API              │ Python/Django     │ Rapid development               │
│ Real-time        │ WebSocket         │ DMs, notifications              │
│ Cache            │ Redis             │ Feed, sessions, counters        │
│ Posts/Likes      │ Cassandra         │ Write-heavy, massive scale      │
│ Users/Social     │ MySQL             │ ACID, complex queries           │
│ Search           │ Elasticsearch     │ Full-text, fuzzy                │
│ Queue            │ Kafka             │ Event-driven, durability        │
│ Media            │ S3 + CDN          │ Blob storage, global delivery   │
│ Video            │ FFmpeg            │ Transcoding                     │
│ Push             │ APNs/FCM          │ Mobile notifications            │
│ ML               │ PyTorch           │ Recommendations                 │
│ Monitoring       │ Prometheus/Grafana│ Metrics, alerts                 │
└───────────────────────────────────────────────────────────────────────────
```

---

# 9. INTERVIEW TALKING POINTS

## Key Design Decisions

```
1. HYBRID FEED MODEL
   - Push for regular users (pre-compute feeds)
   - Pull for celebrities (on-demand merge)
   - Tradeoff: Latency vs fanout cost

2. DENORMALIZED DATA
   - Likes stored twice (by_post and by_user)
   - Follows stored twice (following and followers)
   - Tradeoff: Storage vs query speed

3. CASSANDRA FOR POSTS
   - Write-heavy workload (100M posts/day)
   - Partition by user_id (fast user queries)
   - Eventual consistency OK for social data

4. MYSQL FOR SOCIAL GRAPH
   - Need ACID for follow transactions
   - Complex queries (mutual friends)
   - Smaller dataset than posts/likes

5. REDIS AS CACHE (NOT source of truth)
   - Feed cache, counters, sessions
   - Can be rebuilt from Cassandra/MySQL
   - Regional deployment for low latency

6. KAFKA FOR DECOUPLING
   - Post events → multiple consumers
   - Async processing (notifications, analytics)
   - Durability and replay capability

7. STORIES AUTO-EXPIRY
   - S3 lifecycle policies
   - Redis TTL for active story tracking
   - Background cleanup jobs
```

---

# 10. QUICK REFERENCE

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    INSTAGRAM CHEAT SHEET                                │
└─────────────────────────────────────────────────────────────────────────┘

FEED:
  • Stored as post_ids only (Redis)
  • Hydrated at read time (parallel queries)
  • Hybrid: Push for regular, Pull for celebrities

LIKES:
  • Source of truth: Cassandra (likes_by_post, likes_by_user)
  • Counter cache: Redis (can be rebuilt)
  • Batch query for "did I like?"

SOCIAL GRAPH:
  • Two tables: following, followers (denormalized)
  • MySQL for ACID transactions
  • Counters updated on each follow/unfollow

STORIES:
  • 24-hour TTL (S3 lifecycle + Redis)
  • Exact view tracking (Cassandra)
  • Separate "users_with_active_stories" set

REELS:
  • Algorithm-driven (not chronological)
  • Bloom filter for dedup
  • Pre-computed recommendations (ML)

SEARCH:
  • Elasticsearch for full-text
  • Indexes: users, hashtags, locations
  • Autocomplete as user types

DMs:
  • WebSocket for real-time
  • Cassandra for persistence
  • Partition by conversation_id
```

---

# 11. REELS & RECOMMENDATION SYSTEM (TikTok-Level Deep Dive)

This section covers everything needed for TikTok/Reels system design interviews.

---

## 11.1 Scale of Reels/TikTok

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              REELS/TIKTOK SCALE                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Daily Active Users:           1 billion
Videos uploaded/day:          10 million
Videos watched/user/day:      100+ videos
Total video views/day:        100 BILLION
Average watch time:           45 minutes/user
Video length:                 15-60 seconds

STORAGE:
  Original videos:            10M × 50 MB = 500 TB/day
  Multiple resolutions (5×):  2.5 PB/day
  Yearly:                     ~900 PB/year

BANDWIDTH:
  100B views × 10 MB (avg) = 1 EXABYTE/day egress!
  (CDN is critical!)
```

---

## 11.2 Why Reels/TikTok is Different

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    REELS vs INSTAGRAM FEED - KEY DIFFERENCES                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

│ Aspect              │ Instagram Feed        │ Reels/TikTok                    │
├─────────────────────┼───────────────────────┼─────────────────────────────────┤
│ Content source      │ People you follow     │ Anyone in the world             │
│ Discovery           │ Social graph based    │ Algorithm based                 │
│ Ordering            │ Chronological + rank  │ Pure ML recommendation          │
│ Engagement signal   │ Likes, comments       │ Watch time, replays, shares     │
│ Content type        │ Mixed (photo/video)   │ Video only (15-60 sec)          │
│ User intent         │ "What are friends up to?" │ "Entertain me"              │
│ Cold start          │ Need to follow first  │ Works immediately               │
│ Virality            │ Limited to followers  │ Anyone can go viral             │
└─────────────────────┴───────────────────────┴─────────────────────────────────┘
```

---

## 11.3 Complete Reels/TikTok Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              REELS/TIKTOK SYSTEM ARCHITECTURE                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                    ┌─────────────────┐
                                    │   MOBILE APP    │
                                    │  (iOS/Android)  │
                                    └────────┬────────┘
                                             │
                              ┌──────────────┼──────────────┐
                              │              │              │
                              ▼              ▼              ▼
                    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
                    │   UPLOAD    │  │    FEED     │  │ INTERACTION │
                    │   SERVICE   │  │   SERVICE   │  │   SERVICE   │
                    └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
                           │                │                │
                           ▼                │                │
┌──────────────────────────────────────────┐│                │
│           VIDEO PROCESSING PIPELINE       ││                │
│                                          ││                │
│  ┌──────────┐  ┌──────────┐  ┌────────┐ ││                │
│  │ Transcode│→ │ Generate │→ │Content │ ││                │
│  │ (FFmpeg) │  │Thumbnails│  │Moderate│ ││                │
│  └──────────┘  └──────────┘  └────────┘ ││                │
│       │                           │      ││                │
│       ▼                           ▼      ││                │
│  ┌──────────┐              ┌──────────┐ ││                │
│  │ Multiple │              │   ML     │ ││                │
│  │Resolutions│              │ Features │ ││                │
│  │ 360-1080p│              │Extraction│ ││                │
│  └──────────┘              └──────────┘ ││                │
└──────────────────────────────────────────┘│                │
                           │                │                │
                           ▼                ▼                ▼
         ┌─────────────────────────────────────────────────────────────┐
         │                        KAFKA                                 │
         │   Topics: video-uploads, user-interactions, view-events     │
         └─────────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────────────────────┐
           │               │                               │
           ▼               ▼                               ▼
┌─────────────────┐ ┌─────────────────┐         ┌─────────────────────┐
│  REAL-TIME      │ │  BATCH          │         │  FEATURE STORE      │
│  PROCESSING     │ │  PROCESSING     │         │                     │
│                 │ │                 │         │  User features      │
│  Apache Flink   │ │  Apache Spark   │         │  Video features     │
│  Kafka Streams  │ │  (Daily jobs)   │         │  Interaction feats  │
│                 │ │                 │         │                     │
│  • Trending     │ │  • User embed   │         │  Redis (real-time)  │
│  • View counts  │ │  • Video embed  │         │  Cassandra (batch)  │
│  • Engagement   │ │  • Collab filter│         │                     │
└────────┬────────┘ └────────┬────────┘         └──────────┬──────────┘
         │                   │                             │
         └───────────────────┼─────────────────────────────┘
                             │
                             ▼
         ┌─────────────────────────────────────────────────────────────┐
         │                  RECOMMENDATION ENGINE                       │
         │                                                             │
         │   ┌───────────┐  ┌───────────┐  ┌───────────┐              │
         │   │ Candidate │→ │  Ranking  │→ │ Diversity │              │
         │   │ Generation│  │   Model   │  │   Filter  │              │
         │   │ (1000s)   │  │  (Top 100)│  │  (Top 50) │              │
         │   └───────────┘  └───────────┘  └───────────┘              │
         │                                                             │
         └─────────────────────────────────────────────────────────────┘
                             │
                             ▼
         ┌─────────────────────────────────────────────────────────────┐
         │                  PRE-COMPUTED FEEDS                          │
         │                                                             │
         │   Redis: user:{id}:reel_recommendations = [R1, R2, ...]    │
         │   Updated every few hours by batch pipeline                 │
         │   Refreshed on-demand for active users                      │
         └─────────────────────────────────────────────────────────────┘
```

---

## 11.4 Video Upload & Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              VIDEO UPLOAD FLOW                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User records/uploads video
           │
           ▼
1. UPLOAD TO S3 (Raw video)
   
   - Chunked upload for large files
   - Resume support for poor connections
   - Client-side compression (optional)
           │
           ▼
2. TRIGGER VIDEO PROCESSING (AWS Lambda / SQS)
   
   Message: { video_id, s3_path, user_id }
           │
           ▼
3. VIDEO PROCESSING WORKERS (Kubernetes pods)
   
   a) TRANSCODING (FFmpeg / AWS MediaConvert)
      ┌────────────────────────────────────────────────────────┐
      │  Original → Multiple resolutions                       │
      │                                                        │
      │  360p  (low bandwidth, 0.5 Mbps)                      │
      │  480p  (medium, 1 Mbps)                               │
      │  720p  (HD, 2.5 Mbps)                                 │
      │  1080p (Full HD, 5 Mbps)                              │
      │                                                        │
      │  Format: H.264/H.265 (HEVC for newer devices)         │
      │  Container: MP4 with fragmented segments (for HLS)    │
      └────────────────────────────────────────────────────────┘
   
   b) GENERATE THUMBNAILS
      - Every 1 second for seekbar preview
      - Best frame selection for cover
      - WebP format for fast loading
   
   c) AUDIO ANALYSIS
      - Extract audio fingerprint (for music detection)
      - Speech-to-text (for captions/search)
      - Music identification (Shazam-like)
   
   d) CONTENT MODERATION (ML Models)
      - Nudity detection
      - Violence detection
      - Copyright check (audio fingerprint)
      - Spam/bot detection
      
      If flagged → Queue for human review
           │
           ▼
4. FEATURE EXTRACTION (ML Pipeline)
   
   ┌────────────────────────────────────────────────────────┐
   │  VIDEO FEATURES (for recommendation)                   │
   │                                                        │
   │  Visual:                                               │
   │    - Object detection (people, animals, food)          │
   │    - Scene classification (indoor, outdoor, beach)     │
   │    - Color palette                                     │
   │    - Motion intensity                                  │
   │                                                        │
   │  Audio:                                                │
   │    - Music genre                                       │
   │    - Speech content (transcription)                    │
   │    - Sound effects                                     │
   │                                                        │
   │  Metadata:                                             │
   │    - Hashtags                                          │
   │    - Caption text                                      │
   │    - Creator category                                  │
   │    - Duration                                          │
   │                                                        │
   │  Output: Video embedding vector (512-1024 dimensions)  │
   └────────────────────────────────────────────────────────┘
           │
           ▼
5. STORE VIDEO METADATA (Cassandra)
   
   videos table:
   ┌──────────────────────────────────────────────────────────────────┐
   │ video_id │ user_id │ s3_urls │ duration │ status │ features    │
   └──────────────────────────────────────────────────────────────────┘
           │
           ▼
6. INDEX FOR DISCOVERY
   
   - Publish to Kafka: "video-ready"
   - Add to creator's video list
   - Index in Elasticsearch (for search)
   - Add to candidate pool for recommendation
           │
           ▼
7. NOTIFY CREATOR
   
   "Your video is live!"
   (Typically 1-5 minutes after upload)
```

---

## 11.5 Recommendation System — Complete Deep Dive

### 11.5.1 The Two-Tower Model

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              TWO-TOWER ARCHITECTURE                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

TikTok and most modern recommendation systems use the Two-Tower model:

                    ┌─────────────────┐     ┌─────────────────┐
                    │   USER TOWER    │     │  VIDEO TOWER    │
                    └────────┬────────┘     └────────┬────────┘
                             │                       │
                    ┌────────▼────────┐     ┌────────▼────────┐
                    │ User Features   │     │ Video Features  │
                    │                 │     │                 │
                    │ - Demographics  │     │ - Visual embed  │
                    │ - Watch history │     │ - Audio embed   │
                    │ - Liked videos  │     │ - Hashtags      │
                    │ - Following     │     │ - Creator info  │
                    │ - Time of day   │     │ - Duration      │
                    │ - Device type   │     │ - Language      │
                    └────────┬────────┘     └────────┬────────┘
                             │                       │
                    ┌────────▼────────┐     ┌────────▼────────┐
                    │  Dense Layers   │     │  Dense Layers   │
                    │   (Neural Net)  │     │   (Neural Net)  │
                    └────────┬────────┘     └────────┬────────┘
                             │                       │
                    ┌────────▼────────┐     ┌────────▼────────┐
                    │ User Embedding  │     │ Video Embedding │
                    │  (256-dim vec)  │     │  (256-dim vec)  │
                    └────────┬────────┘     └────────┬────────┘
                             │                       │
                             └──────────┬────────────┘
                                        │
                                        ▼
                             ┌─────────────────────┐
                             │   Similarity Score  │
                             │   dot(user, video)  │
                             └─────────────────────┘

WHY TWO TOWERS?
  - User embeddings computed at request time (user features change)
  - Video embeddings pre-computed and cached (video features static)
  - Fast nearest neighbor search using video embeddings
```

---

### 11.5.2 Feature Engineering

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              FEATURE CATEGORIES                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

USER FEATURES (computed in real-time):
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Feature               │ Type      │ Example                │ Why It Matters                      │
├───────────────────────┼───────────┼────────────────────────┼─────────────────────────────────────┤
│ Age                   │ Numeric   │ 25                     │ Content preferences vary by age     │
│ Gender                │ Categorical│ Female                │ Content consumption patterns        │
│ Country               │ Categorical│ India                 │ Language, culture preferences       │
│ Device type           │ Categorical│ iPhone                │ Video quality preferences           │
│ Network type          │ Categorical│ 4G                    │ Can show higher res videos          │
│ Time of day           │ Numeric   │ 22:30                  │ Entertainment vs educational        │
│ Day of week           │ Categorical│ Saturday              │ More time on weekends               │
│ Session duration      │ Numeric   │ 15 min                 │ Engagement level                    │
│ Videos watched today  │ Numeric   │ 50                     │ Content fatigue                     │
│ Recent categories     │ List      │ [dance, comedy]        │ Current interest                    │
│ Favorite creators     │ List      │ [C1, C2, C3]           │ Similar creator suggestions         │
│ Historical CTR        │ Numeric   │ 0.15                   │ How clickable is user               │
│ Avg watch time %      │ Numeric   │ 0.75                   │ Engagement quality                  │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘

VIDEO FEATURES (computed at upload, cached):
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Feature               │ Type      │ Example                │ How It's Extracted                  │
├───────────────────────┼───────────┼────────────────────────┼─────────────────────────────────────┤
│ Visual embedding      │ Vector    │ [0.2, -0.5, ...]       │ CNN (ResNet/Vision Transformer)     │
│ Audio embedding       │ Vector    │ [0.1, 0.3, ...]        │ Audio classification model          │
│ Hashtags              │ List      │ [travel, beach]        │ User-provided + auto-detected       │
│ Caption embedding     │ Vector    │ [0.4, -0.2, ...]       │ BERT/Sentence Transformer           │
│ Duration              │ Numeric   │ 30 seconds             │ Direct                              │
│ Music ID              │ Categorical│ Song_12345            │ Audio fingerprinting                │
│ Language              │ Categorical│ English               │ Speech detection + caption          │
│ Object tags           │ List      │ [person, dog, car]     │ Object detection (YOLO)             │
│ Scene type            │ Categorical│ outdoor, beach        │ Scene classification                │
│ Text overlay          │ Text      │ "Wait for it..."       │ OCR (Optical Character Recognition) │
│ Creator follower cnt  │ Numeric   │ 1,000,000              │ From user profile                   │
│ Creator category      │ Categorical│ Influencer            │ Based on content history            │
│ Upload time           │ Timestamp │ 2024-02-07 10:00       │ Direct                              │
│ Historical engagement │ Numeric   │ 0.12 (12% like rate)   │ Computed after initial views        │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘

INTERACTION FEATURES (user-video pairs, real-time):
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Feature               │ How Collected           │ Signal Strength                              │
├───────────────────────┼─────────────────────────┼──────────────────────────────────────────────┤
│ Watch time %          │ Client sends progress   │ STRONGEST signal! (70% watch = strong like)  │
│ Completed             │ Watched 100%            │ Very positive                                │
│ Replayed              │ Rewatched same video    │ Extremely positive                           │
│ Liked                 │ Explicit action         │ Strong positive                              │
│ Commented             │ Explicit action         │ Very strong positive (effort required)       │
│ Shared                │ Explicit action         │ Extremely positive (endorsement)             │
│ Saved/Bookmarked      │ Explicit action         │ Strong positive                              │
│ Followed creator      │ Explicit action         │ Very strong positive                         │
│ Skipped early         │ < 3 sec watch           │ Strong NEGATIVE                              │
│ "Not interested"      │ Explicit action         │ Very strong negative                         │
│ Reported              │ Explicit action         │ Extremely negative                           │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘

KEY INSIGHT: Watch time > Likes!
  - Likes can be faked or habitual
  - Watch time is hard to fake (cost = actual time)
  - TikTok optimizes for WATCH TIME, not likes
```

---

### 11.5.3 Recommendation Pipeline Stages

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              THREE-STAGE RECOMMENDATION                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User opens Reels tab → Need to show 50 videos
But there are 500 MILLION videos in the corpus!

STAGE 1: CANDIDATE GENERATION (1000s of candidates)
─────────────────────────────────────────────────
Goal: Reduce 500M → 10,000 candidates (fast, approximate)

Methods:
  a) COLLABORATIVE FILTERING
     "Users similar to you watched these videos"
     
     Precomputed user clusters:
       user_cluster:{cluster_id}:popular_videos = [V1, V2, ...]
  
  b) CONTENT-BASED
     "Similar to videos you liked"
     
     ANN (Approximate Nearest Neighbor) search:
       - Index all video embeddings in FAISS/Milvus
       - Query with user's preference vector
       - Get top 1000 similar videos in O(log n)
  
  c) SOCIAL GRAPH
     "Videos from creators you follow"
     "Videos friends engaged with"
  
  d) TRENDING
     "Popular videos in last 24 hours"
     "Trending in your region/country"
  
  e) NEW CREATOR BOOST
     "Give new videos initial exposure for cold start"

Output: ~10,000 candidate video IDs


STAGE 2: RANKING (Score each candidate)
────────────────────────────────────────
Goal: Predict engagement for each candidate

Model: Deep Neural Network (DNN) / Transformer

Input features (per user-video pair):
  - User embedding (from Two-Tower)
  - Video embedding (from Two-Tower)
  - Interaction features
  - Context features (time, device)

Output: Predicted engagement score
  - P(watch > 50%)
  - P(like)
  - P(share)
  - P(follow)

Combined into single ranking score:
  score = w1 * P(watch) + w2 * P(like) + w3 * P(share) + w4 * P(follow)

Select top 100-200 candidates


STAGE 3: RERANKING & DIVERSITY
──────────────────────────────
Goal: Ensure good user experience (not just highest scores)

Rules applied:
  a) DIVERSITY
     - Don't show 10 dance videos in a row
     - Mix categories: comedy, food, sports, ...
     - Mix creator follower counts (not all mega-influencers)
  
  b) FRESHNESS
     - Boost newly uploaded videos
     - Balance viral oldies with fresh content
  
  c) CREATOR FAIRNESS
     - Don't let same creator appear too often
     - Give exposure to new creators
  
  d) ANTI-ECHO-CHAMBER
     - Inject slightly different content
     - Explore vs Exploit balance
  
  e) AD SLOTS
     - Reserve positions for ads
     - Ad every 5-10 videos

Output: Final 50 videos to show
```

---

### 11.5.4 Apache Spark for Batch Processing

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SPARK BATCH PIPELINE                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Apache Spark jobs run DAILY (or every few hours) to compute:

JOB 1: USER EMBEDDINGS (Daily, 6 hours)
───────────────────────────────────────
Input:  User interaction logs (100 TB/day)
Output: User embedding vectors (store in Feature Store)

from pyspark.sql import SparkSession
from pyspark.ml.feature import Word2Vec

spark = SparkSession.builder.appName("UserEmbeddings").getOrCreate()

# Load user watch history
user_history = spark.read.parquet("s3://data/interactions/")

# Create "sentences" of watched video IDs per user
user_sequences = user_history \
    .groupBy("user_id") \
    .agg(collect_list(col("video_id")).alias("watched_videos"))

# Word2Vec to learn embeddings (videos as "words", history as "sentence")
word2vec = Word2Vec(vectorSize=128, inputCol="watched_videos", outputCol="user_embedding")
model = word2vec.fit(user_sequences)

# Save embeddings
model.transform(user_sequences).write.parquet("s3://features/user_embeddings/")


JOB 2: VIDEO EMBEDDINGS (On upload + Daily refresh)
────────────────────────────────────────────────────
Input:  Video metadata + features
Output: Video embedding vectors

# Combine visual, audio, text features into final embedding
videos = spark.read.parquet("s3://data/videos/")

video_embeddings = videos \
    .withColumn("combined_features", concat_features(
        col("visual_embedding"),
        col("audio_embedding"),
        col("text_embedding"),
        col("hashtag_embedding")
    )) \
    .withColumn("final_embedding", normalize(col("combined_features")))

video_embeddings.write.parquet("s3://features/video_embeddings/")


JOB 3: COLLABORATIVE FILTERING (Daily, 4 hours)
───────────────────────────────────────────────
Algorithm: ALS (Alternating Least Squares)

from pyspark.ml.recommendation import ALS

# User-Video interaction matrix
interactions = spark.read.parquet("s3://data/interactions/") \
    .withColumn("rating", compute_engagement_score(...))

# Train ALS model
als = ALS(maxIter=10, regParam=0.01, 
          userCol="user_id", itemCol="video_id", ratingCol="rating")
model = als.fit(interactions)

# Generate recommendations for all users
user_recs = model.recommendForAllUsers(100)  # Top 100 per user
user_recs.write.parquet("s3://recommendations/als_recs/")


JOB 4: TRENDING COMPUTATION (Hourly)
────────────────────────────────────
# Sliding window of last 24 hours
recent_engagement = spark.read.parquet("s3://data/interactions/") \
    .where(col("timestamp") > current_timestamp() - hours(24))

trending = recent_engagement \
    .groupBy("video_id", "country") \
    .agg(
        count("*").alias("views"),
        sum(col("watch_time") / col("duration")).alias("total_watch_pct"),
        sum(col("liked").cast("int")).alias("likes"),
        sum(col("shared").cast("int")).alias("shares")
    ) \
    .withColumn("trending_score", 
        col("views") * 0.3 + 
        col("total_watch_pct") * 0.4 + 
        col("shares") * 10  # Shares weighted heavily
    ) \
    .orderBy(desc("trending_score"))

trending.write.parquet("s3://recommendations/trending/")


JOB 5: USER CLUSTERING (Weekly)
───────────────────────────────
from pyspark.ml.clustering import KMeans

user_embeddings = spark.read.parquet("s3://features/user_embeddings/")

kmeans = KMeans(k=1000, seed=1, featuresCol="user_embedding")
model = kmeans.fit(user_embeddings)

clustered_users = model.transform(user_embeddings)
clustered_users.write.parquet("s3://features/user_clusters/")

# For each cluster, compute popular videos
cluster_popular = interactions \
    .join(clustered_users, "user_id") \
    .groupBy("cluster_id", "video_id") \
    .agg(count("*").alias("cluster_views")) \
    .orderBy(desc("cluster_views"))
```

---

### 11.5.5 Real-Time Processing (Flink/Kafka Streams)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              REAL-TIME STREAM PROCESSING                                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

While Spark handles batch jobs, real-time signals need streaming:

APACHE FLINK / KAFKA STREAMS

1. REAL-TIME VIEW COUNTING
   
   Kafka Topic: view-events
   → Flink processes each view
   → Updates Redis counter: video:{id}:view_count
   → Sliding window: views in last 1 hour
   
   # Flink pseudo-code
   stream = kafka.read_stream("view-events")
   
   view_counts = stream \
       .key_by("video_id") \
       .window(TumblingWindow.of(1.minute)) \
       .count()
   
   view_counts.sink_to(redis("video:views"))


2. TRENDING DETECTION (Real-time)
   
   Detect videos suddenly getting high engagement:
   
   # Flink
   stream = kafka.read_stream("engagement-events")
   
   trending = stream \
       .key_by("video_id") \
       .window(SlidingWindow.of(5.minutes).slide(1.minute)) \
       .aggregate(
           count_views,
           sum_watch_time,
           count_shares
       ) \
       .filter(is_trending)  # Spike detection
   
   trending.sink_to(kafka("trending-alerts"))


3. USER SESSION TRACKING
   
   Build real-time user profile during session:
   
   stream = kafka.read_stream("view-events")
   
   session_profile = stream \
       .key_by("user_id") \
       .window(SessionWindow.of(30.minutes)) \
       .aggregate(
           collect_watched_categories,
           compute_session_interests
       )
   
   # Used for real-time recommendation adjustment


4. FRAUD DETECTION
   
   Detect bot-like behavior:
   
   stream = kafka.read_stream("all-events")
   
   suspicious = stream \
       .key_by("user_id") \
       .window(TumblingWindow.of(1.minute)) \
       .aggregate(count_events) \
       .filter(events_per_minute > 1000)  # Impossible for human
   
   suspicious.sink_to(kafka("fraud-alerts"))
```

---

### 11.5.6 Feature Store Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              FEATURE STORE                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

A Feature Store is a centralized repository for ML features.

                              ┌─────────────────────────┐
                              │     FEATURE STORE       │
                              │                         │
                              │  ┌─────────────────┐   │
                              │  │ ONLINE STORE    │   │
                              │  │ (Redis/DynamoDB)│   │ ← Real-time serving
                              │  │                 │   │    Low latency (<10ms)
                              │  │ user:U123:feats │   │
                              │  │ video:V456:feats│   │
                              │  └─────────────────┘   │
                              │           ↑            │
                              │           │ Sync      │
                              │           │            │
                              │  ┌─────────────────┐   │
                              │  │ OFFLINE STORE   │   │ ← Training data
                              │  │ (S3/HDFS)       │   │    Historical features
                              │  │                 │   │
                              │  │ features/       │   │
                              │  │  user/          │   │
                              │  │  video/         │   │
                              │  │  interaction/   │   │
                              │  └─────────────────┘   │
                              └─────────────────────────┘
                                          ↑
                    ┌─────────────────────┼─────────────────────┐
                    │                     │                     │
            ┌───────┴───────┐     ┌───────┴───────┐     ┌───────┴───────┐
            │ Spark Batch   │     │ Flink Stream  │     │ Feature       │
            │ Jobs          │     │ Processing    │     │ Engineering   │
            │               │     │               │     │ Scripts       │
            │ Daily refresh │     │ Real-time     │     │               │
            └───────────────┘     └───────────────┘     └───────────────┘


FEATURE FRESHNESS REQUIREMENTS:

│ Feature Type      │ Update Frequency │ Storage             │
├───────────────────┼──────────────────┼─────────────────────┤
│ User demographics │ Rarely           │ Offline (Cassandra) │
│ Video embedding   │ Once (on upload) │ Online (Redis)      │
│ User interests    │ Daily            │ Both                │
│ View count        │ Real-time        │ Online (Redis)      │
│ Trending score    │ Hourly           │ Online (Redis)      │
│ User session data │ Real-time        │ Online (Redis)      │
└───────────────────┴──────────────────┴─────────────────────┘


POPULAR FEATURE STORES:
  - Feast (open source)
  - Tecton (enterprise)
  - AWS SageMaker Feature Store
  - Databricks Feature Store
```

---

### 11.5.7 Model Training Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              ML MODEL TRAINING                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

TRAINING DATA PREPARATION:
─────────────────────────
# Positive samples: User engaged with video
# Negative samples: User saw video but didn't engage (or skipped)

training_data = spark.sql("""
    SELECT 
        user_features.*,
        video_features.*,
        CASE 
            WHEN watch_pct > 0.5 OR liked = 1 THEN 1 
            ELSE 0 
        END as label
    FROM impressions
    JOIN user_features ON impressions.user_id = user_features.user_id
    JOIN video_features ON impressions.video_id = video_features.video_id
    WHERE timestamp > current_date - 7  -- Last 7 days
""")

# Typically: 100+ million training examples


MODEL ARCHITECTURE:
──────────────────

import tensorflow as tf

class RecommendationModel(tf.keras.Model):
    def __init__(self):
        super().__init__()
        
        # User tower
        self.user_tower = tf.keras.Sequential([
            tf.keras.layers.Dense(512, activation='relu'),
            tf.keras.layers.Dense(256, activation='relu'),
            tf.keras.layers.Dense(128)  # User embedding
        ])
        
        # Video tower
        self.video_tower = tf.keras.Sequential([
            tf.keras.layers.Dense(512, activation='relu'),
            tf.keras.layers.Dense(256, activation='relu'),
            tf.keras.layers.Dense(128)  # Video embedding
        ])
        
        # Ranking layers (after combining embeddings)
        self.ranking_layers = tf.keras.Sequential([
            tf.keras.layers.Dense(256, activation='relu'),
            tf.keras.layers.Dropout(0.3),
            tf.keras.layers.Dense(128, activation='relu'),
            tf.keras.layers.Dense(1, activation='sigmoid')  # P(engage)
        ])
    
    def call(self, inputs):
        user_features = inputs['user_features']
        video_features = inputs['video_features']
        
        user_emb = self.user_tower(user_features)
        video_emb = self.video_tower(video_features)
        
        # Combine embeddings
        combined = tf.concat([user_emb, video_emb, user_emb * video_emb], axis=1)
        
        return self.ranking_layers(combined)


TRAINING INFRASTRUCTURE:
───────────────────────
- Distributed training on GPU cluster (8-128 GPUs)
- Frameworks: TensorFlow, PyTorch, Horovod
- Training time: 4-12 hours
- Re-trained: Daily or weekly

MODEL SERVING:
─────────────
- TensorFlow Serving / TorchServe
- Batch inference for pre-computation
- Real-time inference for ranking (< 50ms)
- Model size: 100MB - 1GB
```

---

### 11.5.8 Cold Start Problem

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              COLD START SOLUTIONS                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

COLD START = New user or new video with no history

NEW USER COLD START:
───────────────────
1. ASK INTERESTS (Onboarding)
   - "What are you interested in?"
   - Dance, Comedy, Food, Sports...
   
2. USE DEMOGRAPHICS
   - Age, country → Use similar users' preferences
   - "Users in India, age 20-25 like these videos"
   
3. EXPLORE PHASE
   - Show diverse popular content
   - Observe first interactions closely
   - Rapid learning from first 10-20 videos
   
4. CONTEXTUAL SIGNALS
   - Device type → Infer demographics
   - Time of day → Content preferences
   - Language settings

  First 30 minutes: Recommendations improve 3x!


NEW VIDEO COLD START:
────────────────────
1. CONTENT-BASED FEATURES
   - Extract visual/audio features immediately
   - Match to similar existing videos
   
2. CREATOR CONTEXT
   - If creator has existing videos, use performance
   - "This creator's videos typically get 5% like rate"
   
3. INITIAL BOOST
   - Give every new video minimum impressions (1000 views)
   - Measure initial engagement
   - High engagement → More recommendations
   
4. HASHTAG MATCHING
   - #dance → Show to users who like dance videos

  First 500 views: Determines if video goes viral or dies
```

---

### 11.5.9 A/B Testing & Experimentation

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              A/B TESTING FRAMEWORK                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Every recommendation change is A/B tested before full rollout.

METRICS TRACKED:
───────────────
Primary:
  - Time spent (total watch time per session)
  - DAU/MAU (retention)
  - Video completion rate

Secondary:
  - Likes per video
  - Shares per video
  - Videos watched per session
  - Creator follows
  - Content diversity consumed

Guardrail:
  - Reports/complaints
  - User churn
  - App uninstalls


EXPERIMENT INFRASTRUCTURE:
─────────────────────────

User opens app:
       │
       ▼
1. EXPERIMENT ASSIGNMENT
   
   hash(user_id) % 100 → bucket_number
   
   Bucket 0-1:   Control (old algorithm)
   Bucket 2-3:   Experiment A (new model)
   Bucket 4-5:   Experiment B (new features)
   Bucket 6-99: Production
       │
       ▼
2. LOG EVERYTHING
   
   {
     user_id,
     experiment_id,
     variant,
     videos_shown: [...],
     engagement_events: [...],
     session_duration,
     ...
   }
       │
       ▼
3. STATISTICAL ANALYSIS (after 7-14 days)
   
   Compare control vs treatment:
     - T-test for significance
     - Confidence intervals
     - MDE (Minimum Detectable Effect)
       │
       ▼
4. DECISION
   
   If statistically significant improvement:
     - Gradual rollout (10% → 50% → 100%)
   
   If negative or neutral:
     - Kill experiment
     - Analyze why


TikTok runs 100s of A/B tests simultaneously!
```

---

## 11.6 Video Delivery & Optimization

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              VIDEO DELIVERY OPTIMIZATION                                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

1. ADAPTIVE BITRATE STREAMING (ABR)
   ─────────────────────────────────
   Client measures bandwidth → Requests appropriate quality
   
   Protocol: HLS (HTTP Live Streaming)
   
   video.m3u8 (playlist):
     #EXT-X-STREAM-INF:BANDWIDTH=500000
     360p/video.m3u8
     #EXT-X-STREAM-INF:BANDWIDTH=1000000
     480p/video.m3u8
     #EXT-X-STREAM-INF:BANDWIDTH=2500000
     720p/video.m3u8
   
   Client switches quality seamlessly based on network!


2. PRELOADING
   ──────────
   While user watches video N, preload video N+1 and N+2
   
   Preload priority:
     - First 2 seconds of next video (critical for continuity)
     - Thumbnail of next 3 videos
     - Full video of N+1


3. CDN STRATEGY
   ────────────
   - Edge caching for popular videos
   - Regional origin servers
   - Request routing based on latency
   
   Popular video (1M+ views): Cached at ALL edge locations
   Long-tail video (100 views): Fetched from origin on-demand


4. CLIENT-SIDE CACHING
   ───────────────────
   - Cache recently watched videos
   - Offline mode: Pre-download favorites
   - Intelligent cache eviction (LRU + frequency)
```

---

## 11.7 Content Moderation at Scale

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              CONTENT MODERATION PIPELINE                                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

AUTOMATED MODERATION:
────────────────────

Video uploaded:
       │
       ▼
1. VISUAL ANALYSIS
   
   - Nudity detector (CNN)
   - Violence detector
   - Graphic content detector
   - Brand/logo detection (copyright)
       │
       ▼
2. AUDIO ANALYSIS
   
   - Audio fingerprinting (music copyright)
   - Speech-to-text → Hate speech detection
   - Sound classification (gunshots, etc.)
       │
       ▼
3. TEXT ANALYSIS
   
   - Caption text → Toxicity classification
   - Hashtags → Banned terms check
   - OCR text in video → Policy violation
       │
       ▼
4. DECISION
   
   Confidence score for each category:
   
   If score > 0.95: AUTO-REJECT (clear violation)
   If score > 0.60: QUEUE FOR HUMAN REVIEW
   If score < 0.60: APPROVE (monitor for user reports)


HUMAN REVIEW QUEUE:
──────────────────
- 10,000+ human moderators (contract workers)
- 24/7 coverage across time zones
- Specialized teams: Violence, Nudity, Misinformation
- Appeal process for creators


REACTIVE MODERATION:
───────────────────
User reports → Queue for review
Multiple reports → Priority boost
Viral + reports → Urgent review (within minutes)
```

---

## 11.8 Complete Technology Stack

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              REELS/TIKTOK TECH STACK                                                │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

│ Component              │ Technology                    │ Why                              │
├────────────────────────┼───────────────────────────────┼──────────────────────────────────┤
│ Video Storage          │ S3 / Google Cloud Storage     │ Cheap, durable, scalable         │
│ Video Transcoding      │ FFmpeg, AWS MediaConvert      │ Multiple resolutions, HLS        │
│ CDN                    │ Akamai, CloudFront, Fastly    │ Low latency global delivery      │
│                        │                               │                                  │
│ API Servers            │ Go, Rust, Java                │ High performance                 │
│ Real-time              │ WebSocket, gRPC               │ Live interactions                │
│                        │                               │                                  │
│ Message Queue          │ Kafka                         │ Event streaming, durability      │
│ Stream Processing      │ Apache Flink, Kafka Streams   │ Real-time analytics              │
│ Batch Processing       │ Apache Spark                  │ Daily ML jobs, aggregations      │
│                        │                               │                                  │
│ Feature Store          │ Feast, Redis, Cassandra       │ ML feature serving               │
│ ML Training            │ TensorFlow, PyTorch, Horovod  │ Model training (GPU cluster)     │
│ ML Serving             │ TensorFlow Serving, Triton    │ Real-time inference              │
│ Vector Search          │ FAISS, Milvus, Pinecone       │ Nearest neighbor for embeddings  │
│                        │                               │                                  │
│ Metadata DB            │ Cassandra                     │ Video metadata, high write       │
│ User DB                │ MySQL                         │ User profiles, social graph      │
│ Cache                  │ Redis                         │ Counters, sessions, features     │
│ Search                 │ Elasticsearch                 │ Video search, hashtags           │
│                        │                               │                                  │
│ Orchestration          │ Kubernetes                    │ Container management             │
│ Workflow               │ Airflow, Dagster              │ ML pipeline orchestration        │
│ Monitoring             │ Prometheus, Grafana, Datadog  │ Metrics, alerts                  │
│ Logging                │ ELK Stack, Splunk             │ Log aggregation                  │
└────────────────────────┴───────────────────────────────┴──────────────────────────────────┘
```

---

## 11.9 Interview Talking Points for Reels/TikTok

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              KEY DESIGN DECISIONS                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

1. WHY WATCH TIME > LIKES?
   - Likes are low-effort, can be habitual
   - Watch time represents genuine interest
   - Harder to fake (costs real time)
   - Better signal for recommendation quality

2. WHY TWO-TOWER MODEL?
   - Video embeddings can be pre-computed (static)
   - User embeddings computed at request time (dynamic)
   - Fast lookup via approximate nearest neighbor
   - Scales to billions of videos

3. WHY THREE-STAGE RANKING?
   - Stage 1: Fast pruning (500M → 10K)
   - Stage 2: Accurate ranking (10K → 100)
   - Stage 3: Diversity & business rules (100 → 50)
   - Balance speed vs accuracy

4. WHY BATCH + REAL-TIME?
   - Batch (Spark): Heavy computation, can be delayed
   - Real-time (Flink): Fresh signals, low latency
   - Both feed into Feature Store

5. COLD START SOLUTION?
   - New user: Demographics + explore phase
   - New video: Initial boost + content-based features
   - Learn fast from first interactions

6. SCALE CHALLENGES?
   - 100B views/day → CDN crucial
   - 10M uploads/day → Async processing pipeline
   - 1B users → Pre-compute recommendations
   - Real-time → Feature Store for low latency
```

---
