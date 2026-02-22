# Uber — Complete Deep Dive

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
| 1 | **Driver Location Tracking** | P0 | Drivers update GPS every 5 sec |
| 2 | **Find Nearby Drivers** | P0 | Show available drivers on rider's map |
| 3 | **Request Ride** | P0 | Rider enters pickup & destination |
| 4 | **Driver Matching** | P0 | Find best driver based on ETA |
| 5 | **Ride State Management** | P0 | Track ride from request → complete |
| 6 | **Real-time Tracking** | P0 | Both parties see live location during trip |
| 7 | **Fare Calculation** | P0 | Distance + time + surge pricing |
| 8 | **Surge Pricing** | P1 | Dynamic pricing based on demand/supply |
| 9 | **Payments** | P0 | Charge rider, pay driver |
| 10 | **Ratings** | P1 | Both parties rate each other |
| 11 | **Push Notifications** | P1 | Ride updates, promotions |
| 12 | **Ride History** | P2 | Past rides for both users |

---

# 2. NON-FUNCTIONAL REQUIREMENTS

## Latency

| Operation | Target | Rationale |
|-----------|--------|-----------|
| Find nearby drivers | < 200ms | Real-time map update |
| Driver matching | < 5 sec | Rider waiting for confirmation |
| Location update processing | < 100ms | Keep map current |
| ETA calculation | < 500ms | Part of matching flow |

## Throughput

| Metric | Target |
|--------|--------|
| Active drivers | 5 million |
| Location updates/sec | 1 million (5M drivers ÷ 5 sec) |
| Concurrent rides | 500,000 |
| Ride requests/sec | 10,000 |

## Availability

| Component | Target | Strategy |
|-----------|--------|----------|
| Ride matching | 99.99% | Multi-region, no SPOF |
| Location service | 99.9% | Redis cluster, fallback |
| Payments | 99.99% | Critical, full redundancy |

## Consistency

| Data Type | Consistency Level |
|-----------|-------------------|
| Driver location | Eventual (seconds OK) |
| Ride state | Strong (critical) |
| Payments | Strong (financial) |
| Ratings | Eventual |

---

# 3. CAPACITY PLANNING

## Step-by-Step Calculation Guide

### Step 1: Define Scale

```
Active drivers:              5 million
Location update frequency:   Every 5 seconds
Concurrent rides:            500,000
Ride requests/day:           20 million
```

---

### Step 2: Location Updates (Write Heavy)

```
Drivers:                     5 million
Updates per driver:          1 every 5 sec
Total updates/sec:           5M ÷ 5 = 1,000,000 writes/sec

This is the HEAVIEST load in the system!
```

---

### Step 3: Storage Calculation

**Per Driver Location (Redis):**
```
Driver ID:                   16 bytes
Latitude:                    8 bytes
Longitude:                   8 bytes
Cell ID:                     8 bytes
Status:                      4 bytes
Timestamp:                   8 bytes
─────────────────────────────────────
Total:                       ~50 bytes per driver

5 million drivers:           5M × 50 = 250 MB
With overhead/indexes:       ~1 GB
```

**Active Rides (MySQL):**
```
Per ride:                    ~500 bytes
Concurrent active rides:     500,000
Storage for active:          250 MB (tiny!)
Sharded by city             
```

**Trip History (Cassandra):**
```
Per completed trip:          ~500 bytes
Trips/day:                   20 million
Storage/day:                 20M × 500 = 10 GB/day
Storage/year:                3.6 TB/year
With replication (3×):       ~11 TB/year

Why Cassandra?
  - Write-once, read-many (no updates)
  - Partition by rider_id for fast "my trips"
  - Horizontal scaling for billions of trips
```

---

### Step 4: Server Estimation

**Location Service (Redis):**
```
Operations/sec:              1 million writes + 500K reads
Per Redis node:              100,000 ops/sec
Nodes needed:                15 master nodes
With replicas (3×):          45 Redis nodes total

Sharded by geographic region for locality
```

**Matching Service:**
```
Ride requests/sec:           ~250 (peak: 750)
Processing time:             ~100ms per request
Servers needed (peak):       75 / 10 = 8 servers
With redundancy:             20 servers
```

**WebSocket Servers (Real-time):**
```
Concurrent connections:      1 million (riders + drivers in active rides)
Per server:                  50,000 connections
Servers needed:              20 servers
With redundancy:             40 WebSocket servers
```

