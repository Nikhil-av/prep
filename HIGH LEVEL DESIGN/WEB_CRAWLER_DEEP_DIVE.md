# Web Crawler — Complete Deep Dive

> Interview-ready documentation — Covers Google Bot, Bing Crawler, any Search Engine Crawler

---

# 1. WHAT IS A WEB CRAWLER?

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              WEB CRAWLER OVERVIEW                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

A Web Crawler (Spider/Bot) is a program that:
  1. Starts with a list of URLs (seeds)
  2. Downloads the page content
  3. Extracts all links from the page
  4. Adds new links to the queue
  5. Repeats... forever!

PURPOSE:
  • Search Engines: Google crawls to index pages
  • Price Monitoring: Compare prices across e-commerce
  • Archive: Internet Archive (Wayback Machine)
  • Analytics: Track website changes
  • Machine Learning: Training data collection

SCALE (Google):
  • Known URLs: 130+ trillion pages
  • Crawled daily: 20+ billion pages
  • Index size: 100+ petabytes
  • Crawl rate: 1000+ pages/second per crawler
```

---

# 2. FUNCTIONAL REQUIREMENTS

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Seed URLs** | Start with initial list of URLs |
| 2 | **URL Discovery** | Extract links from crawled pages |
| 3 | **Content Download** | Fetch HTML/JSON content |
| 4 | **Deduplication** | Don't crawl same page twice |
| 5 | **Politeness** | Respect robots.txt, rate limits |
| 6 | **Priority** | Crawl important pages first |
| 7 | **Freshness** | Re-crawl pages based on change frequency |
| 8 | **URL Normalization** | Treat equivalent URLs as same |
| 9 | **Content Storage** | Store crawled content |
| 10 | **Distributed** | Scale across many machines |

---

# 3. NON-FUNCTIONAL REQUIREMENTS

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SCALE REQUIREMENTS                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

SCALE:
  Pages to crawl:           1 billion pages
  Crawl frequency:          20 billion pages/month
  Average page size:        500 KB
  Storage per month:        10 PB (raw)
  
THROUGHPUT:
  Pages/second:             8,000 (20B / 30 days / 86400 sec)
  Requests/second:          10,000+ (with retries)
  
LATENCY:
  Page download:            2-5 seconds (network bound)
  URL dedup check:          < 10ms
  
CONSTRAINTS:
  • Network bandwidth is the bottleneck
  • Must respect website rate limits
  • Some pages require JavaScript rendering
```

---

# 4. URL FRONTIER (THE CORE DATA STRUCTURE)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              URL FRONTIER                                                           │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

The URL Frontier is a priority queue with special properties:
  • Prioritizes important URLs
  • Enforces politeness (rate limits per domain)
  • Deduplicates URLs

STRUCTURE:

┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 URL FRONTIER                                                        │
│                                                                                                     │
│   ┌─────────────────────────────────────────────────────────────────────────────────────────────┐ │
│   │                        FRONT QUEUES (Priority-based)                                        │ │
│   │                                                                                              │ │
│   │   ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐                           │ │
│   │   │ Priority 1 │  │ Priority 2 │  │ Priority 3 │  │ Priority N │                           │ │
│   │   │ (Hot news) │  │ (Popular)  │  │ (Regular)  │  │ (Low)      │                           │ │
│   │   │            │  │            │  │            │  │            │                           │ │
│   │   │ cnn.com    │  │ wiki.org   │  │ blog.xyz   │  │ old.site   │                           │ │
│   │   │ bbc.com    │  │ github.com │  │ forum.abc  │  │            │                           │ │
│   │   └────────────┘  └────────────┘  └────────────┘  └────────────┘                           │ │
│   │                                                                                              │ │
│   │   Selector picks from queues (weighted random)                                              │ │
│   └─────────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                          │                                                         │
│                                          ▼                                                         │
│   ┌─────────────────────────────────────────────────────────────────────────────────────────────┐ │
│   │                        BACK QUEUES (Politeness-based)                                       │ │
│   │                                                                                              │ │
│   │   One queue per domain (ensures rate limiting)                                              │ │
│   │                                                                                              │ │
│   │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │ │
│   │   │ amazon.com   │  │ wikipedia.org│  │ github.com   │  │ medium.com   │                   │ │
│   │   │ next: 10:05  │  │ next: 10:04  │  │ next: 10:06  │  │ next: 10:05  │                   │ │
│   │   │              │  │              │  │              │  │              │                   │ │
│   │   │ /product/1   │  │ /wiki/Python │  │ /repo/linux  │  │ /post/123    │                   │ │
│   │   │ /product/2   │  │ /wiki/Java   │  │ /repo/react  │  │ /post/456    │                   │ │
│   │   └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘                   │ │
│   │                                                                                              │ │
│   │   Each queue has "next_fetch_time" based on Crawl-Delay                                     │ │
│   └─────────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘


