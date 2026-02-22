# Netflix / Video Streaming — Complete Deep Dive

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
| 1 | **Video Playback** | P0 | Stream video content smoothly |
| 2 | **Adaptive Bitrate** | P0 | Adjust quality based on network |
| 3 | **Video Catalog** | P0 | Browse movies and shows |
| 4 | **Search** | P0 | Find content by title, actor, genre |
| 5 | **User Profiles** | P0 | Multiple profiles per account |
| 6 | **Recommendations** | P1 | Personalized content suggestions |
| 7 | **Resume Watching** | P1 | Continue from where you left off |
| 8 | **Watchlist** | P1 | Save videos to watch later |
| 9 | **Offline Downloads** | P1 | Watch without internet |
| 10 | **Multiple Devices** | P1 | Watch on TV, phone, tablet |
| 11 | **Subtitles/Audio** | P1 | Multiple languages, accessibility |
| 12 | **Skip Intro** | P2 | Jump past opening credits |
| 13 | **Parental Controls** | P2 | Content restrictions per profile |
| 14 | **Ratings/Reviews** | P2 | User feedback on content |

---

# 2. NON-FUNCTIONAL REQUIREMENTS

## Latency

| Operation | Target | Rationale |
|-----------|--------|-----------|
| Video start | < 2 sec | First frame visible |
| Quality switch | < 500ms | Seamless transition |
| Search results | < 200ms | Instant feedback |
| Homepage load | < 1 sec | Fast browsing |
| Resume position fetch | < 100ms | Instant resume |

## Throughput

| Metric | Target |
|--------|--------|
| Concurrent streams | 50 million |
| Peak bandwidth | 50+ Tbps |
| Search QPS | 100,000 |
| API requests/sec | 5 million |

## Availability

| Component | Target | Strategy |
|-----------|--------|----------|
| Streaming | 99.99% | CDN + multi-region |
| API | 99.95% | Circuit breakers |
| Catalog | 99.9% | Read replicas |

## Consistency

| Data Type | Consistency Level |
|-----------|-------------------|
| Video metadata | Eventually consistent (minutes OK) |
| Watch position | Eventually consistent (seconds) |
| User preferences | Eventually consistent |
| Billing | Strongly consistent |

---

# 3. CAPACITY PLANNING

## Step-by-Step Calculation Guide

### Step 1: Define User Base

```
Total Subscribers:         200 million
Daily Active Users (DAU):  100 million (50%)
Concurrent Streams:        10 million (10% of DAU at peak)
```

**Formula:**
```
DAU = Subscribers × 0.5
Concurrent = DAU × 0.1
```

---

### Step 2: Video Catalog Size

```
Total Videos:              15,000 titles
Average Video Length:      1.5 hours
Encoded Versions:          ~1,200 files per video
  (5 resolutions × 4 codecs × 3 audio tracks × ~20 chunks/min)

Total Files:               15,000 × 1,200 = 18 million files
```

---

### Step 3: Storage Calculation

**Per Video:**
```
4K version:    ~20 GB (2 hours)
1080p:         ~7 GB
720p:          ~3.5 GB
480p:          ~1.8 GB
360p:          ~0.9 GB
Total/video:   ~35 GB (all resolutions)
```

**Total Storage:**
```
15,000 videos × 35 GB = 525 TB
With redundancy (3x): 1.5 PB
Across CDN locations: ~10 PB (popular content replicated globally)
```

**Formula:**
```
Storage = Num_videos × Avg_size_all_resolutions × Replication × CDN_factor
```

---

### Step 4: Bandwidth Calculation

**Per Stream:**
```
Average bitrate:    5 Mbps (mix of resolutions)
Peak bitrate (4K):  25 Mbps
```

**Total Bandwidth:**
```
Concurrent streams:     10 million
Average bandwidth:      10M × 5 Mbps = 50 Tbps
Peak bandwidth:         50 Tbps

(This is why CDN is critical - origin can't handle this!)
```

**CDN Offload:**
```
Cache hit rate:         95%
Origin bandwidth:       50 Tbps × 5% = 2.5 Tbps
CDN handles:            47.5 Tbps (distributed globally)
```

**Formula:**
```
Total_bandwidth = Concurrent_streams × Avg_bitrate
Origin_bandwidth = Total_bandwidth × (1 - Cache_hit_rate)
```

---

### Step 5: API Server Estimation

**Requests:**
```
Homepage loads/day:     100 million (each user once)
Actions per session:    20 (browse, search, play, pause, etc.)
Total API calls/day:    100M × 20 = 2 billion
QPS average:            2B / 86400 = 23,000 QPS
QPS peak:               23,000 × 5 = 115,000 QPS
```