---

### Quick Reference: Capacity Cheat Sheet

```
┌────────────────────────────────────────────────────────────────────────┐
│                    UBER CAPACITY CHEAT SHEET                           │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  SCALE                                                                 │
│  • Drivers: 5M    Rides/day: 20M    Concurrent rides: 500K            │
│                                                                        │
│  LOCATION UPDATES                                                      │
│  • 1M writes/sec    50 bytes/driver    1 GB total in Redis            │
│                                                                        │
│  SERVERS                                                               │
│  • Redis: 45 nodes (15 masters + 30 replicas)                         │
│  • Matching: 20 servers                                                │
│  • WebSocket: 40 servers                                               │
│  • API Gateway: 30 servers                                             │
│                                                                        │
│  DATABASE                                                              │
│  • MySQL: Active rides (sharded by city)                              │
│  • Cassandra: Trip history (11 TB/year)                               │
│  • Kafka: Location ingestion (1M events/sec)                          │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

# 4. DETAILED HLD DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    UBER - DETAILED ARCHITECTURE                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                           CLIENTS
                    ┌─────────────────────────────────────────────────────────┐
                    │      Rider App              Driver App                  │
                    │         │                       │                       │
                    └─────────┼───────────────────────┼───────────────────────┘
                              │                       │
                              │                       │ GPS every 5 sec
                              ▼                       ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │                    LOAD BALANCER                        │
                    │                   (AWS ALB / Nginx)                     │
                    │                                                         │
                    │   - Health checks        - SSL termination              │
                    │   - Geographic routing   - Rate limiting                │
                    └─────────────────────────────────────────────────────────┘
                              │                       │
          ┌───────────────────┼───────────────────────┼───────────────────────┐
          │                   │                       │                       │
          ▼                   ▼                       ▼                       ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│  API GATEWAY     │ │  WEBSOCKET       │ │  LOCATION        │ │  PUSH SERVICE    │
│                  │ │  GATEWAY         │ │  INGESTION       │ │                  │
│  [30 instances]  │ │  [40 instances]  │ │  [20 instances]  │ │  [10 instances]  │
│                  │ │                  │ │                  │ │                  │
│  - Auth/JWT      │ │  - Rider ←→ Driver│ │  - 1M updates/sec│ │  - APNs/FCM     │
│  - Rate limiting │ │  - Real-time     │ │  - S2 cell calc  │ │  - Batch sends   │
│  - Routing       │ │  - During ride   │ │  - Redis writes  │ │                  │
└────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘ └────────┬─────────┘
         │                    │                    │                    │
         └────────────────────┼────────────────────┼────────────────────┘
                              │                    │
                              ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    MICROSERVICES LAYER                                              │
├─────────────────────┬─────────────────────┬─────────────────────┬───────────────────────────────────┤
│  MATCHING SERVICE   │  RIDE SERVICE       │  PRICING SERVICE    │  SUPPLY SERVICE                  │
│  [20 instances]     │  [30 instances]     │  [10 instances]     │  [15 instances]                  │
│                     │                     │                     │                                   │
│  - Find candidates  │  - Ride CRUD        │  - Fare estimate    │  - Driver availability           │
│  - ETA calculation  │  - State machine    │  - Upfront pricing  │  - Nearby drivers                │
│  - Sequential offer │  - Transitions      │  - Surge calc       │  - Cell management               │
│  - Conflict resolve │  - Event publish    │  - ML predictions   │  - Heat maps                     │
└─────────┬───────────┴─────────┬───────────┴─────────┬───────────┴───────────────────┬───────────────┘
          │                     │                     │                               │
          ▼                     ▼                     ▼                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    REDIS CLUSTER (Location + State)                                 │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│   KEY PATTERNS:                                                                                     │
│                                                                                                     │
│   1. DRIVER STATUS (Hash)                 2. CELL MEMBERSHIP (Set)                                 │
│      driver:{id}                             cell:{cell_id}:available                              │
│      ├── status: AVAILABLE/ON_TRIP          {driver_1, driver_5, driver_42}                        │
│      ├── lat: 12.97                                                                                 │
│      ├── lng: 77.59                       3. GEO INDEX                                             │
│      ├── cell_id: 9q5c                       drivers:geo                                           │
│      ├── vehicle_type: UberX                 GEOADD lng lat driver_id                              │
│      └── current_ride: null                                                                        │
│                                           4. SURGE MULTIPLIERS                                     │
│   TTL: 60 seconds                            surge:{cell_id} → 1.8                                 │
│   Extended by heartbeat                      TTL: 60 seconds                                       │
│                                                                                                     │
│   CLUSTER: 15 masters + 30 replicas, sharded by geographic region                                 │
│   TOTAL MEMORY: ~5 GB                                                                               │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATABASE LAYER                                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│   ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐                      │
│   │   MYSQL CLUSTER     │   │     CASSANDRA       │   │  MYSQL (Payments)   │                      │
│   │   (Active Rides)    │   │   (Trip History)    │   │  (Separate DB)      │                      │
│   ├─────────────────────┤   ├─────────────────────┤   ├─────────────────────┤                      │
│   │                     │   │                     │   │                     │                      │
│   │ • Active rides only │   │ • Completed trips   │   │ • Card tokens       │                      │
│   │ • ACID transactions │   │ • Billions of rows  │   │ • Transactions      │                      │
│   │ • State machine     │   │ • Write-once        │   │ • Audit trail       │                      │
│   │ • Sharded by city   │   │ • Partition by user │   │ • PCI compliance    │                      │
│   │ • Optimistic locks  │   │ • Time-series query │   │ • Strong consistency│                      │
│   │                     │   │                     │   │                     │                      │
│   │ WHY MYSQL:          │   │ WHY CASSANDRA:      │   │ WHY SEPARATE:       │                      │
│   │ • Need transactions │   │ • Massive scale     │   │ • Regulatory        │                      │
│   │ • Strong consistency│   │ • No updates needed │   │ • Isolation         │                      │
│   │ • Active rides < 1M │   │ • Fast writes       │   │ • Security          │                      │
│   └─────────────────────┘   └─────────────────────┘   └─────────────────────┘                      │
│                                                                                                     │
│   SHARDING STRATEGY:                                                                                │
│   ┌───────────────────────┬──────────────────────┬────────────────────────────────────────────────┐ │
│   │  DATA TYPE            │  SHARD KEY           │  WHY                                           │ │
│   ├───────────────────────┼──────────────────────┼────────────────────────────────────────────────┤ │
│   │  Users/Drivers        │  hash(user_id)       │  Users travel! Can't shard by region          │ │
│   │  Active Rides         │  city                │  Ride always happens in ONE city              │ │
│   │  Trip History         │  rider_id            │  "My trips" query is always by user           │ │
│   │  Payments             │  user_id             │  User can pay from anywhere                   │ │
│   │  Driver Location      │  geographic (Redis)  │  Query is always local to city                │ │
│   └───────────────────────┴──────────────────────┴────────────────────────────────────────────────┘ │
│                                                                                                     │
│   KEY INSIGHT: Users travel, but rides are always LOCAL to one city!                               │
│                                                                                                     │
│   DATABASE SELECTION GUIDE:                                                                         │
│   ┌───────────────────────┬──────────────────────┬────────────────────────────────────────────────┐ │
│   │  DATA TYPE            │  DATABASE            │  WHY                                           │ │
│   ├───────────────────────┼──────────────────────┼────────────────────────────────────────────────┤ │
│   │  Driver Locations     │  Redis               │  Real-time, 1M writes/sec, TTL auto-expiry    │ │
│   │  Active Rides         │  MySQL (by city)     │  ACID transactions, state machine             │ │
│   │  Trip History         │  Cassandra           │  Massive scale, append-only, fast reads       │ │
│   │  User Profiles        │  MySQL (by user_id)  │  Users travel, can't shard by location        │ │
│   │  Payments             │  MySQL (Separate)    │  Compliance, audit trail, strong consistency  │ │
│   │  Analytics            │  Hadoop/Spark        │  Batch processing, ML training                │ │
│   │  Location Stream      │  Kafka               │  Durability, multiple consumers               │ │
│   └───────────────────────┴──────────────────────┴────────────────────────────────────────────────┘ │
│                                                                                                     │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                    EXTERNAL SERVICES                                                │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│   MAPS API (Google/OSM)              PAYMENT GATEWAY                  PUSH SERVICES                │
│     - ETA calculation                  (Stripe/Razorpay)               (APNs/FCM)                  │
│     - Route optimization               - Card authorization            - iOS notifications         │
│     - Distance calculation             - Capture payments              - Android notifications     │
│                                        - Refunds                                                    │
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
│   ride-events                                 Analytics Service                                    │
│     - Ride created/matched/completed            - Trip metrics, demand patterns                    │
│     - 100 partitions                                                                                │
│                                               Notification Service                                  │
│   location-events                               - Push to rider/driver                              │
│     - Driver GPS stream (sampling)                                                                  │
│     - For ML training                         Billing Service                                      │
│                                                 - Driver payouts, invoices                          │
│   payment-events                                                                                    │
│     - Charges, refunds                        Fraud Detection                                      │
│                                                 - ML anomaly detection                              │
│   surge-updates                                                                                     │
│     - Pricing changes                         Surge Calculator                                     │
│                                                 - Recalculate every 30 sec                          │
│                                                                                                     │
│   CLUSTER: 20 brokers, replication factor 3, 7-day retention                                       │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 5. REQUEST FLOWS

## Flow 1: Driver Location Update (via Kafka)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              DRIVER LOCATION UPDATE (Every 5 sec)                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Driver app sends GPS: { lat: 12.9716, lng: 77.5946, driver_id: "D123" }

1. LOCATION INGESTION SERVICE receives update
           │
           ├────────────────────────────────────────────────────────────────────┐
           │                                                                    │
           ▼                                                                    ▼
2. PUBLISH TO KAFKA                                              3. UPDATE REDIS (Real-time)
   Topic: location-updates                                          (In parallel!)
   Partition: hash(driver_id) % 100                                  
                                                                     a) Update driver hash:
   Why Kafka?                                                           driver:D123 → { status, lat, lng, cell_id }
     • Durability (never lose location data)                            Set TTL to 60 seconds
     • Multiple consumers (analytics, ML, surge)                     
     • Buffer during traffic spikes                                  b) If cell changed:
     • Replay for debugging                                             Move between cell sets
           │                                                          
           ▼                                                         c) Update geo index
    ┌──────────────────────────────────────────────┐
    │              KAFKA CONSUMERS                 │
    ├──────────────────────────────────────────────┤
    │  • Redis Writer (backup path)                │
    │  • Analytics Service (trip patterns)         │
    │  • ML Pipeline (ETA model training)          │
    │  • Surge Calculator (demand signals)         │
    │  • Fraud Detection (unusual patterns)        │
    └──────────────────────────────────────────────┘


ARCHITECTURE PATTERN:

  Driver GPS ──► Location Service ──┬──► Kafka (durability, multi-consumer)
                                    │
                                    └──► Redis (real-time queries)

  Both paths happen in PARALLEL!
  • Redis for real-time matching (< 50ms)
  • Kafka for analytics, ML, durability

Latency: < 50ms (to Redis)
Volume: 1 million updates/sec
```

