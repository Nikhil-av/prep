# Amazon E-commerce — Complete Deep Dive

> Interview-ready documentation with all details — Covers Flipkart, Myntra, any E-commerce

---

# 1. FUNCTIONAL REQUIREMENTS

## Priority Levels
- **P0** = Must have (core functionality)
- **P1** = Should have (important features)
- **P2** = Nice to have (enhancements)

## Feature List

| # | Feature | Priority | Description |
|---|---------|----------|-------------|
| 1 | **Product Catalog** | P0 | Browse, search, filter products |
| 2 | **Product Search** | P0 | Full-text search with filters |
| 3 | **Product Detail Page** | P0 | Images, specs, pricing, availability |
| 4 | **Shopping Cart** | P0 | Add, remove, update quantities |
| 5 | **User Authentication** | P0 | Login, signup, sessions |
| 6 | **Checkout & Payment** | P0 | Address, payment, order placement |
| 7 | **Order Management** | P0 | Order status, tracking, history |
| 8 | **Inventory Management** | P0 | Stock levels, warehouse allocation |
| 9 | **Reviews & Ratings** | P1 | User reviews, star ratings |
| 10 | **Wishlist** | P1 | Save items for later |
| 11 | **Seller Marketplace** | P1 | Multi-vendor platform |
| 12 | **Recommendations** | P1 | "You may also like", "Frequently bought together" |
| 13 | **Flash Sales / Deals** | P2 | Time-limited offers, lightning deals |
| 14 | **Returns & Refunds** | P1 | Return requests, refund processing |
| 15 | **Notifications** | P1 | Order updates, deals, price drops |

---

# 2. NON-FUNCTIONAL REQUIREMENTS

## Latency

| Operation | Target | Rationale |
|-----------|--------|-----------|
| Product search | < 200ms | Interactive typing |
| Product page load | < 300ms | First impression |
| Add to cart | < 100ms | Must feel instant |
| Checkout | < 1 sec | Critical path |
| Payment processing | < 3 sec | Industry standard |
| Order confirmation | < 500ms | User waiting |

## Throughput

| Metric | Normal | Peak (Sale Events) |
|--------|--------|-------------------|
| Daily Active Users | 100 million | 300 million |
| Product views/day | 1 billion | 5 billion |
| Orders/day | 10 million | 50 million |
| Orders/second (peak) | 500 | 5,000 |
| Cart operations/sec | 10,000 | 100,000 |

## Availability

| Component | Target | Strategy |
|-----------|--------|----------|
| Product catalog | 99.99% | Read replicas, CDN |
| Cart service | 99.99% | Multi-region, eventual consistency OK |
| Checkout/Payment | 99.999% | CRITICAL — zero downtime |
| Order service | 99.99% | Multi-region, async processing |

## Consistency

| Data Type | Consistency Level | Why |
|-----------|-------------------|-----|
| Product catalog | Eventual (minutes OK) | Can tolerate stale prices briefly |
| Inventory | Strong (for checkout) | Avoid overselling |
| Cart | Eventual | Can merge conflicts |
| Orders | Strong | Financial transaction |
| Payments | Strong | Money involved |
| User accounts | Strong | Security critical |

---

# 3. CAPACITY PLANNING

## Step-by-Step Calculation

### Step 1: Define Scale

```
Daily Active Users:          100 million (normal), 300M (sale)
Products in catalog:         500 million SKUs
Orders/day:                   10 million (normal), 50M (sale)
Average order value:         $50
Product images/product:       10 images
Average cart size:            5 items
```

---

### Step 2: Storage Calculation

**Product Catalog (PostgreSQL/Cassandra):**
```
Products:                    500 million
Per product metadata:        5 KB (title, description, specs)
Total:                       500M × 5 KB = 2.5 TB

With indexes and replicas:   ~10 TB
```

**Product Images (S3):**
```
Products:                    500 million
Images per product:          10
Average image size:          500 KB (compressed)
Total:                       500M × 10 × 500 KB = 2.5 PB

With multiple resolutions (3×): ~7.5 PB
```

**Orders (Cassandra):**
```
Orders/day:                  10 million
Order record size:           2 KB
Daily:                       20 GB/day
Yearly:                      7.3 TB/year
With 3-year retention:       ~25 TB
```

**Inventory (PostgreSQL/Redis):**
```
Products:                    500 million
Warehouses:                  100
Inventory records:           500M × 100 = 50 billion
Per record:                  50 bytes
Total:                       2.5 TB
```

---

### Step 3: Server Estimation

**API Servers:**
```
Requests/sec (peak):         100,000
Per server:                  5,000 req/sec
Servers needed:              20 servers
With redundancy (3×):        60 API servers
```

**Search Service:**
```
Search queries/sec:          20,000
Elasticsearch cluster:       50 nodes
```

**Cart Service:**
```
Cart operations/sec:         100,000 (peak)
Per server:                  10,000 ops/sec
Servers:                     10 servers (+ replicas)
```

**Order Service:**
```
Orders/sec (peak):           5,000
Processing per order:        200ms
Servers:                     20 servers
```

---

### Quick Reference: Capacity Cheat Sheet