PRIORITY CALCULATION:

priority_score = (
    page_rank * 0.4 +
    freshness_need * 0.3 +
    domain_authority * 0.2 +
    backlink_count * 0.1
)

High priority: News sites, popular pages, frequently changing
Low priority: Old blogs, static pages, low traffic
```

---

# 5. DETAILED HLD ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              WEB CRAWLER ARCHITECTURE                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                                        SEED URLS
                                   (Initial URL list)
                                           │
                                           ▼
           ┌─────────────────────────────────────────────────────────────────────────────┐
           │                         URL FRONTIER                                         │
           │                                                                             │
           │   • Priority queues (importance)                                            │
           │   • Back queues (per-domain politeness)                                     │
           │   • Distributed across nodes (sharded by domain hash)                       │
           │                                                                             │
           └─────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           │ Pop URL when domain's rate limit allows
                                           ▼
           ┌─────────────────────────────────────────────────────────────────────────────┐
           │                         FETCHER WORKERS                                      │
           │                                                                             │
           │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
           │   │  Fetcher Pod 1  │  │  Fetcher Pod 2  │  │  Fetcher Pod N  │            │
           │   ├─────────────────┤  ├─────────────────┤  ├─────────────────┤            │
           │   │ • Check robots  │  │ • DNS lookup    │  │ • HTTP request  │            │
           │   │ • Render JS?    │  │ • Handle redirect│ │ • Store content │            │
           │   └─────────────────┘  └─────────────────┘  └─────────────────┘            │
           │                                                                             │
           └─────────────────────────────────────────────────────────────────────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ▼                      ▼                      ▼
           ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
           │   ROBOTS.TXT      │  │   DNS RESOLVER    │  │   CONTENT STORE   │
           │   CACHE           │  │   CACHE           │  │   (S3/HDFS)       │
           ├───────────────────┤  ├───────────────────┤  ├───────────────────┤
           │ domain → rules    │  │ domain → IP       │  │ Raw HTML storage  │
           │ TTL: 24 hours     │  │ TTL: varies       │  │ Compressed        │
           └───────────────────┘  └───────────────────┘  └───────────────────┘
                                           │
                                           ▼
           ┌─────────────────────────────────────────────────────────────────────────────┐
           │                         HTML PARSER                                          │
           │                                                                             │
           │   • Extract text content                                                    │
           │   • Extract all <a href> links                                              │
           │   • Extract metadata (title, description)                                   │
           │   • Handle relative URLs                                                    │
           │                                                                             │
           └─────────────────────────────────────────────────────────────────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    ▼                                             ▼
           ┌───────────────────────────────────────┐    ┌─────────────────────────────────┐
           │         URL FILTER                    │    │      CONTENT PROCESSOR          │
           │                                       │    │                                 │
           │   • Normalize URL                     │    │   • Calculate content hash      │
           │   • Check if already seen (Bloom)     │    │   • Detect language            │
           │   • Filter spam/blocked domains       │    │   • Extract entities           │
           │   • Calculate priority                │    │   • Send to Search Indexer     │
           │                                       │    │                                 │
           └───────────────────────────────────────┘    └─────────────────────────────────┘
                    │                                             │
                    ▼                                             ▼
           ┌───────────────────────────────────────┐    ┌─────────────────────────────────┐
           │       URL DEDUP STORE                 │    │      SEARCH INDEX               │
           │       (Bloom Filter + DB)             │    │      (Elasticsearch/Solr)       │
           │                                       │    │                                 │
           │   • Bloom filter: 10B URLs, 1% FP    │    │   Indexed for search            │
           │   • Exact check in DB if needed       │    │                                 │
           └───────────────────────────────────────┘    └─────────────────────────────────┘
                    │
                    │ New URLs added back to frontier
                    ▼
              ┌──────────┐
              │ FRONTIER │ ◄── Loop continues!
              └──────────┘
```