---

## Flow 2: Find Nearby Drivers (Map View)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              FIND NEARBY DRIVERS                                                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Rider opens app at location (12.97, 77.59)

1. GET /nearby-drivers?lat=12.97&lng=77.59
           │
           ▼
2. CALCULATE COVERING CELLS
   
   Rider's cell: 9q5e
   Neighbors: 9q5a, 9q5b, 9q5c, 9q5d, 9q5f, 9q5g, 9q5h, 9q5i
   
        ┌───────┬───────┬───────┐
        │ 9q5a  │ 9q5b  │ 9q5c  │
        ├───────┼───────┼───────┤
        │ 9q5d  │ RIDER │ 9q5f  │
        ├───────┼───────┼───────┤
        │ 9q5g  │ 9q5h  │ 9q5i  │
        └───────┴───────┴───────┘
           │
           ▼
3. QUERY REDIS (Parallel, all 9 cells)
   
   cell:9q5a:available → { }
   cell:9q5b:available → { D42 }
   cell:9q5c:available → { D15, D89 }
   cell:9q5d:available → { D23 }
   cell:9q5e:available → { D7, D56 }
   ...
           │
           ▼
4. GET DRIVER DETAILS
   
   For each driver → Get full hash (lat, lng, vehicle_type)
           │
           ▼
