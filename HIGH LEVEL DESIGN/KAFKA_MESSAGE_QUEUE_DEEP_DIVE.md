# Kafka / Message Queue — Complete Deep Dive

> Interview-ready documentation — Covers Apache Kafka, RabbitMQ, SQS, Event-Driven Architecture

---

# 1. WHAT IS A MESSAGE QUEUE?

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              MESSAGE QUEUE OVERVIEW                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

A Message Queue decouples producers and consumers:

WITHOUT MESSAGE QUEUE:
  Order Service → (HTTP) → Inventory Service
                → (HTTP) → Email Service
                → (HTTP) → Analytics Service
  
  Problems:
    • Order Service must wait for all responses
    • If Inventory is down, order fails
    • Tight coupling

WITH MESSAGE QUEUE:
  Order Service → [Message Queue] → Inventory Service
                         ↘        → Email Service
                          ↘       → Analytics Service
  
  Benefits:
    • Order Service just publishes and returns
    • If Inventory is down, message waits
    • Loose coupling, async processing


KAFKA VS TRADITIONAL QUEUES:

Traditional (RabbitMQ, SQS):
  • Message consumed → deleted
  • One consumer per message
  • Push model

Kafka:
  • Message retained (days/weeks)
  • Multiple consumers read same message
  • Pull model (consumers fetch)
  • Replay possible!
```

---

# 2. KAFKA FUNDAMENTALS

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              KAFKA CORE CONCEPTS                                                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

1. TOPIC
   A category/stream of messages
   Example: "orders", "user-events", "payments"
   
   Like a table in a database, but append-only

2. PARTITION
   A topic is split into partitions (for parallelism)
   
   Topic: "orders"
   ├── Partition 0: [msg1, msg4, msg7, msg10...]
   ├── Partition 1: [msg2, msg5, msg8, msg11...]
   └── Partition 2: [msg3, msg6, msg9, msg12...]
   
   Each partition is an ordered, immutable log

3. OFFSET
   Position of a message within a partition
   
   Partition 0: [0][1][2][3][4][5][6][7][8]...
                 ↑           ↑
               offset 0   offset 4
   
   Consumers track their offset (where they've read up to)

4. PRODUCER
   Writes messages to topics
   Can specify which partition (or let Kafka decide)

5. CONSUMER
   Reads messages from topics
   Tracks its own offset

6. CONSUMER GROUP
   Multiple consumers sharing the work
   Each partition → exactly one consumer in group
   
   Topic: orders (3 partitions)
   Consumer Group: "order-processors"
   ├── Consumer A ← Partition 0
   ├── Consumer B ← Partition 1
   └── Consumer C ← Partition 2
   
   If Consumer B dies, its partition reassigned to A or C

7. BROKER
   A Kafka server
   Cluster = multiple brokers
   Each broker stores subset of partitions

8. ZOOKEEPER / KRAFT
   Coordinates brokers, tracks metadata
   (KRaft is new Zookeeper-less mode)
```

---