```
┌────────────────────────────────────────────────────────────────────────┐
│                    AMAZON CAPACITY CHEAT SHEET                         │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  SCALE                                                                 │
│  • DAU: 100M (normal), 300M (sale)                                    │
│  • Products: 500M SKUs                                                 │
│  • Orders/day: 10M (normal), 50M (sale)                               │
│  • Orders/sec (peak): 5,000                                            │
│                                                                        │
│  STORAGE                                                               │
│  • Product catalog: 10 TB                                              │
│  • Product images: 7.5 PB                                              │
│  • Orders: 25 TB (3 years)                                             │
│  • Inventory: 2.5 TB                                                   │
│                                                                        │
│  SERVERS                                                               │
│  • API: 60 servers                                                     │
│  • Search: 50 Elasticsearch nodes                                      │
│  • Cart: 10 servers                                                    │
│  • Order: 20 servers                                                   │
│  • Payment: 15 servers                                                 │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

# 4. DETAILED HLD DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    AMAZON E-COMMERCE ARCHITECTURE                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                           CLIENTS
                    ┌─────────────────────────────────────────────────────────┐
                    │      iOS App              Android App          Web      │
                    │         │                       │                │      │
                    └─────────┼───────────────────────┼────────────────┼──────┘
                              │                       │                │
                              ▼                       ▼                ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │                    CDN (CloudFront)                     │
                    │                                                         │
                    │   - Product images                                      │
                    │   - Static assets (JS, CSS)                             │
                    │   - Cached product pages                                │
                    └─────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │                    LOAD BALANCER                        │
                    │                   (AWS ALB / Nginx)                     │
                    │                                                         │
                    │   - Rate limiting          - SSL termination            │
                    │   - Geographic routing     - Health checks              │
                    └─────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────────────────────────────────────────────┐
                    │                    API GATEWAY                          │
                    │                                                         │
                    │   - Authentication (JWT)                                │
                    │   - Request routing                                     │
                    │   - Rate limiting per user                              │
                    │   - Request/Response transformation                     │
                    └─────────────────────────────────────────────────────────┘
                              │
           ┌──────────────────┼──────────────────────────────────────────────┐
           │                  │                                              │
           ▼                  ▼                                              ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    MICROSERVICES LAYER                                              │
├─────────────────────┬─────────────────────┬─────────────────────┬───────────────────────────────────┤
│  USER SERVICE       │  PRODUCT SERVICE    │  SEARCH SERVICE     │  CART SERVICE                    │
│  [20 instances]     │  [30 instances]     │  [50 ES nodes]      │  [15 instances]                  │
│                     │                     │                     │                                   │
│  - Auth/Login       │  - Product CRUD     │  - Full-text search │  - Add/remove items              │
│  - User profiles    │  - Categories       │  - Filters          │  - Update quantities             │
│  - Addresses        │  - Pricing          │  - Autocomplete     │  - Guest cart → User merge       │
│  - Payment methods  │  - Seller catalog   │  - Faceted search   │  - Cart persistence              │
├─────────────────────┼─────────────────────┼─────────────────────┼───────────────────────────────────┤
│  INVENTORY SERVICE  │  ORDER SERVICE      │  PAYMENT SERVICE    │  SHIPPING SERVICE                │
│  [25 instances]     │  [20 instances]     │  [15 instances]     │  [10 instances]                  │
│                     │                     │                     │                                   │
│  - Stock levels     │  - Order creation   │  - Payment gateway  │  - Carrier selection             │
│  - Warehouse alloc  │  - Order status     │  - Refunds          │  - Rate calculation              │
│  - Reservations     │  - Order history    │  - Wallet           │  - Label generation              │
│  - Low stock alerts │  - Returns          │  - EMI/BNPL         │  - Tracking                      │
├─────────────────────┼─────────────────────┼─────────────────────┼───────────────────────────────────┤
│  SELLER SERVICE     │  REVIEW SERVICE     │  RECOMMENDATION     │  NOTIFICATION SERVICE            │
│  [10 instances]     │  [10 instances]     │  [20 instances]     │  [15 instances]                  │
│                     │                     │                     │                                   │
│  - Seller onboard   │  - Submit reviews   │  - "You may like"   │  - Order updates                 │
│  - Seller products  │  - Ratings          │  - "Bought together"│  - Price drop alerts             │
│  - Seller payouts   │  - Moderation       │  - Personalization  │  - Deal notifications            │
│  - Analytics        │  - Helpfulness      │  - ML ranking       │  - Push/Email/SMS                │
└─────────────────────┴─────────────────────┴─────────────────────┴───────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    CACHE LAYER (REDIS)                                              │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│   PRODUCT CACHE:                           SESSION/AUTH:                                           │
│   product:{id} = {...}                     session:{token} = {user_id, ...}                       │
│   product:{id}:price = 999                                                                         │
│                                            CART CACHE:                                              │
│   INVENTORY CACHE:                         cart:{user_id} = [{product_id, qty}, ...]              │
│   inventory:{product_id}:{warehouse} = 50  cart:guest:{session_id} = [...]                        │
│   inventory:{product_id}:total = 500                                                               │
│                                            RATE LIMITING:                                           │
│   HOT PRODUCTS:                            rate:{user_id}:{action} = count                        │
│   trending:today = [P1, P2, P3]            flash_sale:{id}:remaining = 1000                       │
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
│   │ • users             │   │ • orders            │   │ • products index    │                      │
│   │ • products          │   │ • order_items       │   │ • sellers index     │                      │
│   │ • inventory         │   │ • reviews           │   │ • reviews index     │                      │
│   │ • sellers           │   │ • user_activity     │   │                     │                      │
│   │ • categories        │   │ • notifications     │   │ Facets:             │                      │
│   │ • payments          │   │                     │   │ • brand             │                      │
│   │                     │   │ WHY:                │   │ • price range       │                      │
│   │ WHY:                │   │ • Order history     │   │ • category          │                      │
│   │ • ACID for money    │   │ • High write volume │   │ • rating            │                      │
│   │ • Complex queries   │   │ • Time-series data  │   │ • availability      │                      │
│   │ • Inventory locks   │   │                     │   │                     │                      │
│   └─────────────────────┘   └─────────────────────┘   └─────────────────────┘                      │
│                                                                                                     │
│   SHARDING STRATEGY:                                                                                │
│   ┌───────────────────────┬──────────────────────┬────────────────────────────────────────────────┐ │
│   │  DATA TYPE            │  SHARD KEY           │  WHY                                           │ │
│   ├───────────────────────┼──────────────────────┼────────────────────────────────────────────────┤ │
│   │  Products             │  category_id         │  Products in same category on same shard      │ │
│   │  Orders               │  user_id             │  User's order history on same shard           │ │
│   │  Inventory            │  warehouse_id        │  Warehouse inventory on same shard            │ │
│   │  Reviews              │  product_id          │  Product reviews on same shard                │ │
│   │  Users                │  hash(user_id)       │  Uniform distribution                         │ │
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
│   order-events                                Inventory Service                                    │
│     - Order placed                              - Decrement stock                                  │
│     - Order cancelled                           - Release reservation                              │
│     - Order returned                                                                                │
│                                               Payment Service                                       │
│   inventory-events                              - Process refunds                                  │
│     - Stock updated                                                                                 │
│     - Low stock alert                         Notification Service                                 │
│     - Restock notification                      - Email/SMS/Push                                   │
│                                                 - Order status updates                             │
│   payment-events                                                                                    │
│     - Payment success                         Analytics Service                                    │
│     - Payment failed                            - Sales metrics                                    │
│     - Refund processed                          - Conversion tracking                              │
│                                                                                                     │
│   search-index-events                         Search Indexer                                       │
│     - Product created/updated                   - Update Elasticsearch                             │
│     - Price changed                                                                                 │
│     - Stock changed                           Recommendation Service                               │
│                                                 - Update "bought together"                         │
│   user-activity-events                          - Personalization                                  │
│     - Product viewed                                                                                │
│     - Added to cart                           Seller Service                                       │
│     - Purchase completed                        - Sales reports                                    │
│                                                 - Payout calculations                              │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    EXTERNAL SERVICES                                                │
├─────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                     │
│   PAYMENT GATEWAYS:                           SHIPPING CARRIERS:                                   │
│     - Stripe / Razorpay                         - FedEx, UPS, USPS                                │
│     - PayPal                                    - Delhivery, BlueDart                             │
│     - UPI (India)                               - Internal logistics                              │
│     - Credit/Debit cards                                                                            │
│                                               SMS/EMAIL:                                           │
│   FRAUD DETECTION:                              - Twilio / SNS                                     │
│     - ML-based scoring                          - SendGrid / SES                                   │
│     - Address verification                                                                          │
│     - Velocity checks                         MAPS:                                                │
│                                                 - Google Maps API                                  │
│                                                 - Address validation                               │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

# 5. DATABASE SCHEMA

## Core Tables

### Products

```sql
-- PostgreSQL
CREATE TABLE products (
    product_id      UUID PRIMARY KEY,
    seller_id       UUID NOT NULL REFERENCES sellers(seller_id),
    category_id     UUID NOT NULL REFERENCES categories(category_id),
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    brand           VARCHAR(200),
    base_price      DECIMAL(10,2) NOT NULL,
    sale_price      DECIMAL(10,2),
    currency        VARCHAR(3) DEFAULT 'USD',
    status          VARCHAR(20) DEFAULT 'active', -- active, inactive, deleted
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Product variants (sizes, colors)
CREATE TABLE product_variants (
    variant_id      UUID PRIMARY KEY,
    product_id      UUID NOT NULL REFERENCES products(product_id),
    sku             VARCHAR(100) UNIQUE NOT NULL,
    variant_name    VARCHAR(200),  -- "Red, Large"
    attributes      JSONB,         -- {"color": "red", "size": "L"}
    price_modifier  DECIMAL(10,2) DEFAULT 0,
    weight_grams    INTEGER,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Product images
CREATE TABLE product_images (
    image_id        UUID PRIMARY KEY,
    product_id      UUID NOT NULL REFERENCES products(product_id),
    variant_id      UUID REFERENCES product_variants(variant_id),
    image_url       VARCHAR(500) NOT NULL,
    thumbnail_url   VARCHAR(500),
    display_order   INTEGER DEFAULT 0,
    is_primary      BOOLEAN DEFAULT FALSE
);
```

### Inventory

```sql
-- Inventory per warehouse
CREATE TABLE inventory (
    inventory_id    UUID PRIMARY KEY,
    variant_id      UUID NOT NULL REFERENCES product_variants(variant_id),
    warehouse_id    UUID NOT NULL REFERENCES warehouses(warehouse_id),
    quantity        INTEGER NOT NULL DEFAULT 0,
    reserved        INTEGER NOT NULL DEFAULT 0,  -- Reserved during checkout
    reorder_level   INTEGER DEFAULT 10,
    updated_at      TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(variant_id, warehouse_id)
);

-- Inventory reservations (during checkout)
CREATE TABLE inventory_reservations (
    reservation_id  UUID PRIMARY KEY,
    variant_id      UUID NOT NULL,
    warehouse_id    UUID NOT NULL,
    quantity        INTEGER NOT NULL,
    order_id        UUID,  -- NULL until order placed
    session_id      VARCHAR(100),  -- For guest checkout
    status          VARCHAR(20) DEFAULT 'pending', -- pending, confirmed, released
    expires_at      TIMESTAMP NOT NULL,  -- Auto-release after 15 min
    created_at      TIMESTAMP DEFAULT NOW()
);
```

### Cart

```sql
-- Cart (can use Redis, but also persist to DB)
CREATE TABLE carts (
    cart_id         UUID PRIMARY KEY,
    user_id         UUID REFERENCES users(user_id),
    session_id      VARCHAR(100),  -- For guest users
    status          VARCHAR(20) DEFAULT 'active', -- active, converted, abandoned
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE cart_items (
    cart_item_id    UUID PRIMARY KEY,
    cart_id         UUID NOT NULL REFERENCES carts(cart_id),
    variant_id      UUID NOT NULL REFERENCES product_variants(variant_id),
    quantity        INTEGER NOT NULL DEFAULT 1,
    price_at_add    DECIMAL(10,2) NOT NULL,  -- Snapshot of price when added
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(cart_id, variant_id)
);
```

### Orders

```sql
-- Cassandra for orders (high write volume, partitioned by user)
CREATE TABLE orders (
    user_id         UUID,
    order_id        UUID,
    order_number    TEXT,          -- Human-readable: "ORD-2024-001234"
    status          TEXT,          -- placed, confirmed, processing, shipped, delivered, cancelled
    subtotal        DECIMAL,
    tax             DECIMAL,
    shipping_fee    DECIMAL,
    discount        DECIMAL,
    total           DECIMAL,
    currency        TEXT,
    shipping_address FROZEN<address_type>,
    billing_address  FROZEN<address_type>,
    payment_method  TEXT,
    payment_status  TEXT,          -- pending, paid, failed, refunded
    created_at      TIMESTAMP,
    updated_at      TIMESTAMP,
    
    PRIMARY KEY ((user_id), order_id)
) WITH CLUSTERING ORDER BY (order_id DESC);

-- Order items
CREATE TABLE order_items (
    order_id        UUID,
    item_id         UUID,
    variant_id      UUID,
    product_title   TEXT,          -- Snapshot
    variant_name    TEXT,          -- Snapshot
    quantity        INT,
    unit_price      DECIMAL,
    total_price     DECIMAL,
    status          TEXT,          -- confirmed, shipped, delivered, returned
    tracking_number TEXT,
    
    PRIMARY KEY ((order_id), item_id)
);

-- Order status history (for tracking)
CREATE TABLE order_status_history (
    order_id        UUID,
    timestamp       TIMESTAMP,
    status          TEXT,
    description     TEXT,
    updated_by      TEXT,          -- system, admin, seller
    
    PRIMARY KEY ((order_id), timestamp)
) WITH CLUSTERING ORDER BY (timestamp DESC);
```

### Users & Sellers

```sql
-- Users
CREATE TABLE users (
    user_id         UUID PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    phone           VARCHAR(20),
    password_hash   VARCHAR(255) NOT NULL,
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    status          VARCHAR(20) DEFAULT 'active',
    created_at      TIMESTAMP DEFAULT NOW()
);

-- User addresses
CREATE TABLE user_addresses (
    address_id      UUID PRIMARY KEY,
    user_id         UUID NOT NULL REFERENCES users(user_id),
    label           VARCHAR(50),   -- "Home", "Office"
    address_line1   VARCHAR(200) NOT NULL,
    address_line2   VARCHAR(200),
    city            VARCHAR(100) NOT NULL,
    state           VARCHAR(100),
    postal_code     VARCHAR(20) NOT NULL,
    country         VARCHAR(50) NOT NULL,
    phone           VARCHAR(20),
    is_default      BOOLEAN DEFAULT FALSE
);

-- Sellers
CREATE TABLE sellers (
    seller_id       UUID PRIMARY KEY,
    business_name   VARCHAR(200) NOT NULL,
    email           VARCHAR(255) UNIQUE NOT NULL,
    phone           VARCHAR(20),
    status          VARCHAR(20) DEFAULT 'pending', -- pending, approved, suspended
    rating          DECIMAL(2,1) DEFAULT 0,
    total_sales     INTEGER DEFAULT 0,
    commission_rate DECIMAL(4,2) DEFAULT 10.00,  -- 10%
    bank_details    JSONB,
    created_at      TIMESTAMP DEFAULT NOW()
);
```

---

# 6. REQUEST FLOWS

## Flow 1: Product Search

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              PRODUCT SEARCH FLOW                                                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User searches "iPhone 15 Pro"
           │
           ▼
1. API GATEWAY
   - Rate limit check
   - Auth (optional for search)
           │
           ▼
2. SEARCH SERVICE
   
   Query Elasticsearch:
   
   POST /products/_search
   {
     "query": {
       "bool": {
         "must": [
           {
             "multi_match": {
               "query": "iPhone 15 Pro",
               "fields": ["title^3", "description", "brand^2"]
             }
           }
         ],
         "filter": [
           { "term": { "status": "active" } },
           { "range": { "inventory_count": { "gt": 0 } } }
         ]
       }
     },
     "aggs": {
       "brands": { "terms": { "field": "brand" } },
       "price_ranges": { "range": { "field": "price", "ranges": [...] } },
       "ratings": { "terms": { "field": "rating" } }
     }
   }
           │
           ▼
3. RANKING & BOOSTING
   
   Boost factors:
     - Relevance score (default ES)
     - Sales velocity (last 30 days)
     - Rating (4.5+ boosted)
     - Seller performance
     - Sponsored/Ads (paid boost)
           │
           ▼
4. RESPONSE WITH FACETS
   
   {
     "products": [...],
     "facets": {
       "brands": ["Apple", "Samsung", ...],
       "price_ranges": ["$500-1000", "$1000-1500"],
       "ratings": [5, 4, 3]
     },
     "total": 1234,
     "page": 1
   }


AUTOCOMPLETE (Typeahead):

As user types:
1. Query prefix: "iph" → ["iphone", "iphone 15", "iphone case"]
2. Use Elasticsearch "completion" suggester
3. Cache popular queries in Redis
4. Personalize based on user history
```

---

## Flow 2: Product Detail Page

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              PRODUCT DETAIL PAGE FLOW                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User clicks on product
           │
           ▼
1. PARALLEL REQUESTS (Frontend makes multiple calls)
   
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │  Product    │  │  Inventory  │  │  Reviews    │  │  Recommend  │
   │  Details    │  │  Check      │  │  Summary    │  │  -ations    │
   └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
   
2. PRODUCT SERVICE (Cache-first)
   
   Check Redis: product:{id}
   
   Cache HIT → Return
   Cache MISS → Query PostgreSQL → Cache → Return
   
   Response:
   {
     product_id, title, description, brand,
     price, sale_price, images: [...],
     variants: [...], attributes: {...}
   }
           │
           ▼
3. INVENTORY SERVICE
   
   Check: Can deliver to user's pincode?
   
   a) Get user's location (from profile or IP)
   b) Find nearest warehouses with stock
   c) Calculate delivery estimate
   
   Response:
   {
     in_stock: true,
     quantity_available: 50,
     delivery_estimate: "Tomorrow by 9 PM",
     nearest_warehouse: "BLR-01"
   }
           │
           ▼