**Servers:**
```
QPS per server:         5,000 (with proper async I/O)
Servers needed:         115,000 / 5,000 = 23 servers
With redundancy (3x):   69 servers
```

---

### Step 6: Encoding Farm

**New Content:**
```
New videos/day:         10 titles
Encoding time/video:    4 hours (with parallelization)
Parallel segments:      120 (split 2hr video into 1-min segments)
```

**Servers:**
```
Encoding servers:       500 (burst capacity for parallel encoding)
GPU-accelerated:        Yes (NVENC or similar)
```

---

### Step 7: Database Sizing

**Cassandra (User Data):**
```
Users:                  200 million
Data per user:          10 KB (watch history, preferences)
Total:                  200M × 10 KB = 2 TB

Recommendations:        200M × 50 KB = 10 TB
Watch positions:        200M × 1 KB = 200 GB

Total:                  ~15 TB
With replication (3x):  45 TB
Nodes (2 TB each):      25 nodes
```

**MySQL (Catalog):**
```
Videos:                 15,000 rows
Metadata per video:     50 KB (titles, descriptions, cast)
Total:                  750 MB

Episodes (TV shows):    500,000 rows × 10 KB = 5 GB
```

---

### Quick Reference: Capacity Cheat Sheet

```
┌────────────────────────────────────────────────────────────────────────┐
│                    NETFLIX CAPACITY CHEAT SHEET                        │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  USERS                                                                 │
│  • Subscribers: 200M    DAU: 100M    Concurrent: 10M                  │
│                                                                        │
│  STREAMING                                                             │
│  • Peak bandwidth: 50 Tbps    CDN handles: 95%                        │
│  • Average bitrate: 5 Mbps                                            │
│                                                                        │
│  STORAGE                                                               │
│  • Videos: 15,000 titles × 35 GB = 525 TB                             │
│  • CDN distributed: ~10 PB globally                                   │
│                                                                        │
│  SERVERS                                                               │
│  • API: 70 servers                                                    │
│  • Encoding: 500 GPU servers (burst)                                  │
│  • Cassandra: 25 nodes                                                │
│                                                                        │
│  API                                                                   │
│  • 2B calls/day    115K QPS peak                                      │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

# 4. DETAILED HLD DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    NETFLIX - DETAILED ARCHITECTURE                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                           CLIENTS
                    ┌─────────────────────────────────────────────────────────┐
                    │   Smart TV       Phone        Tablet        Web        │
                    │      │             │            │            │          │
                    └──────┼─────────────┼────────────┼────────────┼──────────┘
                           │             │            │            │
                           └─────────────┼────────────┴────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
          ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
          │    CDN TIER     │  │   API GATEWAY   │  │   DNS/GSLB      │
          │  (Open Connect) │  │     (Zuul)      │  │                 │
          │                 │  │                 │  │  Route to       │
          │  • 10,000+ OCAs │  │  • 70 servers   │  │  nearest PoP    │
          │  • At ISP level │  │  • Auth/JWT     │  │                 │
          │  • 95% cache hit│  │  • Rate limit   │  │                 │
          │  • 47.5 Tbps    │  │  • Routing      │  │                 │
          └────────┬────────┘  └────────┬────────┘  └─────────────────┘
                   │                    │
    Video streams  │                    │  API calls
                   │                    │
                   │                    ▼
                   │     ┌─────────────────────────────────────────────────────────────────────────┐
                   │     │                        MICROSERVICES LAYER                              │
                   │     ├─────────────────┬─────────────────┬─────────────────┬───────────────────┤
                   │     │  VIDEO SERVICE  │  USER SERVICE   │  RECS SERVICE   │  SEARCH SERVICE  │
                   │     │  [30 servers]   │  [20 servers]   │  [40 servers]   │  [15 servers]    │
                   │     │                 │                 │                 │                   │
                   │     │  • Manifest     │  • Profiles     │  • ML models    │  • Elasticsearch │
                   │     │  • License      │  • Watch pos    │  • Personalize  │  • Fuzzy match   │
                   │     │  • DRM keys     │  • Preferences  │  • Batch Spark  │  • Ranking       │
                   │     │                 │                 │                 │                   │
                   │     │  Go             │  Java           │  Python/Scala   │  Java            │
                   │     └────────┬────────┴────────┬────────┴────────┬────────┴─────────┬─────────┘
                   │              │                 │                 │                  │
                   │              ▼                 ▼                 ▼                  ▼
                   │     ┌─────────────────────────────────────────────────────────────────────────┐
                   │     │                        DATA LAYER                                       │
                   │     ├─────────────────────────────────────────────────────────────────────────┤
                   │     │                                                                         │
                   │     │   CASSANDRA                MYSQL                 ELASTICSEARCH         │
                   │     │   (User Data)              (Catalog)             (Search Index)        │
                   │     │                                                                         │
                   │     │   • 25 nodes               • 1 primary           • 10 nodes            │
                   │     │   • 3 replicas             • 5 read replicas     • 3 shards            │
                   │     │   • Partition: user_id     • per region          • 1 replica each      │
                   │     │                                                                         │
                   │     │   Tables:                  Tables:               Indices:              │
                   │     │   - user_recommendations   - videos              - videos              │
                   │     │   - watch_positions        - episodes            - actors              │
                   │     │   - viewing_history        - cast                - genres              │
                   │     │                            - genres                                     │
                   │     │                                                                         │
                   │     └─────────────────────────────────────────────────────────────────────────┘
                   │              │
                   │              ▼
                   │     ┌─────────────────────────────────────────────────────────────────────────┐
                   │     │                        STREAMING & ANALYTICS                           │
                   │     ├─────────────────────────────────────────────────────────────────────────┤
                   │     │                                                                         │
                   │     │   KAFKA                    SPARK CLUSTER          REDIS                │
                   │     │   (Events)                 (ML/Batch)             (Cache)              │
                   │     │                                                                         │
                   │     │   • 30 brokers             • 200 nodes            • 15 nodes           │
                   │     │   • Topics:                • Nightly batch        • 5 masters          │
                   │     │     - viewing_events       • Recs training        • 10 replicas        │
                   │     │     - playback_quality     • ALS algorithm        • 100 GB memory      │
                   │     │     - user_actions                                                     │
                   │     │   • 500 partitions         Storage:               Data:                │
                   │     │   • 7 day retention        • S3 (data lake)       • Hot recs           │
                   │     │                            • 50 PB total          • Session data       │
                   │     │                                                   • Rate limits        │
                   │     └─────────────────────────────────────────────────────────────────────────┘
                   │
                   ▼
          ┌─────────────────────────────────────────────────────────────────────────────────────────┐
          │                        VIDEO STORAGE & DELIVERY                                        │
          ├─────────────────────────────────────────────────────────────────────────────────────────┤
          │                                                                                         │
          │   S3 ORIGIN                          OPEN CONNECT CDN                                  │
          │   (Master Storage)                   (Edge Delivery)                                   │
          │                                                                                         │
          │   • 3 regions                        Tier 1: Netflix PoPs                              │
          │   • 1.5 PB total                       • 50 locations                                  │
          │   • All resolutions                    • Full catalog                                  │
          │   • All codecs                                                                         │
          │                                      Tier 2: IXP (Internet Exchange)                  │
          │   Buckets:                             • 100 locations                                 │
          │   - videos/                            • Popular content                               │
          │   - thumbnails/                                                                        │
          │   - subtitles/                       Tier 3: ISP (Open Connect Appliances)            │
          │   - audio/                             • 10,000+ locations                             │
          │                                        • Top 20% content                               │
          │                                        • Inside Jio, Comcast, etc.                     │
          │                                                                                         │
          └─────────────────────────────────────────────────────────────────────────────────────────┘
                   │
                   │
          ┌────────▼────────────────────────────────────────────────────────────────────────────────┐
          │                        ENCODING PIPELINE                                               │
          ├─────────────────────────────────────────────────────────────────────────────────────────┤
          │                                                                                         │
          │   INGEST                 TRANSCODING FARM              OUTPUT                          │
          │                                                                                         │
          │   • Upload portal        • 500 GPU servers             • HLS manifests                 │
          │   • Master files         • Parallel segments           • DASH manifests                │
          │   • 50-100 GB each       • 5 resolutions               • 18M files/video              │
          │                          • 4 codecs each               • Push to S3                    │
          │                          • H.264, H.265, VP9, AV1      • Replicate to CDN              │
          │                                                                                         │
          │   Time: New video → 4 hours → Ready to stream                                          │
          │                                                                                         │
          └─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 5. REQUEST FLOWS

## Flow 1: Video Playback (Happy Path)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              VIDEO PLAYBACK FLOW - HAPPY PATH                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User clicks "Play" on "Stranger Things S1E1"

1. CLIENT → API GATEWAY (Zuul)
   GET /api/video/play?id=stranger-things-s1e1
   Headers: Authorization: Bearer <JWT>
           │
           ▼
2. ZUUL validates request
   • Check JWT token
   • Rate limit check
   • Route to Video Service
           │
           ▼
3. VIDEO SERVICE handles request
   • Verify subscription active
   • Check concurrent stream limit (4 max)
   • Get user's preferred quality settings
   • Generate manifest URL with auth token
           │
           ▼
4. Return manifest URL to client
   {
     "manifest_url": "https://cdn.netflix.com/video/st-s1e1/manifest.m3u8?token=xyz",
     "license_url": "https://api.netflix.com/drm/license",
     "resume_position": 1234  // seconds
   }
           │
           ▼
5. CLIENT requests manifest from CDN
   GET https://cdn.netflix.com/video/st-s1e1/manifest.m3u8
   
   Returns:
   #EXTM3U
   #EXT-X-STREAM-INF:BANDWIDTH=25000000,RESOLUTION=3840x2160
   4k/playlist.m3u8
   #EXT-X-STREAM-INF:BANDWIDTH=8000000,RESOLUTION=1920x1080
   1080p/playlist.m3u8
   ...
           │
           ▼
6. CLIENT selects quality based on bandwidth
   • Measures download speed
   • Picks 1080p (8 Mbps available)
           │
           ▼
7. CLIENT requests DRM license
   POST /drm/license
   Body: { "video_id": "st-s1e1", "device_id": "abc" }
   
   Response: { "license_key": "encrypted_key" }
           │
           ▼
8. CLIENT downloads video chunks
   GET https://cdn.netflix.com/video/st-s1e1/1080p/chunk_0001.ts
   GET https://cdn.netflix.com/video/st-s1e1/1080p/chunk_0002.ts
   ...
           │
           ▼
9. CLIENT decrypts and plays
   • Decrypt chunk with license key
   • Decode video (H.264/H.265)
   • Render to screen
           │
           ▼
10. CLIENT buffers ahead
    • Download chunks 3-10 while playing chunk 1
    • Maintain 30 second buffer
```