# 3. KAFKA ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              KAFKA CLUSTER ARCHITECTURE                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

                              PRODUCERS
           ┌─────────────────────────────────────────────────────────────────┐
           │  Order Service    │  Payment Service  │  User Service          │
           └─────────────────────────────────────────────────────────────────┘
                    │                   │                    │
                    └─────────────┬─────┴────────────────────┘
                                  ▼
           ┌─────────────────────────────────────────────────────────────────────────────┐
           │                           KAFKA CLUSTER                                     │
           │                                                                             │
           │   ┌─────────────────────────────────────────────────────────────────────┐ │
           │   │                    ZOOKEEPER / KRAFT                                │ │
           │   │   • Broker registration    • Topic configuration                    │ │
           │   │   • Leader election        • Consumer group coordination            │ │
           │   └─────────────────────────────────────────────────────────────────────┘ │
           │                                                                             │
           │   ┌────────────────┐  ┌────────────────┐  ┌────────────────┐              │
           │   │   BROKER 1     │  │   BROKER 2     │  │   BROKER 3     │              │
           │   │                │  │                │  │                │              │
           │   │ Topic: orders  │  │ Topic: orders  │  │ Topic: orders  │              │
           │   │ ┌────────────┐ │  │ ┌────────────┐ │  │ ┌────────────┐ │              │
           │   │ │Partition 0 │ │  │ │Partition 0 │ │  │ │Partition 0 │ │              │
           │   │ │ (Leader)   │ │  │ │ (Replica)  │ │  │ │ (Replica)  │ │              │
           │   │ └────────────┘ │  │ └────────────┘ │  │ └────────────┘ │              │
           │   │ ┌────────────┐ │  │ ┌────────────┐ │  │ ┌────────────┐ │              │
           │   │ │Partition 1 │ │  │ │Partition 1 │ │  │ │Partition 1 │ │              │
           │   │ │ (Replica)  │ │  │ │ (Leader)   │ │  │ │ (Replica)  │ │              │
           │   │ └────────────┘ │  │ └────────────┘ │  │ └────────────┘ │              │
           │   │ ┌────────────┐ │  │ ┌────────────┐ │  │ ┌────────────┐ │              │
           │   │ │Partition 2 │ │  │ │Partition 2 │ │  │ │Partition 2 │ │              │
           │   │ │ (Replica)  │ │  │ │ (Replica)  │ │  │ │ (Leader)   │ │              │
           │   │ └────────────┘ │  │ └────────────┘ │  │ └────────────┘ │              │
           │   └────────────────┘  └────────────────┘  └────────────────┘              │
           │                                                                             │
           │   REPLICATION: Each partition has 1 leader + N replicas                    │
           │   Leader handles reads/writes, replicas sync passively                     │
           │                                                                             │
           └─────────────────────────────────────────────────────────────────────────────┘
                                  │
                    ┌─────────────┴─────────────────────┐
                    ▼                                   ▼
           ┌─────────────────────────────────────────────────────────────────┐
           │  Inventory Service │  Email Service  │  Analytics Service      │
           │  (Consumer Group A)│ (Consumer Group B)│ (Consumer Group C)     │
           └─────────────────────────────────────────────────────────────────┘
                              CONSUMERS


NOTE: Multiple consumer groups can read same topic independently!
      Each group maintains its own offsets.
```

---

# 4. HOW KAFKA STORES DATA

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              KAFKA STORAGE INTERNALS                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

ON-DISK STRUCTURE:

/kafka-logs/
├── orders-0/               ← Topic "orders", Partition 0
│   ├── 00000000000000000000.log    ← Segment file (messages)
│   ├── 00000000000000000000.index  ← Offset → position mapping
│   ├── 00000000000000000000.timeindex
│   ├── 00000000000012345678.log    ← Next segment (after 1GB)
│   └── ...
├── orders-1/               ← Partition 1
│   └── ...
└── orders-2/               ← Partition 2
    └── ...


SEGMENT FILES:

Messages appended to .log file:
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Offset │ Size │ CRC │ Timestamp │ Key │ Value                                          │
├────────┼──────┼─────┼───────────┼─────┼────────────────────────────────────────────────┤
│   0    │ 256  │ ... │ 170734... │ u1  │ {"order_id": "123", "amount": 500}            │
│   1    │ 312  │ ... │ 170734... │ u2  │ {"order_id": "124", "amount": 750}            │
│   2    │ 198  │ ... │ 170734... │ u1  │ {"order_id": "125", "amount": 300}            │
└────────┴──────┴─────┴───────────┴─────┴────────────────────────────────────────────────┘


INDEX FILE:

Sparse index (every Nth message):
┌────────┬──────────────┐
│ Offset │ Position     │
├────────┼──────────────┤
│   0    │ 0            │
│  100   │ 45678        │
│  200   │ 91234        │
└────────┴──────────────┘

To find offset 150:
  1. Binary search index → find 100 is closest
  2. Seek to position 45678
  3. Scan forward to offset 150


WHY SO FAST?

1. SEQUENTIAL I/O
   Always append to end → disk friendly
   HDDs: 100+ MB/s sequential vs 1 MB/s random

2. ZERO-COPY
   Data goes from disk → network socket directly
   No copying through application memory
   sendfile() system call

3. PAGE CACHE
   OS caches file pages in RAM
   Hot data served from cache, not disk

4. BATCHING
   Producer batches messages before sending
   Consumer fetches in batches
   Reduces network round trips
```

---

# 5. PRODUCER DEEP DIVE

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              PRODUCER INTERNALS                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

PRODUCER WORKFLOW:

1. CREATE MESSAGE
   
   producer.send(
     topic="orders",
     key="user_123",      # Optional, used for partitioning
     value='{"order_id": "456", "amount": 1000}'
   )

2. SERIALIZE
   
   Key → bytes (StringSerializer, AvroSerializer)
   Value → bytes

3. PARTITION SELECTION
   
   If key provided:
     partition = hash(key) % num_partitions
     → Same key always goes to same partition
     → Ordering guaranteed for same key!
   
   If no key:
     Round-robin or sticky partition

