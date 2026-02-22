# Netflix / Video Streaming — High Level Design

## 1. Problem Statement

Design a video streaming system like Netflix that supports:
- Millions of videos in the catalog
- 200M+ subscribers globally
- Multiple device types (TV, phone, tablet, web)
- Adaptive quality based on network conditions
- Personalized recommendations

---

## 2. Requirements

### Functional Requirements

| Feature | Description |
|---------|-------------|
| **Video Streaming** | Smooth playback with minimal buffering |
| **Adaptive Bitrate** | Quality adjusts based on network speed |
| **Search** | Find movies by title, actor, genre |
| **Recommendations** | Personalized content suggestions |
| **Resume Watching** | Continue from where you left off (any device) |
| **Profiles** | Multiple users per account |
| **Offline Downloads** | Watch without internet |

### Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| **Latency** | < 2 sec to start playing |
| **Availability** | 99.99% uptime |
| **Scale** | 200M+ users, petabytes of video |
| **Global** | Low latency worldwide |

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTS                                        │
│                    (Smart TV, Phone, Tablet, Web, Gaming Console)           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
           ┌─────────────┐  ┌─────────────────┐  ┌─────────────┐
           │    CDN      │  │      Zuul       │  │   AWS S3    │
           │(Open Connect)│  │  (API Gateway)  │  │  (Origin)   │
           └─────────────┘  └─────────────────┘  └─────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
     ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
     │  User Service   │   │  Recs Service   │   │  Video Service  │
     └─────────────────┘   └─────────────────┘   └─────────────────┘
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
     ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
     │   Cassandra     │   │     Kafka       │   │  Elasticsearch  │
     │ (User Data)     │   │   (Events)      │   │   (Search)      │
     └─────────────────┘   └─────────────────┘   └─────────────────┘
```

---

## 4. Video Streaming: Chunk-Based Delivery

### Why Chunks?

| Approach | Problem |
|----------|---------|
| Download entire file first | Wait 30 min before watching? ❌ |
| Stream in chunks ✅ | Start watching in 2-3 seconds! |

### How It Works

```
2-hour movie "Inception" (5GB total)
        │
        ▼
Split into 2000 chunks (each ~2MB, ~4 seconds of video)

Player:
1. Download first 5 chunks → Start playing immediately
2. Keep downloading ahead (buffer)
3. User watching chunk 10 → Already have chunks 11-20 ready
```

---

## 5. Adaptive Bitrate Streaming (ABR)

Same movie stored in **multiple qualities**:

| Quality | Bitrate | Resolution | File Size (2hr) |
|---------|---------|------------|-----------------|
| 4K Ultra | 25 Mbps | 3840×2160 | ~20 GB |
| 1080p HD | 8 Mbps | 1920×1080 | ~7 GB |
| 720p | 4 Mbps | 1280×720 | ~3.5 GB |
| 480p | 2 Mbps | 854×480 | ~1.8 GB |
| 360p | 1 Mbps | 640×360 | ~900 MB |

**Player monitors bandwidth:**
- Fast WiFi → Request 1080p chunks
- Network drops → Switch to 480p instantly
- Network recovers → Switch back to 1080p

---

## 6. CDN: Open Connect

Netflix's **custom CDN** places servers inside ISPs:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CONTENT DELIVERY TIERS                           │
└─────────────────────────────────────────────────────────────────────┘

Tier 1: Origin (AWS S3)
  └── Master copies of ALL content
  
Tier 2: Regional PoPs
  └── Netflix data centers in major regions
  
Tier 3: Open Connect Appliances (OCAs)
  └── Physical servers INSIDE ISPs (Jio, Airtel, Comcast)
  └── Most popular content cached here
```

**Result:** User in India streams from Jio's datacenter (10km away), not US servers!

---

## 7. Video Encoding Pipeline

When Netflix adds a new movie:

```
Input: Master file (100GB, 4K raw)
        │
        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    TRANSCODING FARM                                 │
│                 (1000s of servers in parallel)                      │
└─────────────────────────────────────────────────────────────────────┘
        │
        ▼
Output: 1200+ encoded files!

  5 resolutions × 4 codecs × 3 formats × 3 audio tracks = 180+ files
  + Each split into 4-second chunks = 1200+ total files
```

### Parallel Encoding