4. REVIEW SERVICE
   
   Query Cassandra: reviews_by_product
   
   Aggregate:
   {
     average_rating: 4.5,
     total_reviews: 1234,
     rating_distribution: {5: 800, 4: 300, ...},
     top_reviews: [...]
   }
           │
           ▼
5. RECOMMENDATION SERVICE
   
   Get personalized recommendations:
   
   {
     "frequently_bought_together": [...],
     "similar_products": [...],
     "customers_also_viewed": [...]
   }
           │
           ▼
6. LOG USER ACTIVITY (Async - Kafka)
   
   Publish: user-activity-events
   { user_id, product_id, event: "view", timestamp }
   
   → Used for recommendations, analytics
```

---

## Flow 3: Add to Cart

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              ADD TO CART FLOW                                                       │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User clicks "Add to Cart"
           │
           ▼
1. VALIDATE REQUEST
   - Product exists?
   - Variant valid?
   - Quantity available?
           │
           ▼
2. CHECK INVENTORY (Soft check, not reservation)
   
   Redis: inventory:{variant_id}:total
   
   If quantity < requested → Error: "Only X left"
           │
           ▼
3. UPDATE CART (Redis + Async DB)
   
   a) Get/Create cart for user
   
      Logged in: cart:{user_id}
      Guest: cart:guest:{session_id}
   
   b) Add item to cart
   
      HSET cart:{user_id} {variant_id} {
        quantity: 1,
        price: 999,
        added_at: timestamp
      }
   
   c) Update cart metadata
   
      cart:{user_id}:updated_at = now()
           │
           ▼
4. ASYNC PERSIST TO DATABASE
   
   Kafka → Cart DB Writer → PostgreSQL (carts, cart_items)
   
   Why async?
     - Cart is read-heavy, write-light
     - Eventual consistency is fine
     - Redis is source of truth for active carts
           │
           ▼
5. RESPONSE
   
   {
     success: true,
     cart: {
       items: [...],
       subtotal: 999,
       item_count: 1
     }
   }


GUEST TO USER CART MERGE:

When guest logs in:
1. Get guest cart: cart:guest:{session_id}
2. Get user cart: cart:{user_id}
3. Merge:
   - Same item in both → Take higher quantity
   - Different items → Add all
4. Delete guest cart
5. Return merged cart
```