4. BATCH ACCUMULATION
   
   ┌─────────────────────────────────────────────────────────────────────────────────────────────┐
   │ SEND BUFFER (per partition)                                                                │
   │                                                                                             │
   │ Partition 0 batch: [msg1, msg4, msg7, msg10]  ← Buffer until batch.size or linger.ms      │
   │ Partition 1 batch: [msg2, msg5, msg8]                                                      │
   │ Partition 2 batch: [msg3, msg6, msg9]                                                      │
   └─────────────────────────────────────────────────────────────────────────────────────────────┘
   
   batch.size: 16KB (flush when reached)
   linger.ms: 5ms (flush after time, even if batch not full)

5. SEND TO BROKER
   
   Sender thread sends batches to partition leaders
   Uses TCP connection pool

6. ACKNOWLEDGMENT

   acks=0: Fire and forget (no wait)
   acks=1: Leader wrote to its log (may lose if leader dies)
   acks=all: Leader + all in-sync replicas wrote (safest, slowest)


PRODUCER CODE:

from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['kafka1:9092', 'kafka2:9092'],
    acks='all',                    # Wait for all replicas
    retries=3,                     # Retry on failure
    batch_size=16384,              # 16KB batches
    linger_ms=5,                   # Wait 5ms to batch
    key_serializer=str.encode,
    value_serializer=lambda v: json.dumps(v).encode()
)

# Send message
future = producer.send(
    topic='orders',
    key='user_123',
    value={'order_id': '456', 'amount': 1000}
)

# Wait for confirmation
record_metadata = future.get(timeout=10)
print(f"Sent to partition {record_metadata.partition}, offset {record_metadata.offset}")
```

---

# 6. CONSUMER DEEP DIVE

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              CONSUMER INTERNALS                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

CONSUMER WORKFLOW:

1. JOIN CONSUMER GROUP
   
   Consumer registers with group coordinator (a broker)
   Coordinator assigns partitions

2. PARTITION ASSIGNMENT
   
   Topic: orders (6 partitions)
   Consumer Group: order-processors (3 consumers)
   
   Assignment (Range strategy):
   ├── Consumer 1 ← Partitions 0, 1
   ├── Consumer 2 ← Partitions 2, 3
   └── Consumer 3 ← Partitions 4, 5
   
   If Consumer 3 dies:
   ├── Consumer 1 ← Partitions 0, 1, 4
   └── Consumer 2 ← Partitions 2, 3, 5

3. FETCH MESSAGES
   
   Consumer polls broker:
   "Give me messages from partition 2, starting at offset 1000"
   
   Broker returns batch of messages

4. PROCESS MESSAGES
   
   Application logic handles each message

5. COMMIT OFFSET
   
   Tell Kafka "I've processed up to offset 1050"
   
   Commit Options:
     enable.auto.commit=true  → Auto commit every 5s
     enable.auto.commit=false → Manual commit after processing


CONSUMER CODE:

from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'orders',
    bootstrap_servers=['kafka1:9092'],
    group_id='order-processors',
    auto_offset_reset='earliest',  # Start from beginning if no offset
    enable_auto_commit=False,      # Manual commit
    value_deserializer=lambda m: json.loads(m.decode())
)

for message in consumer:
    print(f"Partition: {message.partition}, Offset: {message.offset}")
    print(f"Key: {message.key}, Value: {message.value}")
    
    # Process message
    process_order(message.value)
    
    # Commit after successful processing
    consumer.commit()


OFFSET COMMIT STRATEGIES:

1. AUTO COMMIT (Risky!)
   
   Problem: Commit happens on timer, not after processing
   If crash after commit but before processing → message lost!

2. COMMIT AFTER EACH MESSAGE (Slow)
   
   for message in consumer:
       process(message)
       consumer.commit()  # Slow due to network round trip

3. BATCH COMMIT (Balanced)
   
   messages = consumer.poll(timeout_ms=1000)
   for message in messages:
       process(message)
   consumer.commit()  # Commit entire batch

4. EXACTLY-ONCE (Advanced)
   
   Use Kafka transactions
   Write output + commit offset atomically
```

---

# 7. REPLICATION & FAULT TOLERANCE

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              REPLICATION                                                            │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

REPLICATION FACTOR = 3 means:
  Each partition stored on 3 brokers
  1 Leader + 2 Followers

LEADER:
  Handles all reads and writes
  Producers write to leader
  Consumers read from leader

FOLLOWERS (Replicas):
  Passively replicate from leader
  Pull messages from leader's log
  Stay in sync