### Edge Case: Quality Switch (Adaptive Bitrate)

```
While playing at 1080p, network degrades:

1. Client detects:
   • Chunk download taking longer
   • Buffer level dropping

2. Client switches:
   • Request next chunk at 720p
   • GET .../720p/chunk_0042.ts
   • Seamless playback continues

3. Network recovers:
   • Buffer fills up
   • Switch back to 1080p
   • GET .../1080p/chunk_0050.ts
```

### Edge Case: Cold Start (App Just Opened)

```
1. App needs to determine best initial quality
2. Start with conservative quality (480p)
3. Quickly upgrade as bandwidth is measured
4. Usually at optimal quality by chunk 3-4 (12-16 seconds)
```

### Edge Case: CDN Cache Miss

```
User requests rare old movie not in edge cache:

1. OCA (ISP level) → Cache miss
2. Request goes to regional PoP → Cache miss  
3. Request goes to Origin (S3)
4. Stream from origin (higher latency)
5. Simultaneously cache at each tier
6. Next user gets cache hit
```

---

## Flow 2: Search

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SEARCH FLOW                                                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User types "funny movies the rock"

1. CLIENT sends search request (debounced)
   GET /api/search?q=funny+movies+the+rock
           │
           ▼
2. SEARCH SERVICE receives request
   • Parse query
   • Expand synonyms: "funny" → ["comedy", "humorous"]
           │
           ▼