5. RETURN TO CLIENT
   
   {
     "drivers": [
       { "id": "D7", "lat": 12.968, "lng": 77.591, "type": "UberX" },
       { "id": "D56", "lat": 12.972, "lng": 77.588, "type": "XL" },
       ...
     ]
   }

Client refreshes every 5-10 seconds (POLLING - not WebSocket)
```

---

## Flow 3: Request Ride & Driver Matching

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              RIDE REQUEST & MATCHING                                                │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Rider requests ride: Koramangala → Indiranagar

1. CREATE RIDE RECORD
   
   Ride { 
     id: R456, 
     status: REQUESTED, 
     version: 1,
     pickup: (12.97, 77.59),
     destination: (12.98, 77.64)
   }
           │
           ▼
2. FIND CANDIDATE DRIVERS
   
   Query cells around pickup location
   Filter: status = AVAILABLE, vehicle_type matches
   Result: [D42, D15, D89, D23, D7, D56] (6 candidates)
           │
           ▼
3. CALCULATE ETA FOR EACH (Parallel calls to Maps API)
   
   D42: 8 min (stuck in traffic)
   D15: 4 min ← BEST
   D89: 5 min
   D23: 6 min
   D7:  7 min
   D56: 9 min
           │
           ▼
4. SORT BY ETA → [D15, D89, D23, D7, D42, D56]
           │
           ▼
5. OFFER TO BEST DRIVER (D15)
   
   Mark driver: status = OFFER_PENDING, offer_ride = R456
   Send via WebSocket/Push: "New ride request, 4 min away, ₹150"
           │
           ▼
6. WAIT FOR RESPONSE (15 second timeout)
   
   CASE A: Driver ACCEPTS
     ├── Validate: Is driver still OFFER_PENDING for this ride?
     ├── If yes → Assign driver, status = DRIVER_ASSIGNED
     ├── Notify rider: "Driver on the way!"
     └── Remove driver from available pool
   
   CASE B: Driver DECLINES or TIMEOUT
     ├── Mark D15 as "declined for R456"
     ├── Check cache age:
     │     < 30 sec → Try next driver (D89)
     │     > 30 sec → Recalculate ETAs (drivers moved)
     └── Repeat until matched or no drivers left
   
   CASE C: No drivers after 5 attempts
     └── Expand search radius (3km → 5km) and retry
```