---

## Flow 4: Checkout & Order Placement

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              CHECKOUT FLOW (CRITICAL PATH!)                                         │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User clicks "Proceed to Checkout"
           │
           ▼
1. PRE-CHECKOUT VALIDATION
   
   a) User logged in? (Redirect to login if not)
   b) Cart not empty?
   c) All items still in stock?
   d) Prices haven't changed significantly?
           │
           ▼
2. RESERVE INVENTORY (CRITICAL!)
   
   BEGIN TRANSACTION (PostgreSQL)
   
   FOR each item in cart:
     UPDATE inventory
     SET reserved = reserved + {quantity}
     WHERE variant_id = {id}
       AND warehouse_id = {nearest}
       AND (quantity - reserved) >= {quantity}  -- Check available
   
   IF any update fails:
     ROLLBACK
     Return error: "Item X is out of stock"
   
   INSERT INTO inventory_reservations (
     variant_id, warehouse_id, quantity,
     session_id, expires_at  -- 15 minutes
   )
   
   COMMIT
           │
           ▼
3. USER SELECTS ADDRESS & PAYMENT
   
   Frontend → Display saved addresses
            → Calculate shipping for each warehouse
            → Display payment options
           │
           ▼
4. CALCULATE ORDER TOTAL
   
   subtotal = SUM(item.price × item.quantity)
   tax = calculate_tax(subtotal, address.state)
   shipping = calculate_shipping(items, warehouse, address)
   discount = apply_coupons(subtotal, user_coupons)
   
   total = subtotal + tax + shipping - discount
           │
           ▼