3. Query ELASTICSEARCH
   {
     "query": {
       "bool": {
         "should": [
           { "match": { "title": "the rock" }},
           { "match": { "actors": "Dwayne Johnson" }},  // alias
           { "match": { "genres": "comedy" }}
         ]
       }
     }
   }
           │
           ▼
4. ELASTICSEARCH returns matches
   • Jumanji (score: 0.95)
   • Central Intelligence (score: 0.89)
   • Moana (score: 0.72)
           │
           ▼
5. PERSONALIZE results (ML ranking)
   • User likes action → Boost action-comedies
   • User watched Jumanji before → Lower rank
           │
           ▼
6. Return to client
   {
     "results": [
       { "id": "central-intel", "title": "Central Intelligence", ... },
       { "id": "jumanji", "title": "Jumanji", ... }
     ]
   }
```

### Edge Case: Typo

```
User types "strnger things"

Elasticsearch fuzzy matching:
• fuzziness: AUTO (allows 1-2 char errors)
• "strnger" matches "stranger"
• Returns Stranger Things
```

---

## Flow 3: Homepage Recommendations

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              HOMEPAGE RECOMMENDATIONS FLOW                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User opens Netflix app

1. CLIENT requests homepage
   GET /api/homepage
   Headers: X-Profile-Id: profile_123
           │
           ▼
2. API calls RECOMMENDATIONS SERVICE
           │
           ├── Check Redis cache: GET recs:profile_123
           │   If hit → Return cached recs (fast path)
           │
           └── If miss → Query Cassandra:
               SELECT * FROM user_recommendations 
               WHERE user_id = 'profile_123'
           │
           ▼
3. Recommendations returned:
   {
     "rows": [
       { "type": "continue_watching", "items": [...] },
       { "type": "top_picks", "items": [...] },
       { "type": "because_you_watched_X", "items": [...] },
       { "type": "trending", "items": [...] }
     ]
   }
           │
           ▼
4. CLIENT renders personalized homepage
   • "Continue Watching" row at top
   • Personalized rows with thumbnails
```