---

# 6. KEY ALGORITHMS

## 6.1 URL Normalization

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              URL NORMALIZATION                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

All these URLs point to SAME page:

  http://Example.com/page
  http://example.com/page/
  http://example.com/page?
  http://example.com/page#section
  http://example.com:80/page
  https://www.example.com/page

Normalization rules:

1. Lowercase scheme and host
   HTTP://Example.COM → http://example.com

2. Remove default port
   http://example.com:80 → http://example.com
   https://example.com:443 → https://example.com

3. Remove fragment
   http://example.com/page#section → http://example.com/page

4. Remove trailing slash (or add consistently)
   http://example.com/page/ → http://example.com/page

5. Sort query parameters
   ?b=2&a=1 → ?a=1&b=2

6. Remove empty query
   http://example.com/page? → http://example.com/page

7. Decode unnecessary encoding
   %7E → ~

8. Remove www (optional)
   www.example.com → example.com


IMPLEMENTATION:

def normalize_url(url):
    parsed = urlparse(url.lower())
    
    # Remove default port
    host = parsed.netloc.replace(':80', '').replace(':443', '')
    host = host.lstrip('www.')
    
    # Remove fragment
    path = parsed.path.rstrip('/')
    
    # Sort query params
    query = urlencode(sorted(parse_qs(parsed.query).items()))
    
    return f"{parsed.scheme}://{host}{path}{'?' + query if query else ''}"
```

---

## 6.2 URL Deduplication (Bloom Filter)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              BLOOM FILTER FOR DEDUP                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

PROBLEM:
  10 billion URLs to track
  Each URL ~100 bytes
  Direct storage: 1 TB of memory!

SOLUTION: Bloom Filter
  Space-efficient probabilistic data structure
  Can say: "Definitely NOT seen" or "Probably seen"


HOW IT WORKS:

Bloom filter = Array of M bits (all 0 initially)
K hash functions

INSERT(url):
  for each hash function h1, h2, ... hK:
    index = hash(url) % M
    bit_array[index] = 1

CHECK(url):
  for each hash function:
    index = hash(url) % M
    if bit_array[index] == 0:
      return "DEFINITELY NOT SEEN"  ← 100% accurate
  return "PROBABLY SEEN"  ← May be false positive


EXAMPLE:

M = 10 bits, K = 2 hash functions

Insert "google.com":
  h1("google.com") % 10 = 3  → Set bit 3
  h2("google.com") % 10 = 7  → Set bit 7
  
  Bit array: [0,0,0,1,0,0,0,1,0,0]

Check "facebook.com":
  h1("facebook.com") % 10 = 2  → Bit 2 = 0
  Return: "DEFINITELY NOT SEEN" ✓

Check "new-url.com":
  h1("new-url.com") % 10 = 3  → Bit 3 = 1
  h2("new-url.com") % 10 = 7  → Bit 7 = 1
  Return: "PROBABLY SEEN"  ← False positive possible!


SIZING FOR 10 BILLION URLS:

Formula: m = -n * ln(p) / (ln(2)^2)
  n = 10 billion URLs
  p = 1% false positive rate
  
  m = 11.5 GB of memory (vs 1 TB naive)
  k = 7 hash functions

FALSE POSITIVE HANDLING:
  If Bloom says "probably seen":
    Check actual database (slow but rare)
```

---

## 6.3 Content Deduplication (SimHash)

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              CONTENT DEDUPLICATION                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