5. PROCESS PAYMENT (CRITICAL!)
   
   a) Create pending order in DB
   
      INSERT INTO orders (
        order_id, user_id, status = 'pending',
        total, payment_status = 'pending'
      )
   
   b) Call Payment Gateway (Stripe/Razorpay)
   
      POST /payments/create
      {
        amount: total,
        currency: "USD",
        order_id: order_id,
        payment_method: "card_xxx"
      }
      
      Payment is IDEMPOTENT using order_id!
   
   c) Handle response:
   
      SUCCESS:
        Update order: status = 'confirmed', payment_status = 'paid'
        Confirm inventory reservation
        Publish to Kafka: order-events
      
      FAILURE:
        Update order: status = 'payment_failed'
        Release inventory reservation
        Return error to user
           │
           ▼
6. POST-ORDER PROCESSING (Async via Kafka)
   
   order-events topic → Multiple consumers:
   
   ├──► Inventory Service
   │      - Decrement actual stock
   │      - Remove reservation
   │
   ├──► Seller Service
   │      - Notify seller: "New order!"
   │      - Create packing slip
   │
   ├──► Notification Service
   │      - Email: "Order confirmed!"
   │      - SMS: "Your order #1234 is placed"
   │
   ├──► Analytics Service
   │      - Track conversion
   │      - Update user purchase history
   │
   └──► Recommendation Service
         - Update "frequently bought together"
         - Clear cart
           │
           ▼