---

## Flow 4: Ride State Machine

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              RIDE STATE TRANSITIONS                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────┐
                    │  REQUESTED  │
                    └──────┬──────┘
                           │ Find drivers
                           ▼
                    ┌─────────────┐         ┌─────────────────┐
                    │  MATCHING   │────────►│    CANCELLED    │ (Rider cancels before match)
                    └──────┬──────┘         └─────────────────┘
                           │ Driver accepts
                           ▼
                    ┌─────────────────┐     ┌─────────────────┐
                    │ DRIVER_ASSIGNED │────►│    CANCELLED    │ (Either cancels)
                    └────────┬────────┘     └─────────────────┘
                             │ Driver starts navigation
                             ▼
                    ┌─────────────────────┐
                    │ EN_ROUTE_TO_PICKUP  │
                    └────────┬────────────┘
                             │ Driver arrives
                             ▼
                    ┌─────────────────────┐  ┌─────────────────────┐
                    │ ARRIVED_AT_PICKUP   │─►│ CANCELLED + FEE     │ (Rider no-show after 5 min)
                    └────────┬────────────┘  └─────────────────────┘
                             │ Rider gets in, driver starts trip
                             ▼
                    ┌─────────────────────┐
                    │  TRIP_IN_PROGRESS   │  ← Cannot cancel during trip!
                    └────────┬────────────┘
                             │ Arrive at destination
                             ▼
                    ┌─────────────────────┐
                    │     COMPLETED       │
                    └────────┬────────────┘
                             │ Payment processed
                             ▼
                    ┌─────────────────────┐
                    │  PAYMENT_PROCESSED  │
                    └─────────────────────┘


STATE TRANSITION RULES:
  - Every transition uses OPTIMISTIC LOCKING (version check)
  - Invalid transitions are rejected (e.g., REQUESTED → COMPLETED)
  - Every transition publishes event to Kafka
```

---

## Flow 5: Real-Time Tracking During Ride

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              REAL-TIME TRACKING (WebSocket)                                         │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

During TRIP_IN_PROGRESS:

DRIVER APP                    SERVER                      RIDER APP
     │                           │                            │
     │ GPS update (every 2 sec)  │                            │
     │ ─────────────────────────►│                            │
     │                           │                            │
     │                           │ Lookup: ride R456          │
     │                           │ Find rider's WebSocket     │
     │                           │                            │
     │                           │ Push location ────────────►│
     │                           │                            │
     │                           │                            │ Update map
     │                           │                            │
     │ (repeat every 2 sec)      │                            │


WHY WEBSOCKET HERE (but not for map preview):
  
  MAP PREVIEW (before ride):
    - Rider just browsing
    - 5-10 sec refresh OK
    - Polling is simpler
  
  DURING RIDE (after matching):
    - Real-time matters!
    - 1:1 connection (one driver → one rider)
    - WebSocket is efficient
```