PROBLEM:
  Same article on 100 different news sites
  Slightly different (ads, layout) but same content
  Don't want to index duplicates

SOLUTION: SimHash (Locality Sensitive Hashing)
  Similar documents → Similar hashes
  Compare hashes to find near-duplicates


SIMHASH ALGORITHM:

1. Extract features (words, n-grams)
   Document: "the quick brown fox"
   Features: ["the", "quick", "brown", "fox", "the quick", "quick brown", ...]

2. Hash each feature to 64-bit value
   hash("the") = 0xA3B2C1D4E5F60718
   hash("quick") = 0x1234567890ABCDEF
   ...

3. Weight and aggregate
   For each bit position (0-63):
     If bit is 1: add weight
     If bit is 0: subtract weight
   
4. Convert to final hash
   For each position:
     If sum > 0: bit = 1
     If sum <= 0: bit = 0

5. Compare documents
   Hamming distance (XOR and count 1s)
   Distance < 3 → Near duplicate!


EXAMPLE:

Document A: "The quick brown fox jumps"
Document B: "The quick brown fox leaps"  (1 word different)

SimHash(A) = 1010110011...
SimHash(B) = 1010110010...
              ─────────^ (1 bit different)

Hamming distance = 1 → NEAR DUPLICATE!


Document C: "Machine learning is amazing"
SimHash(C) = 0101001100...

Hamming(A, C) = 28 → DIFFERENT documents
```

---

## 6.4 Politeness & Rate Limiting

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              ROBOTS.TXT & POLITENESS                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

ROBOTS.TXT:

Every website has robots.txt at root:
  https://example.com/robots.txt

Example:
  User-agent: *
  Disallow: /admin/
  Disallow: /private/
  Crawl-delay: 2           ← Wait 2 seconds between requests
  
  User-agent: Googlebot
  Allow: /                  ← Google can crawl everything
  
  Sitemap: https://example.com/sitemap.xml


PARSING RULES:

1. Fetch robots.txt FIRST before any page
2. Cache for 24 hours
3. Match User-agent (or use *)
4. Check if URL matches any Disallow pattern
5. Respect Crawl-delay


RATE LIMITING IMPLEMENTATION:

class PolitenessEnforcer:
    def __init__(self):
        self.domain_last_fetch = {}  # domain → timestamp
        self.domain_delay = {}       # domain → delay seconds
    
    def can_fetch(self, url):
        domain = get_domain(url)
        
        last_fetch = self.domain_last_fetch.get(domain, 0)
        delay = self.domain_delay.get(domain, 1)  # Default 1 sec
        
        if time.now() - last_fetch < delay:
            return False
        
        return True
    
    def record_fetch(self, url):
        domain = get_domain(url)
        self.domain_last_fetch[domain] = time.now()


ADDITIONAL POLITENESS:

• Identify yourself: User-Agent: MyBot/1.0 (contact@company.com)
• Lower priority during peak hours
• Back off on 500 errors
• Respect Cache-Control headers
• Don't crawl login pages
```

---

# 7. REQUEST FLOWS

## Flow 1: Crawling a Single URL

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              SINGLE URL CRAWL FLOW                                                  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

URL: https://example.com/article/123
           │
           ▼
1. POP FROM FRONTIER
   
   Check back queue for example.com
   Verify: current_time >= next_allowed_fetch_time
   Pop URL from queue
           │
           ▼
2. CHECK ROBOTS.TXT (cached)
   
   Redis: robots:example.com = {
     disallow: ["/admin/*", "/private/*"],
     crawl_delay: 2
   }
   
   URL "/article/123" allowed? YES
           │
           ▼
3. DNS RESOLUTION (cached)
   
   Redis: dns:example.com = "93.184.216.34"
   TTL: Based on DNS response
           │
           ▼
4. HTTP REQUEST
   
   GET /article/123 HTTP/1.1
   Host: example.com
   User-Agent: MyCrawler/1.0 (crawler@company.com)
   Accept: text/html
   Accept-Encoding: gzip
           │
           ▼