```
2-hour movie → Split into 120 segments
        │
        ├── Segment 1 → Server A → 5 min
        ├── Segment 2 → Server B → 5 min
        └── Segment 120 → Server Z → 5 min
        
All run in parallel! Total: ~10 min (not 10 hours!)
```

---

## 8. Recommendations

### Key Stat

> **80%** of what users watch comes from recommendations

### Architecture

```
Data Sources:
  • Watch history
  • Ratings
  • Browse behavior
  • Search queries
        │
        ▼
ML Models (Spark):
  • Collaborative Filtering ("Users like you watched X")
  • Content-Based ("You liked action movies")
  • Trending ("Popular in your region")
        │
        ▼
Personalized Homepage
```

### Recommendation Storage

```sql
CREATE TABLE user_recommendations (
    user_id         UUID,
    row_type        TEXT,         -- 'top_picks', 'because_you_watched'
    recommendations LIST<recommendation>,
    PRIMARY KEY (user_id, row_type)
);
```

---

## 9. Apache Spark for ML

### Batch Processing

```python
# Nightly recommendation job

# 1. Load viewing history (petabytes)
viewing_history = spark.read.parquet("s3://netflix/viewing/")

# 2. Train collaborative filtering
model = ALS(userCol="user_id", itemCol="movie_id").fit(data)

# 3. Generate recommendations for ALL users
recommendations = model.recommendForAllUsers(50)

# 4. Save to Cassandra
recommendations.write.format("cassandra").save()
```

### Streaming (Real-time)

```python
# Real-time updates when user finishes a movie
events = spark.readStream.format("kafka").load()
```

---

## 10. Zuul API Gateway

All requests go through Zuul:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ZUUL FILTER PIPELINE                             │
└─────────────────────────────────────────────────────────────────────┘

Request → PRE Filters (Auth, Rate Limit)
            → ROUTING Filter (Forward to service)
            → POST Filters (Headers, Transform)
            → Response
```

### Key Features

| Feature | Description |
|---------|-------------|
| **Dynamic Routing** | Route based on path to different services |
| **Hot Filters** | Deploy new filters without restart |
| **Service Discovery** | Integrates with Eureka |

---

## 11. Hystrix Circuit Breaker

Prevents cascading failures:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CIRCUIT BREAKER STATES                           │
└─────────────────────────────────────────────────────────────────────┘

CLOSED (Normal) → Too many failures → OPEN (Fail fast)
                                          │
                                    Wait 5 seconds
                                          │
                                          ▼
                                    HALF-OPEN (Test)
                                          │
                          Success → CLOSED    Failure → OPEN
```

### With Hystrix

```java
@HystrixCommand(fallbackMethod = "getDefaultRecommendations")
public List<Movie> getRecommendations(String userId) {
    return recsService.call(userId);
}

// Fallback when circuit is open
public List<Movie> getDefaultRecommendations(String userId) {
    return cache.get("default_recommendations");
}
```

---

## 12. Watch Position Sync

Resume watching across devices:

```sql
-- Cassandra table
CREATE TABLE watch_position (
    user_id       UUID,
    video_id      UUID,
    position_sec  INT,
    updated_at    TIMESTAMP,
    PRIMARY KEY (user_id, video_id)
);
```

**Flow:**
- Player updates local position every second
- Sync to server every 10-30 seconds
- New device → Fetch position → Auto-resume

---

## 13. DRM (Digital Rights Management)

### Layer 1: Encryption

```
Video chunks → Encrypted with AES-128
To play → Request license key → Decrypt in protected memory

DRM Technologies:
  • Widevine (Android, Chrome)
  • FairPlay (Apple)
  • PlayReady (Windows, Xbox)
```

### Layer 2: Forensic Watermarking

- Invisible user ID embedded in video frames
- If leaked → Trace back to who recorded it

---

## 14. Search

### Elasticsearch + ML

```
Query: "funny movies with rock"
        │
        ▼
Elasticsearch:
  • Fuzzy: "rock" → "The Rock" (Dwayne Johnson)
  • Synonyms: "funny" → "comedy"
        │
        ▼
ML Ranking:
  • Personalize based on Bob's history
        │
        ▼
Results: Jumanji, Central Intelligence, Moana
```

---

## 15. Handling Viral Content