7. RESPONSE TO USER
   
   {
     success: true,
     order_id: "ORD-2024-001234",
     estimated_delivery: "Wed, Feb 14th",
     tracking_url: "..."
   }
```

---

## Flow 5: Inventory Management

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              INVENTORY MANAGEMENT                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

INVENTORY CHECK FLOW:

1. FAST PATH (Redis)
   
   inventory:{variant_id}:total → Quick availability check
   Updated every few seconds via background sync

2. ACCURATE PATH (PostgreSQL)
   
   Used during checkout:
   
   SELECT SUM(quantity - reserved) as available
   FROM inventory
   WHERE variant_id = ?
   AND warehouse_id IN (warehouses near user)


RESERVATION SYSTEM:

Why reservations?
  - Prevent overselling during checkout
  - Handle cart abandonment gracefully

Reservation lifecycle:
  ┌──────────┐    ┌───────────┐    ┌───────────┐
  │ Created  │───►│ Confirmed │───►│ Fulfilled │
  │ (15 min) │    │ (Ordered) │    │ (Shipped) │
  └────┬─────┘    └───────────┘    └───────────┘
       │
       ▼ (if expired)
  ┌──────────┐
  │ Released │
  └──────────┘

Background job (every minute):
  SELECT * FROM inventory_reservations
  WHERE status = 'pending' AND expires_at < NOW()
  
  FOR each expired reservation:
    UPDATE inventory SET reserved = reserved - quantity
    UPDATE reservation SET status = 'released'


WAREHOUSE SELECTION (for fulfillment):

User in Bangalore, orders iPhone:

1. Find warehouses with stock:
   - BLR-01 (Bangalore): 50 units, distance 10 km
   - HYD-01 (Hyderabad): 200 units, distance 500 km
   - MUM-01 (Mumbai): 100 units, distance 1000 km

2. Score each warehouse:
   score = availability_score + proximity_score + capacity_score
   
3. Select best:
   - If BLR-01 has stock → Use BLR-01 (fastest delivery)
   - If not → Fall back to HYD-01

4. Reserve from selected warehouse
```

---

## Flow 6: Flash Sales / Lightning Deals

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              FLASH SALE HANDLING (High Concurrency!)                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

PROBLEM:
  - 10,000 units of iPhone
  - 1,000,000 users trying to buy at 12:00:00
  - Without control: Database will crash!

SOLUTION: Multi-layer protection

LAYER 1: FRONTEND RATE LIMITING
  
  - Queue users in virtual waiting room
  - Show countdown timer
  - Stagger requests over 1-2 minutes

LAYER 2: REDIS AS GATEKEEPER
  
  Sale starts:
  
  SET flash_sale:12345:remaining 10000
  
  User tries to add to cart:
  
  DECR flash_sale:12345:remaining
  
  If result >= 0:
    → Allowed! Proceed to cart
  Else:
    → Sold out! Return error
  
  This is ATOMIC and can handle 100K+ ops/sec!

LAYER 3: RESERVATION WITH TIMEOUT
  
  User gets through:
  1. Reserve item in Redis (10 min TTL)
  2. User must complete checkout in 10 min
  3. If abandoned → Item released back to pool

LAYER 4: DATABASE WRITES (Async)
  
  Actual inventory decrements happen async via Kafka
  
  Why?
    - Redis handles the burst
    - DB processes at sustainable rate
    - Eventually consistent but correct


FLOW:

User clicks "Buy Now" at 12:00:00
           │
           ▼
1. REDIS: DECR flash_sale:12345:remaining
           │
           ├── Result < 0 → "Sold out!" (immediate response)
           │
           ▼
2. REDIS: SET user:U123:flash_reservation:12345 {expires: 10min}
           │
           ▼
3. Add to cart (normal flow)
           │
           ▼
4. User must checkout within 10 minutes
           │
           ├── Checkout successful → Order placed
           │
           └── Timeout → Release reservation
                INCR flash_sale:12345:remaining
                DEL user:U123:flash_reservation:12345
```

---

## Flow 7: Order Status & Tracking

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              ORDER LIFECYCLE                                                        │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

ORDER STATES:

    ┌──────────┐
    │  PLACED  │──────────────────────┐
    └────┬─────┘                      │
         │                            │ (payment failed)
         ▼                            ▼
    ┌──────────┐                 ┌──────────┐
    │CONFIRMED │                 │ CANCELLED│
    └────┬─────┘                 └──────────┘
         │
         ▼
    ┌──────────┐
    │PROCESSING│ (Seller packing)
    └────┬─────┘
         │
         ▼
    ┌──────────┐
    │ SHIPPED  │ (Handed to carrier)
    └────┬─────┘
         │
         ▼
    ┌──────────┐    ┌──────────┐
    │OUT FOR   │───►│DELIVERED │
    │DELIVERY  │    └──────────┘
    └──────────┘


STATUS UPDATE FLOW:

Carrier API webhook → Shipping Service → Kafka → Consumers

webhook payload:
{
  tracking_number: "FEDEX123",
  status: "out_for_delivery",
  location: "Bangalore Hub",
  timestamp: "2024-02-07T10:30:00Z"
}
     │
     ▼
1. SHIPPING SERVICE
   
   - Validate webhook
   - Map carrier status to our status
   - Update order_status_history
     │
     ▼
2. PUBLISH TO KAFKA
   
   Topic: order-status-events
   { order_id, new_status, timestamp }
     │
     ▼
3. CONSUMERS
   
   ├──► Order Service
   │      Update order status in Cassandra
   │
   ├──► Notification Service
   │      "Your order is out for delivery!"
   │
   └──► Analytics
         Track delivery performance


USER TRACKING PAGE:

1. Load order details (Cassandra: orders)
2. Load status history (Cassandra: order_status_history)
3. Load real-time tracking (Carrier API)
4. Display timeline with map
```