### Background: How Recommendations Are Generated

```
NIGHTLY BATCH (Apache Spark):

1. Load viewing history (all users, 24 hours)
2. Run collaborative filtering (ALS algorithm)
3. Generate top 50 recommendations per user
4. Store in Cassandra (partition by user_id)

REAL-TIME UPDATES:

1. User finishes watching Movie X
2. Kafka event: { "user": 123, "event": "complete", "video": "X" }
3. Spark streaming picks up event
4. Boost similar content in recommendations
5. Update Redis cache
```

---

## Flow 4: Resume Watching

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              RESUME WATCHING FLOW                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

SAVING POSITION (while watching):

1. Player reports position every 10 seconds:
   POST /api/watchpos
   { "video_id": "st-s1e1", "position": 1234, "duration": 3456 }
           │
           ▼
2. USER SERVICE saves to Cassandra:
   INSERT INTO watch_positions (user_id, video_id, position, updated_at)
   VALUES ('user_123', 'st-s1e1', 1234, now())
           │
           ▼
3. Also update Redis for fast access:
   SET watchpos:user_123:st-s1e1 1234 EX 86400


RESUMING (new device):

1. User opens app on TV (was watching on phone)
           │
           ▼
2. CLIENT requests /api/homepage
   • "Continue Watching" row shows st-s1e1 at 20:34
           │
           ▼
3. User clicks play
   • Server returns: resume_position: 1234
           │
           ▼
4. Player seeks to 1234 seconds
   • Requests chunk for that timestamp
   • GET /1080p/chunk_0309.ts (around 20:34)
```

---

## Flow 5: DRM License

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              DRM LICENSE FLOW                                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Before playback:

1. CLIENT requests license
   POST /api/drm/license
   {
     "video_id": "st-s1e1",
     "device_id": "device_abc",
     "drm_type": "widevine",  // or "fairplay", "playready"
     "security_level": "L1"
   }
           │
           ▼
2. DRM SERVICE validates:
   • User has active subscription?
   • Device registered and trusted?
   • Concurrent stream limit not exceeded?
   • Content available in user's region?
           │
           ▼
3. Generate encrypted license
   • Create content key for this session
   • Encrypt with device's public key
   • Set expiration (24 hours typical)
           │
           ▼
4. Return license
   {
     "license": "base64_encrypted_license",
     "expiration": "2024-02-05T00:00:00Z"
   }
           │
           ▼
5. CLIENT stores and uses for decryption
   • Decrypt chunks in protected memory
   • Video never exposed unencrypted
```

### Edge Case: License Expired Mid-Stream

```
1. User watching for 25 hours straight
2. License expires
3. Player requests new license (transparent to user)
4. Continue playback without interruption
```

---

## Error Handling Summary

| Scenario | Handling |
|----------|----------|
| Network drops | Buffer + quality downgrade + retry |
| CDN failure | Failover to alternate CDN PoP |
| DRM failure | Retry with different security level |
| Stream limit reached | Error: "Too many devices streaming" |
| Region restricted | Error: "Not available in your country" |
| Subscription expired | Redirect to billing page |
| Video not found | 404 with suggestions |
| Slow network | Start with lower quality, upgrade later |

---

## Cold Start Optimizations

| Scenario | Optimization |
|----------|--------------|
| First play ever | Pre-fetch manifest on hover |
| New release launch | Pre-warm CDN before release |
| App startup | Pre-load homepage recs in background |
| Search | Typeahead suggestions start after 2 chars |
| Thumbnail loading | Progressive JPEG, blur-up effect |
