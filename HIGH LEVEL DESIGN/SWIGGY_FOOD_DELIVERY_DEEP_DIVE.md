# Swiggy / Food Delivery — Complete Deep Dive

> Interview-ready documentation — Covers Zomato, DoorDash, UberEats, any Food Delivery

---

# 1. FUNCTIONAL REQUIREMENTS

## Priority Levels
- **P0** = Must have (core functionality)
- **P1** = Should have (important features)
- **P2** = Nice to have (enhancements)

## Feature List

| # | Feature | Priority | Description |
|---|---------|----------|-------------|
| 1 | **Restaurant Discovery** | P0 | Browse, search, filter restaurants |
| 2 | **Menu & Pricing** | P0 | View dishes, customizations, prices |
| 3 | **Cart & Checkout** | P0 | Add items, apply coupons, order |
| 4 | **Order Tracking** | P0 | Real-time order status, rider location |
| 5 | **Rider Assignment** | P0 | Match order to delivery partner |
| 6 | **Payments** | P0 | Online/COD, refunds |
| 7 | **Restaurant Onboarding** | P1 | Partner restaurant signup |
| 8 | **Restaurant Dashboard** | P1 | Manage menu, orders, availability |
| 9 | **Ratings & Reviews** | P1 | Rate restaurants, dishes, riders |
| 10 | **Rider App** | P0 | Accept orders, navigation, earnings |
| 11 | **Surge Pricing** | P1 | Dynamic pricing during high demand |
| 12 | **Promotions** | P1 | Coupons, discounts, free delivery |
| 13 | **Subscription (Swiggy One)** | P2 | Free delivery, extra discounts |
| 14 | **Scheduled Orders** | P2 | Order for later |
| 15 | **Group Orders** | P2 | Multiple people, split bills |

---

# 2. NON-FUNCTIONAL REQUIREMENTS

## Latency

| Operation | Target | Rationale |
|-----------|--------|-----------|
| Restaurant search | < 200ms | Interactive |
| Menu load | < 300ms | First impression |
| Add to cart | < 100ms | Must feel instant |
| Place order | < 1 sec | Critical path |
| Rider assignment | < 30 sec | User waiting |
| Location update | < 500ms | Real-time tracking |

## Throughput

| Metric | Normal | Peak (Lunch/Dinner) |
|--------|--------|---------------------|
| DAU | 20 million | 50 million |
| Orders/day | 5 million | 15 million |
| Orders/minute (peak) | 50,000 | 150,000 |
| Location updates/sec | 500,000 | 1,000,000 |

## Availability

| Component | Target | Strategy |
|-----------|--------|----------|
| Order placement | 99.99% | Multi-region, fallback |
| Rider tracking | 99.9% | Eventual consistency OK |
| Restaurant dashboard | 99.9% | Can tolerate brief downtime |

---

# 3. CAPACITY PLANNING