ISR (In-Sync Replicas):
  Replicas that are caught up with leader
  Within replica.lag.max.messages or replica.lag.time.max.ms
  
  Only ISR replicas can become leader if leader dies


WRITE PATH:

Producer                     Leader                    Followers
   │                           │                           │
   │──── Send message ────────▶│                           │
   │                           │                           │
   │                           │──── Replicate ───────────▶│
   │                           │◀─── Acknowledge ──────────│
   │                           │                           │
   │◀─── Ack (if acks=all) ────│                           │


LEADER ELECTION:

1. Leader dies (broker crash, network issue)

2. Zookeeper/KRaft detects failure (session timeout)

3. Controller (a broker) elects new leader:
   - Pick from ISR only (has all data)
   - Prefer broker with lowest ID (deterministic)

4. Update metadata, notify clients

5. Clients refresh metadata, connect to new leader

Time to recover: ~1-2 seconds


UNCLEAN LEADER ELECTION:

What if ALL replicas are behind?
  
  unclean.leader.election.enable=false (default)
    Partition unavailable until a caught-up replica recovers
    No data loss, but unavailable
  
  unclean.leader.election.enable=true
    Elect out-of-sync replica as leader
    Some messages may be lost
    But partition available
```

---

# 8. COMMON USE CASES & PATTERNS

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              KAFKA USE CASES                                                        │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

1. EVENT SOURCING
   
   Store all events, derive state from events
   
   Topic: user-events
   ├── UserCreated {id: 1, name: "John"}
   ├── UserUpdated {id: 1, email: "john@x.com"}
   ├── UserDeleted {id: 1}
   
   Can replay events to rebuild state

2. ACTIVITY TRACKING
   
   Topic: page-views
   Every click, view, action → event
   
   Consumers:
   ├── Real-time dashboard
   ├── Recommendation engine
   └── Fraud detection

3. LOG AGGREGATION
   
   All services → Kafka → centralized logging
   
   Service A ─┐
   Service B ─┼──▶ Topic: logs ──▶ Elasticsearch
   Service C ─┘

4. STREAM PROCESSING
   
   Topic: orders → [Stream Processor] → Topic: order-analytics
   
   Real-time aggregations, transformations
   Use Kafka Streams or Flink

5. CHANGE DATA CAPTURE (CDC)
   
   Database → Debezium → Kafka → Other systems
   
   MySQL binlog captured as events
   Other services sync from Kafka

6. MICROSERVICES COMMUNICATION
   
   Order Service → Topic: orders → Inventory, Email, Analytics
   
   Loose coupling, async processing


OUTBOX PATTERN:

Problem: Write to DB + publish to Kafka atomically?

Solution:
  1. Write business data + event to DB (single transaction)
  2. Separate process reads events from DB
  3. Publishes to Kafka
  4. Marks event as published

  Order Table:           Outbox Table:
  ┌──────────────┐       ┌───────────────────────────────┐
  │ id: 123      │       │ id: 1                         │
  │ amount: 500  │       │ event_type: ORDER_CREATED     │
  │ status: new  │       │ payload: {order_id: 123, ...} │
  └──────────────┘       │ published: false              │
                         └───────────────────────────────┘
```

---

# 9. KAFKA vs OTHER MESSAGE QUEUES

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              COMPARISON                                                             │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

│ Feature              │ Kafka            │ RabbitMQ         │ AWS SQS          │
├──────────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ Model                │ Pull (poll)      │ Push             │ Pull (poll)      │
│ Message Retention    │ Days/weeks       │ Until consumed   │ 14 days max      │
│ Replay               │ Yes              │ No               │ No               │
│ Ordering             │ Per partition    │ Per queue        │ FIFO queue only  │
│ Throughput           │ Millions/sec     │ Thousands/sec    │ Thousands/sec    │
│ Latency              │ ~5ms             │ ~1ms             │ ~20ms            │
│ Multiple Consumers   │ Yes (groups)     │ Fanout exchange  │ No (one reader)  │
│ Exactly-once         │ Yes (complex)    │ No               │ No               │
│ Operational Overhead │ High             │ Medium           │ None (managed)   │


WHEN TO USE WHAT:

KAFKA:
  • High throughput (millions/sec)
  • Event sourcing, log aggregation
  • Multiple consumers for same data
  • Need replay capability
  • Stream processing

RABBITMQ:
  • Complex routing (exchanges)
  • Lower latency needed
  • Traditional request-reply patterns
  • Smaller scale