5. HANDLE RESPONSE
   
   200 OK → Process content
   301/302 → Follow redirect (max 5), add final URL to frontier
   403/404 → Skip, mark as error
   429 → Too many requests, increase crawl delay
   500 → Retry later with exponential backoff
           │
           ▼
6. STORE RAW CONTENT
   
   S3: s3://crawler-data/2024/02/08/example.com/article_123.html.gz
   
   Metadata in DB:
   {
     url: "https://example.com/article/123",
     fetch_time: "2024-02-08T10:30:00Z",
     status: 200,
     content_type: "text/html",
     content_length: 45000,
     s3_path: "...",
     content_hash: "sha256:abc123..."
   }
           │
           ▼
7. PARSE HTML
   
   Extract:
   - Title: "Breaking News: Example Story"
   - Links: ["/article/124", "/category/news", "https://other.com/page"]
   - Text content (for indexing)
           │
           ▼
8. PROCESS EXTRACTED LINKS
   
   For each link:
     a) Resolve relative to absolute
        "/article/124" → "https://example.com/article/124"
     
     b) Normalize URL
     
     c) Check Bloom filter: seen before?
        YES → Skip
        NO  → Continue
     
     d) Calculate priority
        PageRank-like score, domain authority
     
     e) Add to URL Frontier
           │
           ▼
9. UPDATE DOMAIN STATE
   
   example.com:
     next_fetch_time = now + crawl_delay
     pages_crawled += 1
           │
           ▼
10. SEND TO INDEXER
    
    Kafka: crawler.pages.fetched
    {
      url: "https://example.com/article/123",
      title: "Breaking News: Example Story",
      content: "Full text content...",
      fetch_time: "2024-02-08T10:30:00Z"
    }
```

---

## Flow 2: Distributed Crawl Coordination

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              DISTRIBUTED CRAWLING                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

CHALLENGE:
  100 crawler workers
  Must not crawl same domain from multiple workers simultaneously

SOLUTION: Partition by domain hash

                         URL FRONTIER (Central)
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ Shard 0  │ │ Shard 1  │ │ Shard N  │
              │ a-f.*    │ │ g-m.*    │ │ t-z.*    │
              └──────────┘ └──────────┘ └──────────┘
                    │           │           │
                    ▼           ▼           ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │Worker 1-5│ │Worker 6-10│ │Worker N  │
              │Only fetch│ │Only fetch│ │Only fetch│
              │shard 0   │ │shard 1   │ │shard N   │
              └──────────┘ └──────────┘ └──────────┘


CONSISTENT HASHING:

hash(domain) % num_shards = shard_id

amazon.com → hash → 42 % 10 = 2 → Shard 2
google.com → hash → 17 % 10 = 7 → Shard 7

Benefits:
  - Same domain always goes to same shard
  - One shard handles all rate limiting for its domains
  - No coordination needed between shards


WORKER ASSIGNMENT:

Each worker:
  1. Assigned to specific shard(s)
  2. Pulls URLs only from assigned shards
  3. Respects per-domain rate limits within shard

Worker failure:
  1. Health check fails
  2. Shard reassigned to healthy workers
  3. URLs remain in frontier, no loss
```

---

# 8. DATABASE SCHEMA

```sql
-- URL Frontier (in Redis/Cassandra for speed)
-- Actually implemented as sorted sets and queues

-- Crawl metadata (PostgreSQL)
CREATE TABLE crawled_pages (
    page_id         BIGSERIAL PRIMARY KEY,
    url             TEXT NOT NULL,
    url_hash        VARCHAR(64) NOT NULL,  -- For fast lookup
    
    -- Fetch info
    last_fetch      TIMESTAMP,
    next_fetch      TIMESTAMP,
    fetch_count     INT DEFAULT 0,
    
    -- Response
    status_code     INT,
    content_type    VARCHAR(100),
    content_length  BIGINT,
    content_hash    VARCHAR(64),  -- For duplicate detection
    
    -- Storage
    s3_path         TEXT,
    
    -- Priority
    priority_score  FLOAT,
    page_rank       FLOAT,
    
    -- Timestamps
    discovered_at   TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(url_hash)
);

CREATE INDEX idx_next_fetch ON crawled_pages(next_fetch);
CREATE INDEX idx_url_hash ON crawled_pages(url_hash);

-- Domain state
CREATE TABLE domains (
    domain          VARCHAR(255) PRIMARY KEY,
    
    -- Politeness
    crawl_delay     INT DEFAULT 1,
    robots_txt      TEXT,
    robots_fetched  TIMESTAMP,
    
    -- Statistics
    pages_crawled   BIGINT DEFAULT 0,
    last_crawl      TIMESTAMP,
    avg_response_ms INT,
    
    -- Health
    error_count     INT DEFAULT 0,
    blocked_until   TIMESTAMP
);
```