```
┌────────────────────────────────────────────────────────────────────────┐
│                    SWIGGY CAPACITY CHEAT SHEET                         │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  SCALE                                                                 │
│  • DAU: 20M (normal), 50M (peak)                                      │
│  • Orders/day: 5M (normal), 15M (peak)                                │
│  • Active riders: 500,000                                              │
│  • Restaurants: 500,000                                                │
│  • Cities: 500+                                                        │
│                                                                        │
│  STORAGE                                                               │
│  • Restaurant data: 50 GB                                              │
│  • Menu items: 100 GB                                                  │
│  • Orders: 500 GB/year                                                 │
│  • Location history: 5 TB/year                                         │
│                                                                        │
│  REAL-TIME                                                             │
│  • Location updates: 1M/sec                                            │
│  • Order events: 100K/sec (peak)                                       │
│  • Rider assignments: 5K/sec (peak)                                    │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

# 4. DETAILED HLD DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 SWIGGY / FOOD DELIVERY ARCHITECTURE                                │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                           CLIENTS
           ┌───────────────────────────────────────────────────────────────────────┐
           │   Customer App        Restaurant App        Rider App        Web     │
           │   (iOS/Android)       (Tablet/Phone)       (Android)        (React)  │
           └───────────────────────────────────────────────────────────────────────┘
                       │                    │                  │
                       ▼                    ▼                  ▼
           ┌─────────────────────────────────────────────────────────────────────────┐
           │                            LOAD BALANCER                                │
           │                     (Geographic routing by city)                        │
           └─────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
           ┌─────────────────────────────────────────────────────────────────────────┐
           │                            API GATEWAY                                  │
           │                                                                         │
           │   • Authentication (JWT)        • Rate limiting                        │
           │   • Request routing             • A/B testing flags                    │
           └─────────────────────────────────────────────────────────────────────────┘
                                              │
          ┌───────────────────────────────────┼───────────────────────────────────────┐
          │                                   │                                       │
          ▼                                   ▼                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    MICROSERVICES LAYER                                              │
├─────────────────────┬─────────────────────┬─────────────────────┬───────────────────────────────────┤
│  RESTAURANT SERVICE │  MENU SERVICE       │  ORDER SERVICE      │  CART SERVICE                    │
│                     │                     │                     │                                   │
│  - Restaurant CRUD  │  - Menu items       │  - Order creation   │  - Cart management               │
│  - Availability     │  - Customizations   │  - Order tracking   │  - Price calculation             │
│  - Operating hours  │  - Pricing          │  - Order history    │  - Coupon validation             │
│  - Ratings          │  - Stock status     │  - Cancellation     │                                   │
├─────────────────────┼─────────────────────┼─────────────────────┼───────────────────────────────────┤
│  RIDER SERVICE      │  ASSIGNMENT SERVICE │  LOCATION SERVICE   │  PAYMENT SERVICE                 │
│                     │                     │                     │                                   │
│  - Rider profiles   │  - Order matching   │  - Real-time GPS    │  - Payment gateway               │
│  - Availability     │  - Load balancing   │  - ETA calculation  │  - Wallet                        │
│  - Earnings         │  - Batching orders  │  - Route planning   │  - Refunds                       │
│  - Incentives       │                     │  - Geofencing       │  - COD handling                  │
├─────────────────────┼─────────────────────┼─────────────────────┼───────────────────────────────────┤
│  SEARCH SERVICE     │  PRICING SERVICE    │  NOTIFICATION SVC   │  ANALYTICS SERVICE               │
│                     │                     │                     │                                   │
│  - Elasticsearch    │  - Surge pricing    │  - Push/SMS/Email   │  - Order metrics                 │
│  - Geo-search       │  - Delivery fee     │  - Real-time alerts │  - Rider performance             │
│  - Recommendations  │  - Promotions       │  - In-app messages  │  - Restaurant metrics            │
└─────────────────────┴─────────────────────┴─────────────────────┴───────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    REAL-TIME LAYER                                                  │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│   WEBSOCKET SERVERS:                                LOCATION INGESTION:                            │
│   - Customer: Order status updates                  - Rider GPS every 3 sec                       │
│   - Restaurant: New order alerts                    - Kafka → Location Service                    │
│   - Rider: New order assignments                    - Redis Geo for fast lookup                   │
│                                                                                                     │
│   CONNECTION MANAGER:                               REAL-TIME ETA:                                 │
│   - user:{id} → ws_server_1                         - Traffic data                                │
│   - Pub/Sub for cross-server messages               - Restaurant prep time                        │
│                                                     - Rider current location                       │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    CACHE LAYER (REDIS)                                              │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│   RESTAURANT CACHE:                        RIDER CACHE:                                            │
│   restaurant:{id} = {...}                  rider:{id}:location = {lat, lng, timestamp}            │
│   restaurant:{id}:menu = [...]             rider:{id}:status = "available|busy|offline"           │
│   restaurant:{id}:is_open = true           riders:available:{city} = [rider_ids...]              │
│                                                                                                     │
│   GEO INDEX (Redis Geo):                   SESSION:                                                │
│   restaurants:geo:{city} = {               user:{id}:cart = {...}                                 │
│     R1: (lat1, lng1),                      user:{id}:session = {...}                              │
│     R2: (lat2, lng2)                                                                               │
│   }                                        SURGE PRICING:                                          │
│   riders:geo:{city} = {                    surge:{zone_id} = 1.5                                  │
│     D1: (lat1, lng1),                      surge:{zone_id}:demand = 150                           │
│     D2: (lat2, lng2)                       surge:{zone_id}:supply = 100                           │
│   }                                                                                                 │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATABASE LAYER                                                   │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│   ┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐                      │
│   │   POSTGRESQL        │   │     CASSANDRA       │   │  ELASTICSEARCH      │                      │
│   │   (Transactional)   │   │   (High Write)      │   │  (Search)           │                      │
│   ├─────────────────────┤   ├─────────────────────┤   ├─────────────────────┤                      │
│   │                     │   │                     │   │                     │                      │
│   │ • restaurants       │   │ • orders            │   │ • restaurants index │                      │
│   │ • menus             │   │ • location_history  │   │ • menu_items index  │                      │
│   │ • riders            │   │ • rider_activities  │   │                     │                      │
│   │ • users             │   │ • notifications     │   │ Geo queries:        │                      │
│   │ • payments          │   │                     │   │ • Nearby restaurants│                      │
│   │                     │   │                     │   │ • Filter by cuisine │                      │
│   └─────────────────────┘   └─────────────────────┘   └─────────────────────┘                      │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    ASYNC PROCESSING (KAFKA)                                         │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│   TOPICS:                               CONSUMERS:                                                 │
│                                                                                                     │
│   order-events                          Assignment Service                                         │
│     - Order placed                        - Find nearby rider                                      │
│     - Order accepted                                                                                │
│     - Order picked up                   Notification Service                                       │
│     - Order delivered                     - SMS/Push to customer                                   │
│                                           - Alert restaurant                                       │
│   location-events                                                                                   │
│     - Rider GPS updates                 Analytics Service                                          │
│     - Every 3 seconds                     - Order completion time                                  │
│                                           - Rider efficiency                                       │
│   rider-events                                                                                      │
│     - Go online/offline                 ETA Service                                                │
│     - Accept/reject order                 - Recalculate delivery time                              │
│                                                                                                     │
│   restaurant-events                     Search Indexer                                             │
│     - Open/close                          - Update availability                                    │
│     - Menu updates                                                                                  │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 5. DATABASE SCHEMA

## Core Tables (PostgreSQL)

```sql
-- Restaurants
CREATE TABLE restaurants (
    restaurant_id   UUID PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    address         JSONB,
    location        GEOGRAPHY(POINT),
    city_id         UUID REFERENCES cities(city_id),
    cuisines        TEXT[],
    avg_rating      DECIMAL(2,1) DEFAULT 0,
    total_ratings   INTEGER DEFAULT 0,
    avg_prep_time   INTEGER DEFAULT 30,  -- minutes
    min_order_value DECIMAL(10,2) DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    is_accepting    BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Operating hours
CREATE TABLE restaurant_hours (
    restaurant_id   UUID REFERENCES restaurants(restaurant_id),
    day_of_week     INTEGER,  -- 0=Sunday
    open_time       TIME,
    close_time      TIME,
    PRIMARY KEY (restaurant_id, day_of_week)
);

-- Menu items
CREATE TABLE menu_items (
    item_id         UUID PRIMARY KEY,
    restaurant_id   UUID NOT NULL REFERENCES restaurants(restaurant_id),
    category        VARCHAR(100),
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    price           DECIMAL(10,2) NOT NULL,
    image_url       VARCHAR(500),
    is_veg          BOOLEAN DEFAULT FALSE,
    is_bestseller   BOOLEAN DEFAULT FALSE,
    is_available    BOOLEAN DEFAULT TRUE,
    prep_time       INTEGER DEFAULT 15  -- minutes
);

-- Item customizations
CREATE TABLE item_customizations (
    customization_id UUID PRIMARY KEY,
    item_id          UUID REFERENCES menu_items(item_id),
    group_name       VARCHAR(100),  -- "Size", "Toppings"
    option_name      VARCHAR(100),  -- "Large", "Extra Cheese"
    price_modifier   DECIMAL(10,2) DEFAULT 0,
    is_default       BOOLEAN DEFAULT FALSE,
    max_selections   INTEGER DEFAULT 1
);
```

## Riders

```sql
-- Riders (Delivery Partners)
CREATE TABLE riders (
    rider_id        UUID PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    phone           VARCHAR(20) UNIQUE NOT NULL,
    email           VARCHAR(255),
    vehicle_type    VARCHAR(20),  -- bike, scooter, bicycle
    license_number  VARCHAR(50),
    city_id         UUID REFERENCES cities(city_id),
    rating          DECIMAL(2,1) DEFAULT 5.0,
    total_deliveries INTEGER DEFAULT 0,
    status          VARCHAR(20) DEFAULT 'offline', -- online, busy, offline
    is_verified     BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Rider earnings
CREATE TABLE rider_earnings (
    earning_id      UUID PRIMARY KEY,
    rider_id        UUID REFERENCES riders(rider_id),
    order_id        UUID,
    base_pay        DECIMAL(10,2),
    distance_pay    DECIMAL(10,2),
    surge_bonus     DECIMAL(10,2),
    tip             DECIMAL(10,2),
    incentive       DECIMAL(10,2),
    total           DECIMAL(10,2),
    date            DATE,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

## Orders (Cassandra)

```sql
-- Orders partitioned by user
CREATE TABLE orders (
    user_id           UUID,
    order_id          UUID,
    order_number      TEXT,
    restaurant_id     UUID,
    restaurant_name   TEXT,
    rider_id          UUID,
    status            TEXT,  -- placed, confirmed, preparing, picked_up, delivered, cancelled
    items             LIST<FROZEN<order_item>>,
    subtotal          DECIMAL,
    delivery_fee      DECIMAL,
    surge_fee         DECIMAL,
    taxes             DECIMAL,
    discount          DECIMAL,
    total             DECIMAL,
    delivery_address  FROZEN<address_type>,
    payment_method    TEXT,
    payment_status    TEXT,
    special_instructions TEXT,
    estimated_delivery TIMESTAMP,
    actual_delivery   TIMESTAMP,
    created_at        TIMESTAMP,
    
    PRIMARY KEY ((user_id), order_id)
) WITH CLUSTERING ORDER BY (order_id DESC);

-- Orders by restaurant (for restaurant app)
CREATE TABLE orders_by_restaurant (
    restaurant_id     UUID,
    date              DATE,
    order_id          UUID,
    user_id           UUID,
    status            TEXT,
    items             LIST<FROZEN<order_item>>,
    total             DECIMAL,
    created_at        TIMESTAMP,
    
    PRIMARY KEY ((restaurant_id, date), order_id)
) WITH CLUSTERING ORDER BY (order_id DESC);

-- Orders by rider
CREATE TABLE orders_by_rider (
    rider_id          UUID,
    date              DATE,
    order_id          UUID,
    restaurant_id     UUID,
    status            TEXT,
    pickup_address    FROZEN<address_type>,
    delivery_address  FROZEN<address_type>,
    earning           DECIMAL,
    created_at        TIMESTAMP,
    
    PRIMARY KEY ((rider_id, date), order_id)
) WITH CLUSTERING ORDER BY (order_id DESC);
```

---

# 6. REQUEST FLOWS

## Flow 1: Restaurant Discovery

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              RESTAURANT DISCOVERY FLOW                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User opens app with location permission
           │
           ▼
1. GET USER LOCATION
   - GPS coordinates
   - Resolve to delivery zone/city
           │
           ▼
2. NEARBY RESTAURANTS (Elasticsearch + Redis Geo)
   
   POST /restaurants/_search
   {
     "query": {
       "bool": {
         "must": { "term": { "is_active": true } },
         "filter": {
           "geo_distance": {
             "distance": "5km",
             "location": { "lat": 12.97, "lon": 77.59 }
           }
         }
       }
     },
     "sort": [
       { "_geo_distance": { "location": {...}, "order": "asc" } }
     ]
   }
           │
           ▼
3. FILTER BY AVAILABILITY
   
   For each restaurant:
     - Is currently open? (check operating hours)
     - Is accepting orders? (not too busy)
     - Delivery radius includes user?
           │
           ▼
4. ENRICH WITH REAL-TIME DATA
   
   Redis:
     - restaurant:{id}:current_prep_time = 25
     - restaurant:{id}:is_accepting = true
           │
           ▼
5. CALCULATE DELIVERY ESTIMATES
   
   For each restaurant:
     delivery_time = prep_time + travel_time(restaurant → user)
     
   Sort by:
     - Relevance (user preferences)
     - Rating
     - Delivery time
     - Promoted restaurants (paid)
           │
           ▼
6. RESPONSE
   
   {
     "restaurants": [
       {
         "id": "R1",
         "name": "Pizza Hut",
         "cuisines": ["Pizza", "Italian"],
         "rating": 4.2,
         "delivery_time": "30-35 min",
         "delivery_fee": 25,
         "promoted": false
       },
       ...
     ]
   }
```

---

## Flow 2: View Menu & Add to Cart

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              MENU & CART FLOW                                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User taps on restaurant
           │
           ▼
1. LOAD RESTAURANT DETAILS + MENU
   
   Parallel calls:
     a) Restaurant info (cached in Redis)
     b) Menu items (cached in Redis)
     c) Reviews summary
     d) Real-time availability
           │
           ▼
2. DISPLAY MENU BY CATEGORY
   
   Categories: Starters, Main Course, Beverages, Desserts
   Each item: name, price, veg/non-veg, description, image
           │
           ▼
3. USER ADDS ITEM TO CART
   
   Selected: "Margherita Pizza - Large + Extra Cheese"
   
   a) Validate item available
   b) Calculate price with customizations
   c) Add to cart (Redis):
      
      HSET cart:{user_id} {item_key} {
        restaurant_id: "R1",
        item_id: "I1",
        name: "Margherita Pizza",
        customizations: ["Large", "Extra Cheese"],
        quantity: 1,
        unit_price: 350,
        total: 350
      }
           │
           ▼
4. CART VALIDATION RULES
   
   - Can only order from ONE restaurant at a time
   - If adding from different restaurant:
       → "Clear cart and add?" prompt
   
   - Minimum order value check
   - Item availability check (each time cart viewed)
           │
           ▼
5. CART SUMMARY
   
   {
     "restaurant": "Pizza Hut",
     "items": [...],
     "subtotal": 650,
     "delivery_fee": 25,
     "taxes": 32,
     "total": 707,
     "delivery_time": "30-35 min"
   }
```

---

## Flow 3: Place Order

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              ORDER PLACEMENT FLOW                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User clicks "Place Order"
           │
           ▼
1. VALIDATE CART
   
   - All items still available?
   - Restaurant still open?
   - Minimum order value met?
   - Delivery address in range?
           │
           ▼
2. CALCULATE FINAL PRICING
   
   subtotal = sum(items)
   delivery_fee = base_fee + distance_fee + surge_fee
   taxes = subtotal × tax_rate
   discount = apply_coupons()
   total = subtotal + delivery_fee + taxes - discount
           │
           ▼
3. PROCESS PAYMENT
   
   Online payment:
     - Call payment gateway (Razorpay)
     - Idempotency key = order_id
     - Wait for confirmation
   
   COD:
     - Mark payment as "pending"
     - Collect on delivery
           │
           ▼
4. CREATE ORDER
   
   BEGIN TRANSACTION
     INSERT INTO orders (...)
     INSERT INTO orders_by_restaurant (...)
     CLEAR cart:{user_id}
   COMMIT
           │
           ▼
5. PUBLISH ORDER EVENT (Kafka)
   
   Topic: order-events
   {
     "event": "order_placed",
     "order_id": "O123",
     "restaurant_id": "R1",
     "user_id": "U1",
     "delivery_address": {...},
     "timestamp": "..."
   }
           │
           ▼
6. PARALLEL ACTIONS
   
   ├──► Notify Restaurant
   │      WebSocket: "New order received!"
   │      Auto-accept or manual accept
   │
   ├──► Start Rider Assignment
   │      (See Flow 4)
   │
   └──► Notify Customer
         Push: "Order placed successfully!"
           │
           ▼
7. RESPONSE TO CUSTOMER
   
   {
     "order_id": "O123",
     "status": "placed",
     "estimated_delivery": "35 min",
     "tracking_url": "/track/O123"
   }
```

---

## Flow 4: Rider Assignment (THE CORE PROBLEM!)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              RIDER ASSIGNMENT ALGORITHM                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

CHALLENGE:
  - 500K active riders
  - 50K orders/minute at peak
  - Need to assign in < 30 seconds
  - Optimize for: delivery time, rider utilization, cost


ASSIGNMENT FLOW:

Order placed
     │
     ▼
1. FIND NEARBY AVAILABLE RIDERS (Redis Geo)
   
   GEORADIUS riders:geo:{city} {restaurant_lat} {restaurant_lng} 3 km
   
   Filter:
     - status = "available" (not busy, not offline)
     - vehicle_type compatible with order size
     - Rating > 4.0 for priority orders
   
   Result: [D1, D5, D8, D12, D15] (5 candidates)
           │
           ▼
2. SCORE EACH RIDER
   
   score = w1 × proximity_score
         + w2 × rating_score
         + w3 × acceptance_rate
         + w4 × current_earnings_gap  (fairness)
         - w5 × detour_penalty (if already has order)
   
   Example scores:
     D1: 85 (closest, good rating)
     D5: 78 (medium distance, excellent rating)
     D8: 72 (has another order nearby - can batch)
           │
           ▼
3. SEND OFFER TO TOP RIDER
   
   WebSocket → Rider App:
   {
     "order_id": "O123",
     "restaurant": "Pizza Hut",
     "pickup": {...},
     "dropoff": {...},
     "distance": "3.5 km",
     "earning": "₹45",
     "expires_in": 30  // seconds
   }
           │
           ├── ACCEPTED → Assign rider, notify customer
           │
           └── REJECTED or TIMEOUT (30 sec)
                     │
                     ▼
4. CASCADE TO NEXT RIDER
   
   Try D5 → 30 sec → Try D8 → 30 sec → ...
   
   If all reject:
     - Expand search radius (3km → 5km → 8km)
     - Increase rider earning (surge bonus)
     - Retry with new candidates
           │
           ▼
5. ASSIGNMENT CONFIRMED
   
   Update Redis:
     rider:{id}:status = "busy"
     rider:{id}:current_order = "O123"
   
   Publish: rider-events
   {
     "event": "order_assigned",
     "rider_id": "D1",
     "order_id": "O123"
   }
   
   Notify customer: "Rider assigned! Arriving in 10 min"


ORDER BATCHING (Advanced):

Rider D8 has order O100 (picking up from Restaurant A)
New order O123 comes (Restaurant B is 500m from A)

System detects batching opportunity:
  - Same direction
  - Minimal detour (< 1km extra)
  - Both customers get delivery within time window

Batch order:
  D8.orders = [O100, O123]
  Route: A → B → Customer1 → Customer2
```

---

## Flow 5: Real-Time Order Tracking

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              ORDER TRACKING FLOW                                                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

ORDER LIFECYCLE:

    ┌──────────┐
    │  PLACED  │ (Order received)
    └────┬─────┘
         │ Restaurant accepts
         ▼
    ┌───────────┐
    │ CONFIRMED │
    └─────┬─────┘
          │ Kitchen starts
          ▼
    ┌───────────┐
    │ PREPARING │ (Prep time countdown)
    └─────┬─────┘
          │ Ready for pickup
          ▼
    ┌───────────┐
    │   READY   │
    └─────┬─────┘
          │ Rider picks up
          ▼
    ┌───────────┐
    │ PICKED UP │ (Live tracking starts)
    └─────┬─────┘
          │ En route
          ▼
    ┌───────────┐
    │ ARRIVING  │ (< 1km away)
    └─────┬─────┘
          │
          ▼
    ┌───────────┐
    │ DELIVERED │
    └───────────┘


REAL-TIME LOCATION UPDATES:

Rider app sends location every 3 seconds:
     │
     ▼
1. LOCATION INGESTION (Kafka)
   
   Topic: location-events
   { rider_id, lat, lng, timestamp, heading, speed }
     │
     ▼
2. UPDATE REDIS GEO INDEX
   
   GEOADD riders:geo:{city} {lng} {lat} {rider_id}
   SET rider:{id}:location { lat, lng, timestamp }
     │
     ▼
3. STORE IN CASSANDRA (History)
   
   INSERT INTO location_history (rider_id, timestamp, location)
     │
     ▼
4. RECALCULATE ETA
   
   new_eta = current_location → delivery_address
   Consider: traffic, remaining distance, avg speed
     │
     ▼
5. PUSH TO CUSTOMER (WebSocket)
   
   {
     "type": "location_update",
     "order_id": "O123",
     "rider_location": { lat, lng },
     "eta": "5 min"
   }


CUSTOMER TRACKING PAGE:

┌─────────────────────────────────────────────────────┐
│  ORDER #O123                            X Close    │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │                                             │   │
│  │          [MAP WITH LIVE LOCATION]           │   │
│  │                                             │   │
│  │      🛵 -----> 📍                           │   │
│  │      Rider    Your location                 │   │
│  │                                             │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  Status: Out for delivery                          │
│  ETA: 5 minutes                                    │
│                                                     │
│  Rider: Ravi K.  ⭐ 4.8                            │
│  📞 Call  |  💬 Chat                               │
│                                                     │
│  ─────────────────────────────────────────────     │
│  Timeline:                                         │
│  ✓ Order placed         8:00 PM                   │
│  ✓ Restaurant accepted  8:01 PM                   │
│  ✓ Preparing            8:02 PM                   │
│  ✓ Picked up            8:20 PM                   │
│  ○ Arriving soon        ~8:28 PM                  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Flow 6: Surge Pricing

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SURGE PRICING                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

WHY SURGE?
  - 8 PM dinner rush: 1000 orders/min, only 500 riders
  - Without surge: Long wait times, rider shortage
  - With surge: Higher pay attracts more riders, reduces demand


SURGE CALCULATION (Every 5 minutes):

For each zone in city:
     │
     ▼
1. CALCULATE DEMAND
   
   orders_last_15_min = count(orders in zone)
   predicted_orders = ML model (time, day, weather, events)
   
2. CALCULATE SUPPLY
   
   available_riders = count(online, not busy in zone)
   incoming_riders = riders heading to zone after current delivery
   
3. COMPUTE SURGE MULTIPLIER
   
   demand_supply_ratio = predicted_orders / available_riders
   
   if ratio > 1.5 → surge = 1.2× (20% extra)
   if ratio > 2.0 → surge = 1.5× (50% extra)
   if ratio > 3.0 → surge = 2.0× (100% extra)
   
   cap at 2.5× (protect customers)
     │
     ▼
4. STORE IN REDIS
   
   SET surge:{zone_id} 1.5 EX 300  (5 min TTL)
   SET surge:{zone_id}:breakdown {
     demand: 150,
     supply: 75,
     ratio: 2.0,
     multiplier: 1.5
   }
     │
     ▼
5. APPLY TO ORDERS
   
   When user sees delivery fee:
     base_fee = ₹25
     surge_fee = base_fee × (surge_multiplier - 1)
     total_fee = ₹25 + ₹12.50 = ₹37.50
   
   Show user: "High demand in your area (+₹12.50)"
     │
     ▼
6. RIDER INCENTIVE
   
   Rider earning also increases:
   base_pay = ₹30
   surge_bonus = ₹30 × (1.5 - 1) = ₹15
   total = ₹45


SURGE ZONES:

City divided into zones (1-2 km each):
┌─────┬─────┬─────┐
│ Z1  │ Z2  │ Z3  │
│ 1.0×│ 1.5×│ 1.2×│
├─────┼─────┼─────┤
│ Z4  │ Z5  │ Z6  │
│ 1.0×│ 2.0×│ 1.0×│
└─────┴─────┴─────┘

Zone Z5 has surge due to:
  - Cricket match nearby (event)
  - Dinner time
  - Rain (fewer riders)
```

---

## Flow 7: Restaurant Dashboard

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              RESTAURANT OPERATIONS                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

RESTAURANT RECEIVES NEW ORDER:

1. ALERT VIA WEBSOCKET
   
   Restaurant tablet/app receives:
   {
     "type": "new_order",
     "order_id": "O123",
     "items": [...],
     "customer_instructions": "Less spicy",
     "prep_time_suggested": 25
   }
   
   🔔 Alert sound + notification
           │
           ▼
2. RESTAURANT ACCEPTS ORDER
   
   Options:
     a) Accept with suggested time (25 min)
     b) Accept with custom time (30 min)
     c) Reject (item unavailable, closing soon)
   
   POST /restaurant/orders/O123/accept
   { prep_time: 25 }
           │
           ▼
3. PREP TIME COMMUNICATED
   
   - Customer notified: "Restaurant is preparing your order"
   - Rider assignment can be delayed until ~10 min before ready
           │
           ▼
4. ORDER READY
   
   Restaurant taps "Ready for Pickup"
   
   - Rider notified: "Head to restaurant now"
   - Customer notified: "Your order is ready!"
           │
           ▼
5. RIDER PICKS UP
   
   Rider arrives, shows OTP
   Restaurant verifies, hands over food
   Rider taps "Picked Up"


MENU MANAGEMENT:

Restaurant can:
  - Mark items as "Out of Stock" (hides from app)
  - Update prices
  - Add new items (requires approval)
  - Set special offers
  
Changes reflect in:
  - Elasticsearch (search)
  - Redis cache (invalidated)
  - App (next refresh)


TEMPORARILY PAUSE ORDERS:

If kitchen overwhelmed:
  POST /restaurant/availability
  { "is_accepting": false, "resume_at": "21:00" }
  
  - Restaurant hidden from search
  - Existing orders still processed
  - Auto-resume at specified time
```

---

## Flow 8: Rider Earnings & Incentives

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              RIDER EARNINGS                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

EARNING COMPONENTS:

Per Order:
  ┌────────────────────────────────────────┐
  │ Base Pay (pickup)        ₹10          │
  │ Distance Pay             ₹5/km        │
  │ Wait Time Pay            ₹2/min       │
  │ Surge Bonus              Variable     │
  │ Tip                      Variable     │
  │ ────────────────────────────────────  │
  │ Example Order (5km):                  │
  │   Base: ₹10                           │
  │   Distance: 5 × ₹5 = ₹25              │
  │   Surge 1.5×: ₹17.50                  │
  │   Tip: ₹20                            │
  │   Total: ₹72.50                       │
  └────────────────────────────────────────┘


INCENTIVE STRUCTURES:

1. DAILY QUEST
   "Complete 10 orders today → Earn ₹100 bonus"
   
   Progressive:
     5 orders  → ₹25
     10 orders → ₹100 (additional ₹75)
     15 orders → ₹200 (additional ₹100)

2. PEAK HOUR BONUS
   "1.5× on all orders between 12-2 PM"
   
   Targets lunch rush supply shortage

3. RAIN BONUS
   Weather API detects rain
   Automatically activate bonus:
   "₹10 extra per order (Rain bonus)"

4. STREAK BONUS
   "Complete 5 orders in a row without rejection → ₹50 bonus"
   
   Improves acceptance rate

5. WEEKLY TARGET
   "Complete 50 orders this week → ₹500 bonus"


GAMIFICATION:

Rider tiers:
  Bronze → Silver (100 deliveries) → Gold (500) → Platinum (1000)
  
Benefits by tier:
  - Priority order assignment
  - Higher base pay
  - Insurance coverage
  - Flexible cash withdrawal
```

---

# 7. TECHNICAL DEEP DIVES

## 7.1 Geospatial Queries

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              GEOSPATIAL IMPLEMENTATION                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

REDIS GEO for Real-Time Queries:

# Add rider location
GEOADD riders:geo:bangalore 77.5946 12.9716 "rider_D1"

# Find riders within 3km of restaurant
GEORADIUS riders:geo:bangalore 77.6000 12.9800 3 km WITHDIST

Result:
  1) "rider_D1" - 1.2 km
  2) "rider_D5" - 2.1 km


ELASTICSEARCH for Restaurant Search:

Mapping:
{
  "mappings": {
    "properties": {
      "location": { "type": "geo_point" },
      "cuisines": { "type": "keyword" },
      "rating": { "type": "float" }
    }
  }
}

Query: Nearby + Filters
{
  "query": {
    "bool": {
      "must": [
        { "terms": { "cuisines": ["pizza", "italian"] } },
        { "range": { "rating": { "gte": 4.0 } } }
      ],
      "filter": {
        "geo_distance": {
          "distance": "5km",
          "location": { "lat": 12.97, "lon": 77.59 }
        }
      }
    }
  },
  "sort": [
    { "_geo_distance": { "location": { "lat": 12.97, "lon": 77.59 } } }
  ]
}
```

---

## 7.2 ETA Calculation

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              ETA CALCULATION                                                        │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

COMPONENTS:

total_eta = prep_time + rider_to_restaurant + restaurant_to_customer

1. PREP TIME
   - Base: Restaurant's average prep time (historical)
   - Adjusted: Current order volume in kitchen
   - If 10 pending orders: add 5-10 min
   
2. RIDER TO RESTAURANT
   - Distance-based estimate
   - Traffic conditions (Google Maps API or internal)
   - Time of day adjustments
   
3. RESTAURANT TO CUSTOMER
   - Calculated when rider assigned
   - Real-time traffic
   - Weather conditions


DYNAMIC ETA UPDATES:

Every location ping (3 sec):
  1. Get rider's current position
  2. Calculate remaining distance
  3. Apply current traffic multiplier
  4. Update ETA if changed by > 1 min
  5. Push to customer via WebSocket


ML MODEL FOR PREP TIME:

Features:
  - Restaurant ID (some are faster)
  - Items ordered (biryani takes longer than sandwich)
  - Current pending orders
  - Day of week, time of day
  - Historical data

Output: Predicted prep time (minutes)
```

---

## 7.3 Handling Peak Load

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              HANDLING PEAK (50K orders/min)                                         │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

STRATEGIES:

1. QUEUE-BASED ORDER PROCESSING
   
   Order placed → Kafka → Order Processor (async)
   
   Benefits:
     - Handle burst
     - Process at sustainable rate
     - No dropped orders
   
2. SHARD BY CITY
   
   Each city is independent:
     - Separate Kafka partitions
     - Separate Redis instances
     - Separate DB shards
   
   Bangalore surge doesn't affect Mumbai
   
3. GRACEFUL DEGRADATION
   
   If overloaded:
     - Disable recommendations (non-critical)
     - Simplify search (pre-computed lists)
     - Queue less urgent notifications
   
4. RATE LIMITING
   
   Per-user limits:
     - 10 orders per hour
     - 3 concurrent active orders
   
   Prevents abuse and reduces load
```

---

# 8. EDGE CASES

## Order Cancellation

```
CANCELLATION POLICIES:

Before restaurant accepts: Free cancellation
After restaurant starts: Partial refund
After pickup: No refund (rider paid)

FLOW:
1. Customer requests cancellation
2. Check current status
3. Calculate refund amount
4. Process refund (async)
5. Notify restaurant (stop prep)
6. Notify rider (if assigned)
7. Free up rider for new orders
```

## Rider Issues

```
RIDER CANCELS AFTER ACCEPTING:
  1. Immediately reassign to next best rider
  2. Track rider cancellation rate
  3. Penalize (reduce priority) if frequent
  4. Notify customer with updated ETA

RIDER UNREACHABLE:
  1. Detect no location updates for 5+ minutes
  2. Call rider
  3. If no response: Reassign order
  4. Mark rider as "offline"

FOOD NOT DELIVERED:
  1. Customer reports issue
  2. Check rider's location history
  3. Investigate + Refund if legitimate
  4. Action against rider if fraud
```

---

# 9. TECHNOLOGY STACK

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SWIGGY TECH STACK                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

│ Component              │ Technology                    │ Why                              │
├────────────────────────┼───────────────────────────────┼──────────────────────────────────┤
│ API Gateway            │ Kong / AWS API Gateway        │ Rate limiting, auth              │
│ API Servers            │ Java / Go / Node.js           │ High performance                 │
│                        │                               │                                  │
│ Restaurant/Menu DB     │ PostgreSQL                    │ ACID, complex queries            │
│ Orders DB              │ Cassandra                     │ High write, time-series          │
│ Location History       │ Cassandra / TimescaleDB       │ Time-series, high volume         │
│ Search                 │ Elasticsearch                 │ Geo search, full-text            │
│ Cache                  │ Redis (with Geo)              │ Sessions, geo, real-time         │
│                        │                               │                                  │
│ Message Queue          │ Kafka                         │ Event-driven, high throughput    │
│ Real-time              │ WebSocket (Socket.io)         │ Live updates                     │
│ Maps                   │ Google Maps / Mapbox          │ Routing, ETA                     │
│                        │                               │                                  │
│ Payment                │ Razorpay / Paytm              │ UPI, cards, wallets              │
│ SMS                    │ Twilio / MSG91                │ OTP, notifications               │
│ Push                   │ FCM / APNS                    │ Mobile notifications             │
│                        │                               │                                  │
│ Container              │ Kubernetes                    │ Orchestration                    │
│ Monitoring             │ Prometheus / Datadog          │ Metrics, alerts                  │
└────────────────────────┴───────────────────────────────┴──────────────────────────────────┘
```

---

# 10. INTERVIEW TALKING POINTS

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              KEY DESIGN DECISIONS                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

1. WHY REDIS GEO FOR RIDER LOCATION?
   - O(log N) for geo queries
   - In-memory = sub-millisecond
   - Built-in radius search
   - Updates every 3 seconds sustainable

2. WHY KAFKA FOR ORDER EVENTS?
   - Decouples services
   - Handles peak burst
   - Multiple consumers (notifications, analytics, assignment)
   - Replay capability for debugging

3. HOW RIDER ASSIGNMENT WORKS?
   - Geo query → Nearby riders
   - Score by proximity + rating + fairness
   - Offer with timeout → Cascade if rejected
   - Order batching for efficiency

4. HOW SURGE PRICING?
   - Calculate demand/supply ratio per zone
   - Update every 5 minutes
   - Store in Redis with TTL
   - Cap multiplier to protect customers

5. WHY WEBSOCKET FOR TRACKING?
   - Push model (server → client)
   - No polling overhead
   - Real-time ETA updates
   - Connection manager for scale

6. ORDER vs RIDER CONSISTENCY?
   - Orders: Strong (no duplicate orders)
   - Rider location: Eventual (3 sec delay OK)
   - Assignment: Optimistic (might fail, retry)

7. HANDLING 500K CONCURRENT RIDERS?
   - Shard by city (independent instances)
   - Kafka for location ingestion
   - Redis Geo per city cluster
   - Location updates batched (every 3 sec, not 1 sec)
```

---

# 11. SWIGGY vs UBER: KEY DIFFERENCES

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SWIGGY vs UBER COMPARISON                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

│ Aspect               │ UBER                          │ SWIGGY                          │
├──────────────────────┼───────────────────────────────┼─────────────────────────────────┤
│ Parties involved     │ 2 (Driver ↔ Rider)            │ 3 (Restaurant ↔ Rider ↔ Customer)
│                      │                               │                                 │
│ ETA components       │ Just travel time              │ Prep time + Pickup + Delivery  │
│                      │                               │                                 │
│ Assignment timing    │ Immediate (when requested)    │ Delayed (after restaurant accepts)
│                      │                               │                                 │
│ Order batching       │ Carpooling (unusual)          │ Very common (same restaurant)  │
│                      │                               │                                 │
│ Inventory            │ No inventory                  │ Menu availability, stock        │
│                      │                               │                                 │
│ Prep wait            │ None                          │ Rider waits at restaurant       │
│                      │                               │                                 │
│ Search               │ Location → Location           │ Location → Restaurants → Items │
│                      │                               │                                 │
│ Peak handling        │ Surge + more drivers          │ Surge + pause accepting orders │
│                      │                               │                                 │
│ Failure impact       │ Passenger waits               │ Food gets cold, wastage         │
└──────────────────────┴───────────────────────────────┴─────────────────────────────────┘
```

---

# 12. QUICK REFERENCE

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    SWIGGY / FOOD DELIVERY CHEAT SHEET                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

RESTAURANT DISCOVERY:
  • Elasticsearch + Geo for search
  • Redis Geo for real-time availability
  • Personalization via order history

CART:
  • Single restaurant only
  • Redis primary, DB backup
  • Price snapshot on add

ORDER FLOW:
  Restaurant accepts → Rider assigned → Picked up → Delivered

RIDER ASSIGNMENT:
  • Redis Geo for nearby riders
  • Score = proximity + rating + fairness
  • Offer → Timeout → Next rider
  • Order batching for efficiency

LOCATION TRACKING:
  • GPS every 3 seconds
  • Kafka → Redis Geo → WebSocket
  • ETA recalculated on each update

SURGE PRICING:
  • Per-zone calculation
  • demand/supply ratio
  • Updates every 5 minutes
  • Stored in Redis with TTL

SCALE STRATEGIES:
  • Shard by city
  • Kafka for burst handling
  • Graceful degradation
  • Rate limiting per user
```

---