---

## Flow 8: Returns & Refunds

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              RETURNS & REFUNDS FLOW                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

RETURN REQUEST:

User clicks "Return Item"
           │
           ▼
1. VALIDATE RETURN ELIGIBILITY
   
   - Within return window? (7-30 days)
   - Item returnable? (some items not)
   - Not already returned?
           │
           ▼
2. CREATE RETURN REQUEST
   
   INSERT INTO returns (
     return_id, order_id, item_id, reason,
     status = 'requested', created_at
   )
           │
           ▼
3. SCHEDULE PICKUP (or drop-off)
   
   - Call shipping carrier API
   - Generate return label
   - Schedule pickup date
           │
           ▼
4. ITEM RECEIVED AT WAREHOUSE
   
   Warehouse staff:
   - Scan return
   - Quality check (damaged? resellable?)
   - Update return status
           │
           ▼
5. PROCESS REFUND
   
   a) Determine refund amount
      - Full refund if item OK
      - Partial if damaged by user
   
   b) Call Payment Gateway
      POST /refunds
      { payment_id, amount, reason }
   
   c) Credit to original payment method
           │
           ▼
6. UPDATE INVENTORY (if resellable)
   
   Return item to warehouse stock
   inventory += 1


REFUND STATES:

    ┌───────────┐
    │ REQUESTED │
    └─────┬─────┘
          │
          ▼
    ┌───────────┐
    │ PICKUP    │
    │ SCHEDULED │
    └─────┬─────┘
          │
          ▼
    ┌───────────┐
    │ PICKED UP │
    └─────┬─────┘
          │
          ▼
    ┌───────────┐
    │ RECEIVED  │ (at warehouse)
    └─────┬─────┘
          │
    ┌─────┴─────┐
    ▼           ▼
┌────────┐  ┌────────┐
│APPROVED│  │REJECTED│
│        │  │        │
└───┬────┘  └────────┘
    │
    ▼
┌────────┐
│REFUNDED│
└────────┘
```

---

## Flow 9: Seller Onboarding & Product Listing

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SELLER MARKETPLACE                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

SELLER ONBOARDING:

1. REGISTRATION
   - Business details
   - Bank account for payouts
   - Tax documents (GST, PAN)
   
2. VERIFICATION (1-3 days)
   - Document verification
   - Address verification
   - Background check
   
3. APPROVAL
   - Account activated
   - Can list products


PRODUCT LISTING FLOW:

Seller adds product
           │
           ▼
1. PRODUCT CREATION
   
   POST /seller/products
   {
     title, description, category,
     price, images, variants, inventory
   }
           │
           ▼
2. CONTENT MODERATION
   
   - Check for prohibited items
   - Image quality check
   - Trademark/copyright check
   
   Auto-approve if passes
   Queue for review if flagged
           │
           ▼
3. CATALOG UPDATE
   
   - Insert into products table
   - Index in Elasticsearch
   - Update category facets
           │
           ▼
4. INVENTORY SETUP
   
   - Allocate to warehouse
   - Ship products to Amazon warehouse (FBA)
   - Or keep in seller's warehouse (FBM)


SELLER ORDER FULFILLMENT:

New order:
1. Notify seller (email, dashboard, app)
2. Seller packs item
3. Prints shipping label
4. Hands to carrier
5. Updates status to "shipped"
6. Carrier delivers
7. Amazon pays seller (after deducting commission)


SELLER PAYOUT:

Weekly payout cycle:

1. Calculate seller earnings
   
   total_sales - amazon_commission - shipping_costs - returns
   
2. Hold for settlement period (7-14 days)
3. Transfer to seller's bank account
4. Generate payout report
```

---

## Flow 10: Recommendations

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              RECOMMENDATION ENGINE                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

RECOMMENDATION TYPES:

1. "FREQUENTLY BOUGHT TOGETHER"
   
   Pre-computed using Spark:
   
   FROM orders
   GROUP BY products bought in same order
   FIND co-occurrence patterns
   
   Store: product:{id}:bought_together = [P1, P2, P3]

2. "CUSTOMERS WHO VIEWED THIS ALSO VIEWED"
   
   Session-based collaborative filtering:
   
   Track product views per session
   Find products viewed in similar sessions

3. "BASED ON YOUR BROWSING HISTORY"
   
   User's recent views → Similar products (content-based)
   
   user_history = [P1, P2, P3]  (last viewed)
   similar = find_similar_products(user_history)

4. "RECOMMENDED FOR YOU" (Homepage)
   
   Personalized mix:
   - Recent browsing → Similar products
   - Purchase history → Complementary products
   - Trending in categories you browse
   - New arrivals in favorite brands


REAL-TIME PERSONALIZATION:

User views laptop → Immediately show:
  - Laptop bags
  - Mouse, keyboard
  - Extended warranty
  - Similar laptops

Implementation:
  1. Kafka: user-activity-events
  2. Flink: Real-time session tracking
  3. Update user profile in Redis
  4. Next API call uses updated profile