---

## Flow 6: Surge Pricing Calculation

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SURGE PRICING (Every 30 seconds)                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

SURGE SERVICE runs continuously:

Every 30 seconds, for each hexagonal cell:

1. COUNT DEMAND
   - Ride requests in last 2 minutes
   - App opens (potential demand)
   
   Example: Cell 9q5c has 50 requests in 2 min

2. COUNT SUPPLY
   - Available drivers in cell
   - Drivers heading toward cell (predicted)
   
   Example: Cell 9q5c has 20 available drivers

3. CALCULATE RATIO
   
   Demand/Supply = 50/20 = 2.5
   
   ┌─────────────────────────────────────────┐
   │  SURGE TABLE                            │
   ├─────────────────────────────────────────┤
   │  Ratio     │  Multiplier               │
   │  < 1.0     │  1.0× (no surge)          │
   │  1.0-1.5   │  1.2×                     │
   │  1.5-2.0   │  1.5×                     │
   │  2.0-2.5   │  1.8×                     │
   │  2.5-3.0   │  2.2×                     │
   │  > 3.0     │  2.5× (capped)            │
   └─────────────────────────────────────────┘
   
   Ratio 2.5 → Surge = 1.8×

4. STORE IN REDIS
   
   surge:9q5c → 1.8
   TTL: 60 seconds (auto-expires if not refreshed)

5. NOTIFY DRIVERS
   
   Publish: "Surge 1.8× in Koramangala"
   Drivers may relocate to earn more


WHY HEXAGONS (not squares)?
  - Equal distance from center to all edges
  - Smoother surge transitions between cells
  - Better coverage with fewer cells
```

---

## Flow 7: Fare Calculation (Upfront Pricing)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              FARE CALCULATION                                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

BEFORE RIDE (Estimate):

1. Rider enters pickup → destination
           │
           ▼
2. CALL MAPS API
   - Get optimal route
   - Get predicted duration (with traffic)
   - Get distance
           │
           ▼
3. CALCULATE BASE FARE
   
   Base fare:                    ₹50
   Distance (6 km × ₹12/km):     ₹72
   Time (20 min × ₹2/min):       ₹40
   ────────────────────────────────────
   Subtotal:                     ₹162
           │
           ▼
4. APPLY SURGE
   
   Current surge in pickup cell: 1.5×
   Fare × 1.5 = ₹243
           │
           ▼
5. ADD FEES
   
   Platform fee:                 ₹10
   ────────────────────────────────────
   Total:                        ₹253
           │
           ▼
6. SHOW TO RIDER
   
   "Your trip will cost ₹253"
   (This is what they'll pay, regardless of actual route!)


AFTER RIDE:

  Driver took different route due to traffic
  Actual distance: 7 km, actual time: 25 min
  Actual "meter" fare would be: ₹280
  
  BUT rider still pays: ₹253 (upfront price)
  
  Exception: Rider changed destination mid-trip → Recalculate
```

---

## Flow 8: Payments

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              PAYMENT FLOW                                                           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

BEFORE RIDE (Authorization):

1. Rider requests ride with card on file
           │
           ▼
2. AUTHORIZE PAYMENT
   
   Call payment gateway: "Hold ₹300 on this card"
   (₹300 > estimated ₹253, for buffer)
   
   If authorization fails → "Please update payment method"
           │
           ▼
3. RIDE PROCEEDS...


AFTER RIDE (Capture):

1. Trip ends, final fare = ₹253
           │
           ▼
2. CAPTURE PAYMENT
   
   Call payment gateway: "Charge ₹253 from the ₹300 hold"
   Release remaining ₹47 hold
           │
           ▼
3. UPDATE DRIVER EARNINGS
   
   Driver cut: ₹253 × 0.80 = ₹202
   Uber cut:   ₹253 × 0.20 = ₹51
   
   Add ₹202 to driver's earnings balance


DRIVER PAYOUT (Weekly):