SQS:
  • AWS native, serverless
  • Simple queue, no ops burden
  • Decoupling microservices
```

---

# 10. KAFKA CONFIGURATION TUNING

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              KEY CONFIGURATIONS                                                     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

PRODUCER:

│ Config              │ Default    │ Tuning                               │
├─────────────────────┼────────────┼──────────────────────────────────────┤
│ acks                │ 1          │ all for durability, 0 for speed     │
│ batch.size          │ 16KB       │ Increase for throughput              │
│ linger.ms           │ 0          │ 5-100ms to allow batching            │
│ buffer.memory       │ 32MB       │ Increase for burst traffic           │
│ compression.type    │ none       │ snappy/lz4 for bandwidth savings     │
│ retries             │ 0          │ 3+ for reliability                   │
│ max.in.flight       │ 5          │ 1 for strict ordering (with retries) │


CONSUMER:

│ Config                │ Default    │ Tuning                             │
├───────────────────────┼────────────┼────────────────────────────────────┤
│ fetch.min.bytes       │ 1          │ Increase for throughput            │
│ fetch.max.wait.ms     │ 500        │ Higher = more batching             │
│ max.poll.records      │ 500        │ Lower if processing is slow        │
│ session.timeout.ms    │ 10000      │ Higher for slow consumers          │
│ enable.auto.commit    │ true       │ false for exactly-once semantics   │


BROKER:

│ Config                        │ Default  │ Tuning                       │
├───────────────────────────────┼──────────┼──────────────────────────────┤
│ num.partitions                │ 1        │ More = more parallelism      │
│ default.replication.factor    │ 1        │ 3 for production             │
│ min.insync.replicas           │ 1        │ 2 for durability (with acks=all) │
│ log.retention.hours           │ 168 (7d) │ Based on storage/replay needs │
│ log.segment.bytes             │ 1GB      │ Smaller = faster cleanup     │
```

---

# 11. INTERVIEW Q&A

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              KAFKA INTERVIEW QUESTIONS                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

Q1: How does Kafka guarantee ordering?
─────────────────────────────────────
A: Ordering is guaranteed WITHIN a partition only.
   Use the same key for related messages → same partition → ordered.
   No ordering across partitions.

Q2: What happens if a consumer dies?
────────────────────────────────────
A: Consumer group rebalances. Dead consumer's partitions assigned to others.
   Processing resumes from last committed offset.
   May see duplicate processing during rebalance.

Q3: How is Kafka so fast?
────────────────────────
A: • Sequential I/O (append-only logs)
   • Zero-copy (sendfile system call)
   • Page cache utilization
   • Batching (producer & consumer)
   • Compression

Q4: How to achieve exactly-once?
────────────────────────────────
A: Producer: enable.idempotence=true + transactions
   Consumer: Read from input → process → write to output + commit offset atomically
   Use Kafka Streams or transactions API

Q5: When to use more partitions?
────────────────────────────────
A: More partitions = more parallelism
   But: more memory, more rebalance time, more network
   Rule of thumb: 10-100KB/s per partition throughput capacity

Q6: Kafka vs RabbitMQ - when to use which?
─────────────────────────────────────────
A: Kafka: High throughput, event streaming, replay, log aggregation
   RabbitMQ: Complex routing, lower latency, simpler ops

Q7: What is consumer lag?
────────────────────────
A: Difference between latest offset and consumer's committed offset.
   High lag = consumer can't keep up.
   Monitor and scale consumers if lag grows.
```

---

# 12. QUICK REFERENCE

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                              KAFKA CHEAT SHEET                                                      │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘

CONCEPTS:
  Topic → Stream of records
  Partition → Ordered log within topic
  Offset → Position in partition
  Consumer Group → Share partitions among consumers
  Broker → Kafka server

GUARANTEES:
  • Ordering within partition (use same key)
  • At-least-once delivery (default)
  • Exactly-once (with transactions)
  • Durability (replication factor)

PRODUCER:
  acks=0: Fire & forget
  acks=1: Leader ack
  acks=all: All ISR ack (safest)

CONSUMER:
  auto.offset.reset=earliest: Read from start
  auto.offset.reset=latest: Read new only
  Manual commit for control

REPLICATION:
  Leader handles reads/writes
  Followers sync passively
  ISR = in-sync replicas
  Only ISR can become leader

STORAGE:
  Append-only log files
  Configurable retention (time/size)
  Compacted topics for KV state

SCALING:
  More partitions = more parallelism
  Consumer count <= partition count
  Shard by key for locality
```

---