Before release:
1. Encode all formats
2. Push to ALL CDN locations
3. Pre-warm caches
4. Scale backend services

During release:
- 95% requests served from CDN cache
- Backend only handles auth, licenses

---

## 16. Service Mesh & Modern Resilience

### Evolution

| Era | Approach |
|-----|----------|
| 2012 | Hystrix (per-service library) |
| 2020s | Service Mesh (infrastructure-level) |

### Service Mesh (Istio/Envoy)

```
┌───────────┐      ┌───────────┐
│ Service A │      │ Service B │
└─────┬─────┘      └─────┬─────┘
      │                  │
┌─────▼─────┐      ┌─────▼─────┐
│  Envoy    │─────▶│  Envoy    │
│  Sidecar  │      │  Sidecar  │
│[Circuit   │      │[Circuit   │
│ Breaker]  │      │ Breaker]  │
└───────────┘      └───────────┘

Circuit breaker in infrastructure, not code!
```

---

## 17. Database Strategy

| Data Type | Database | Reason |
|-----------|----------|--------|
| **User profiles** | Cassandra | Partitioned by user_id |
| **Recommendations** | Cassandra + Redis | Fast lookup |
| **Video metadata** | MySQL | Relational, catalog |
| **Search** | Elasticsearch | Full-text, fuzzy |
| **Events** | Kafka → S3 | Streaming analytics |
| **Videos** | S3 + CDN | Large files |

---

## 18. Interview Talking Points

### "How does Netflix handle 200M users?"
> "CDN (Open Connect) caches content at ISP level. 95%+ of traffic served from cache, not origin. Backend only handles auth, recommendations, and license validation."

### "How does adaptive bitrate work?"
> "Each video encoded in multiple resolutions. Player monitors bandwidth, switches quality mid-stream. Uses HLS/DASH protocols with manifest files listing all quality variants."

### "How do recommendations scale?"
> "Spark batch jobs run nightly to compute collaborative filtering. Results pre-computed and stored in Cassandra per user. Real-time signals from Kafka boost recent activity."

### "How do they prevent downtime?"
> "Circuit breakers (Hystrix/Resilience4j) prevent cascading failures. Zuul gateway handles routing/auth. Chaos Monkey randomly kills services to test resilience."

---

## 19. Quick Reference Card

```
┌────────────────────────────────────────────────────────────────────────┐
│                    NETFLIX CHEAT SHEET                                 │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  VIDEO DELIVERY                                                        │
│  • Chunk-based streaming (4-sec chunks)                               │
│  • Adaptive bitrate (5 quality levels)                                │
│  • CDN: Open Connect (servers inside ISPs)                            │
│                                                                        │
│  ENCODING                                                              │
│  • Parallel transcoding (split into segments)                         │
│  • Multiple codecs: H.264, H.265, VP9, AV1                           │
│  • Multiple formats: HLS, DASH, Smooth                                │
│                                                                        │
│  RECOMMENDATIONS                                                       │
│  • Spark batch (nightly collaborative filtering)                      │
│  • Kafka streaming (real-time signals)                                │
│  • Pre-computed, stored in Cassandra/Redis                            │
│                                                                        │
│  RESILIENCE                                                            │
│  • Zuul (API Gateway)                                                 │
│  • Hystrix/Resilience4j (Circuit Breaker)                            │
│  • Chaos Monkey (failure testing)                                     │
│                                                                        │
│  DRM                                                                   │
│  • AES-128 encryption                                                 │
│  • Widevine/FairPlay/PlayReady                                       │
│  • Forensic watermarking                                              │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 20. Component Summary

| Component | Technology | Purpose |
|-----------|------------|---------|
| **API Gateway** | Zuul | Routing, auth, rate limiting |
| **Service Discovery** | Eureka | Find service instances |
| **Circuit Breaker** | Hystrix/Resilience4j | Prevent cascading failures |
| **Video Storage** | S3 | Origin for all content |
| **CDN** | Open Connect | Edge caching at ISPs |
| **User Data** | Cassandra | Watch history, profiles |
| **Catalog** | MySQL | Movie metadata |
| **Search** | Elasticsearch | Full-text search |
| **Recommendations** | Spark + Cassandra | ML + pre-computed results |
| **Events** | Kafka | Real-time streaming |
| **Encoding** | EC2 Farm | Parallel transcoding |