1. Every Monday, sum driver's earnings
2. Deduct any fees (phone rental, etc.)
3. Transfer to driver's bank account

Optional: Instant payout (small fee)
```

---

# 6. EDGE CASES & ERROR HANDLING

## Driver Goes Offline During Matching

```
1. Offer sent to Driver D15
2. D15's app crashes / goes offline
3. Timeout after 15 sec → No response
4. System detects: Redis key driver:D15 expired (TTL)
5. Automatically try next driver
6. D15 removed from available pool until reconnects
```

---

## Two Riders Request Same Driver

```
Rider A offers to D15 at T+0
Rider B offers to D15 at T+2

D15 can only see ONE offer at a time
  - Latest offer replaces previous (OR)
  - D15's status is OFFER_PENDING, B can't offer

If D15 accepts A's ride:
  - Atomic check: Is D15 still available for A's offer?
  - Yes → Assign
  - No (already took B) → Retry A with next driver
```

---

## Payment Fails After Ride

```
1. Ride completes, capture payment fails
2. Mark ride as "PAYMENT_PENDING"
3. Retry capture every hour for 7 days
4. Still fails → Send rider notification to update card
5. After 14 days → Send to collections, ban account
6. Driver still gets paid by Uber (Uber absorbs loss)
```

---

## Driver Takes Wrong Route

```
Upfront pricing protects rider:
  - Rider pays ₹253 regardless of actual route
  - Driver gets paid based on actual km/time
  - If much longer → Investigate for fraud
  - ML model flags suspicious patterns
```

---

## Sync vs Async Decision Table

| Operation | Sync/Async | Why |
|-----------|-----------|-----|
| Ride request | SYNC | Rider waiting for response |
| Find drivers | SYNC | Part of matching flow |
| ETA calculation | SYNC | Need answer immediately |
| Driver offer | SYNC (WebSocket) | Real-time interaction |
| Push notification | ASYNC (Kafka) | 1-2 sec delay OK |
| Analytics logging | ASYNC (Kafka) | Not user-facing |
| Surge calculation | ASYNC (Batch) | Every 30 sec is fine |
| Driver payout | ASYNC (Kafka) | Weekly batch |
| Fraud detection | ASYNC (Kafka) | Background analysis |

---

# 7. INTERVIEW TALKING POINTS

## Why S2/GeoHash Instead of PostGIS?

```
PostGIS: Great for static data (stores, restaurants)
S2/Redis: Great for moving data (drivers)

Driver locations change every 5 sec:
  - 1M writes/sec is too much for PostGIS
  - Redis handles this easily
  - S2 cells enable O(1) lookups
```

## Why ETA-Based Matching?

```
Distance is misleading:
  - 500m through traffic jam = 10 min
  - 800m on main road = 4 min

ETA gives better rider experience
Calculated using: Maps API + real-time traffic + ML
```

## Why Upfront Pricing?

```
Old model (meter):
  - Rider doesn't know final cost
  - Surprise surge at end
  - Driver can take long route

Upfront model:
  - Rider knows cost before booking
  - Uber absorbs variance (balances out)
  - Protects against wrong routes
```

## Why Not Broadcast to All Drivers?

```
10 drivers receive offer simultaneously
3 drivers accept within 1 second
Who gets the ride?

Race condition nightmare!
Sequential offers are simpler and reliable
```

## How Does Surge Prevent Starvation?

```
Without surge:
  - 100 riders, 20 drivers
  - 80 riders can't get a cab

With surge (2×):
  - 50 riders say "too expensive" → leave
  - 10 more drivers see surge → come to area
  - 50 riders, 30 drivers → Better balance!
```

---

# 8. TECHNOLOGY SUMMARY

| Component | Technology | Why |
|-----------|------------|-----|
| **Location Store** | Redis Cluster | Fast writes, TTL support |
| **Geo Indexing** | S2/GeoHash | Hierarchical cells, efficient queries |
| **Ride Database** | PostgreSQL | ACID for transactions |
| **Message Queue** | Kafka | High throughput, replay capability |
| **Real-time** | WebSocket | Low latency during rides |
| **Maps/ETA** | Google Maps API | Industry standard |
| **Payments** | Stripe/Razorpay | PCI compliance |
| **Push** | APNs + FCM | Native mobile support |
| **Caching** | Redis | Session, surge values |
| **Load Balancer** | AWS ALB + Nginx | Geographic routing |