```

---

# 7. HANDLING EDGE CASES

## Race Conditions

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              RACE CONDITION: LAST ITEM                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

PROBLEM:
  Stock = 1
  User A and User B both try to buy at same time

SOLUTION: Optimistic Locking with Version

UPDATE inventory
SET quantity = quantity - 1, version = version + 1
WHERE variant_id = ? 
  AND warehouse_id = ?
  AND quantity >= 1
  AND version = {expected_version}

If affected_rows = 0:
  → Either out of stock OR concurrent update
  → Retry or show error
```

---

## Payment Idempotency

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              PAYMENT IDEMPOTENCY                                                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

PROBLEM:
  Payment request sent, but network timeout
  Client retries → Double charge?

SOLUTION: Idempotency Key

Every payment request includes order_id as idempotency key

Payment gateway:
  1. Check: Have I processed this order_id before?
  2. If yes → Return previous result (no new charge)
  3. If no → Process and store result

Our side:
  1. Before calling gateway, set:
     Redis: payment:order_id:status = "processing"
  
  2. After response:
     Update: payment:order_id:status = "success" or "failed"
  
  3. On retry:
     Check Redis first → Return cached result
```

---

## Cart Abandonment

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              CART ABANDONMENT HANDLING                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

User adds item but doesn't checkout

RECOVERY FLOW:

Day 1 (1 hour after):
  - Email: "You left something in your cart!"
  - Show cart items with images

Day 2:
  - Push notification: "Complete your purchase"
  
Day 3:
  - Email with discount: "10% off if you buy today"

Day 7:
  - Final reminder
  - After this, mark cart as "abandoned"

INVENTORY HANDLING:
  - Cart items are NOT reserved (until checkout)
  - If item goes out of stock → Update cart on next load
  - Show "Only 2 left!" urgency messages
```

---

# 8. TECHNOLOGY STACK

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              AMAZON TECH STACK                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

│ Component              │ Technology                    │ Why                              │
├────────────────────────┼───────────────────────────────┼──────────────────────────────────┤
│ API Gateway            │ Kong / AWS API Gateway        │ Rate limiting, auth              │
│ API Servers            │ Java / Go / Node.js           │ High performance                 │
│                        │                               │                                  │
│ Product DB             │ PostgreSQL                    │ ACID, complex queries            │
│ Orders DB              │ Cassandra                     │ High write, time-series          │
│ User DB                │ PostgreSQL                    │ ACID for auth                    │
│ Search                 │ Elasticsearch                 │ Full-text, facets                │
│ Cache                  │ Redis                         │ Sessions, cart, inventory cache  │
│                        │                               │                                  │
│ Message Queue          │ Kafka                         │ Event-driven, durability         │
│ Task Queue             │ Celery / SQS                  │ Background jobs                  │
│                        │                               │                                  │
│ Object Storage         │ S3                            │ Product images, documents        │
│ CDN                    │ CloudFront                    │ Image delivery                   │
│                        │                               │                                  │
│ Payment                │ Stripe / Razorpay             │ PCI compliance                   │
│ Email                  │ SendGrid / SES                │ Transactional email              │
│ SMS                    │ Twilio / SNS                  │ OTP, notifications               │
│                        │                               │                                  │
│ Container              │ Kubernetes / ECS              │ Orchestration                    │
│ Monitoring             │ Prometheus / Datadog          │ Metrics, alerts                  │
│ Logging                │ ELK Stack                     │ Centralized logs                 │
└────────────────────────┴───────────────────────────────┴──────────────────────────────────┘
```

---

# 9. INTERVIEW TALKING POINTS

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              KEY DESIGN DECISIONS                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

1. WHY REDIS FOR CART (NOT JUST DATABASE)?
   - Cart is read-heavy (view cart many times)
   - Eventual consistency is fine
   - Sub-millisecond latency for add/view
   - DB is async backup for persistence

2. WHY RESERVATION SYSTEM FOR INVENTORY?
   - Prevent overselling
   - Handle checkout abandonment gracefully
   - 15-minute window balances fairness and conversion

3. WHY CASSANDRA FOR ORDERS?
   - High write volume (millions/day)
   - Partition by user_id (user's order history = single partition)
   - Eventual consistency OK after order placed
   - PostgreSQL for aggregates (analytics)

4. WHY ELASTICSEARCH FOR PRODUCTS?
   - Full-text search
   - Faceted search (filters)
   - Autocomplete
   - Cannot do this efficiently in relational DB

5. HOW TO HANDLE FLASH SALES?
   - Redis as gatekeeper (DECR is atomic)
   - Virtual waiting room (frontend)
   - Short reservations (10 min TTL)
   - Async inventory decrement

6. PAYMENT IDEMPOTENCY?
   - Order ID as idempotency key
   - Check before charging
   - Store result, return on retry

7. WHY KAFKA FOR EVERYTHING?
   - Decouples services
   - Durability (replay events)
   - Multiple consumers per event
   - Handles burst (buffer during flash sales)
```

---

# 10. QUICK REFERENCE

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    AMAZON E-COMMERCE CHEAT SHEET                                                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

SEARCH:
  • Elasticsearch for full-text + facets
  • Redis for autocomplete cache
  • Personalization via user history

CART:
  • Redis as primary store
  • DB as async backup
  • Guest → User merge on login

CHECKOUT:
  • Reserve inventory with TTL
  • Payment is idempotent (order_id key)
  • Async post-processing via Kafka

INVENTORY:
  • Redis for fast checks
  • PostgreSQL for accuracy (checkout)
  • Reservation system prevents overselling
  • Warehouse routing = nearest with stock

ORDERS:
  • Cassandra (partition by user_id)
  • Status via webhook from carriers
  • Async notifications via Kafka

FLASH SALES:
  • Redis DECR as gatekeeper
  • Short reservation TTL
  • Virtual waiting room (frontend)

PAYMENTS:
  • Idempotency via order_id
  • Two-phase: reserve → confirm
  • Refunds via same gateway
```

---