---

# 9. TECHNOLOGY STACK

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              WEB CRAWLER TECH STACK                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

│ Component              │ Technology                    │ Why                              │
├────────────────────────┼───────────────────────────────┼──────────────────────────────────┤
│ URL Frontier           │ Redis Sorted Sets             │ Priority queue, fast             │
│ URL Dedup              │ Bloom Filter (Redis)          │ Memory efficient                 │
│ Metadata DB            │ PostgreSQL                    │ Complex queries                  │
│                        │                               │                                  │
│ Content Storage        │ S3 / HDFS                     │ Cheap, scalable                  │
│ DNS Cache              │ Redis                         │ Fast lookups                     │
│ Robots Cache           │ Redis                         │ TTL-based expiry                 │
│                        │                               │                                  │
│ Fetcher                │ Python (aiohttp) / Go         │ Async, fast                      │
│ Parser                 │ BeautifulSoup / lxml          │ HTML parsing                     │
│ JS Rendering           │ Puppeteer / Playwright        │ SPAs, dynamic content            │
│                        │                               │                                  │
│ Message Queue          │ Kafka                         │ URL distribution                 │
│ Search Index           │ Elasticsearch                 │ Full-text search                 │
│ Orchestration          │ Kubernetes                    │ Worker scaling                   │
└────────────────────────┴───────────────────────────────┴──────────────────────────────────┘
```

---

# 10. INTERVIEW TALKING POINTS

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              KEY DESIGN DECISIONS                                                   │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

1. HOW TO HANDLE 10 BILLION URLS?
   - Bloom filter for deduplication (10GB vs 1TB)
   - URL normalization to avoid duplicates
   - Distributed frontier sharded by domain

2. HOW TO BE POLITE?
   - Respect robots.txt
   - Per-domain rate limiting (crawl-delay)
   - Identify bot in User-Agent
   - Back off on errors

3. HOW TO PRIORITIZE?
   - PageRank-like scoring
   - Freshness (news sites crawled more often)
   - Change detection (re-crawl if content changes)

4. HOW TO HANDLE DUPLICATES?
   - URL dedup: Bloom filter
   - Content dedup: SimHash for near-duplicates

5. HOW TO SCALE?
   - Shard by domain hash
   - Workers assigned to shards
   - Async fetching (100s of concurrent requests)

6. HOW TO HANDLE JS PAGES?
   - Headless browser (Puppeteer)
   - Only for pages that need it (expensive)
   - Detect by checking if content is minimal
```

---

# 11. QUICK REFERENCE

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                    WEB CRAWLER CHEAT SHEET                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

URL FRONTIER:
  • Front queues: Priority-based
  • Back queues: Per-domain politeness
  • Pop only when rate limit allows

DEDUPLICATION:
  • URL: Bloom filter (seen before?)
  • Content: SimHash (near-duplicate?)

POLITENESS:
  • Fetch robots.txt first
  • Respect Crawl-delay
  • Back off on 429/5xx errors

NORMALIZATION:
  • Lowercase
  • Remove default port
  • Remove fragment
  • Sort query params

SCALING:
  • Shard by domain hash
  • Async fetching
  • Distributed workers

STORAGE:
  • Raw HTML in S3/HDFS
  • Metadata in PostgreSQL
  • Caches in Redis
```

---
