# 📨 PUB-SUB / MESSAGE QUEUE SYSTEM — LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design an **in-memory Pub-Sub messaging system** where publishers send messages to topics, and subscribers consume messages from topics they've subscribed to.

---

## 🤔 THINK: Before Reading Further...
**What are the first 3 clarifying questions YOU would ask?**

<details>
<summary>👀 Click to reveal suggested questions</summary>

| # | Question | Why Ask This? |
|---|----------|---------------|
| 1 | "Is delivery synchronous or asynchronous?" | Determines threading model — producers shouldn't be blocked by slow consumers |
| 2 | "Can a subscriber subscribe to multiple topics?" | Affects the subscriber-topic relationship |
| 3 | "What happens if a subscriber is slow or offline?" | Leads to message queuing per subscriber |
| 4 | "Should messages be persisted?" | In-memory vs disk (Kafka) — keep in-memory for LLD |
| 5 | "Is it push-based or pull-based?" | Push = system pushes to subscribers. Pull = subscribers poll |
| 6 | "Message ordering guarantees?" | FIFO per topic? Per subscriber? |

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | Create **topics** |
| 2 | **Publishers** publish messages to topics |
| 3 | **Subscribers** subscribe/unsubscribe to topics |
| 4 | Messages delivered **asynchronously** to all subscribers of a topic |
| 5 | Each subscriber has its own **queue** (slow subscriber doesn't block others) |
| 6 | **FIFO ordering** — messages delivered in order per subscriber |
| 7 | **Graceful shutdown** — drain all queues before stopping |

---

## 🤔 THINK: Key Design Question
**Should the publisher wait until ALL subscribers have consumed the message before returning? Why or why not?**

<details>
<summary>👀 Click to reveal</summary>

**❌ NO — Publisher should be non-blocking!**

If Publisher waits for all subscribers, one slow subscriber blocks the publisher AND all other subscribers. This defeats the purpose of pub-sub (decoupling).

**✅ Solution: Each subscriber has its own `queue.Queue` and its own worker thread.**

```
Publisher → Topic → drops message into each subscriber's queue → returns immediately
                    Each subscriber's thread consumes from its own queue independently
```

This is exactly how **Kafka consumer groups** work — each consumer has an offset and reads at its own pace.

</details>

---

## 📦 Core Entities

### 🤔 THINK: What entities do you need? Hint: there are 5 main ones.

<details>
<summary>👀 Click to reveal</summary>

| Entity | Key Attributes |
|--------|---------------|
| **Message** | id, content, topic_name, timestamp |
| **Topic** | name, list of subscribers |
| **Publisher** | id, name (stateless — just sends messages) |
| **Subscriber** | id, name, **queue** (thread-safe), **worker thread** |
| **PubSubSystem** | Singleton — manages topics, publishers, subscribers |

</details>

---

## 🔥 THE KEY INSIGHT: Threading Model

### 🤔 THINK: Why does each subscriber need its own thread?

<details>
<summary>👀 Click to reveal</summary>

**Problem:** If subscriber A takes 5 seconds to process a message, subscriber B shouldn't wait.

**Solution:**
```python
class Subscriber:
    def __init__(self, name):
        self.name = name
        self.message_queue = queue.Queue()   # Thread-safe FIFO
        self.worker = threading.Thread(target=self._consume, daemon=True)
        self.running = True
        self.worker.start()

    def receive(self, message):
        self.message_queue.put(message)      # Non-blocking for publisher

    def _consume(self):
        while self.running or not self.message_queue.empty():
            try:
                msg = self.message_queue.get(timeout=0.5)
                print(f"[{self.name}] consumed: {msg.content}")
            except queue.Empty:
                continue
```

**Key points:**
- `queue.Queue` is thread-safe (no explicit locks needed)
- `daemon=True` means thread dies when main program exits
- `timeout=0.5` prevents infinite blocking so shutdown works
- `self.running` flag enables graceful shutdown

</details>

---

## 📊 Message Flow

```
Publisher.publish("topic1", "Hello World")
    │
    ▼
PubSubSystem.publish("topic1", message)
    │
    ▼
Topic("topic1").publish(message)
    │
    ├──→ Subscriber_A.receive(message) → drops into queue_A
    ├──→ Subscriber_B.receive(message) → drops into queue_B
    └──→ Subscriber_C.receive(message) → drops into queue_C
         (Publisher returns immediately!)

    Meanwhile, each subscriber's worker thread independently:
    Subscriber_A._consume() → pops from queue_A → processes
    Subscriber_B._consume() → pops from queue_B → processes
    Subscriber_C._consume() → pops from queue_C → processes
```

---

## 🔗 Entity Relationships

```
PubSubSystem (Singleton)
    ├── topics: dict[str, Topic]
    ├── publishers: dict[id, Publisher]
    └── subscribers: dict[id, Subscriber]

Topic
    └── subscribers: list[Subscriber]

Subscriber
    ├── message_queue: Queue  (own buffer)
    └── worker: Thread        (own consumer thread)
```

---

## 💡 Design Patterns

| Pattern | Where | Why |
|---------|-------|-----|
| **Observer** | Topic notifies all subscribers | Core pub-sub is Observer pattern! |
| **Singleton** | PubSubSystem | One message broker |
| **Producer-Consumer** | Publisher → Queue → Subscriber thread | Decoupled, buffered processing |

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How do you handle graceful shutdown?"

<details>
<summary>👀 Click to reveal</summary>

```python
def shutdown(self):
    # 1. Stop accepting new messages
    for subscriber in self.subscribers.values():
        subscriber.running = False
    
    # 2. Wait for all queues to drain
    for subscriber in self.subscribers.values():
        subscriber.worker.join(timeout=5)
    
    print("All subscribers finished. Shutdown complete.")
```

**Why `join(timeout=5)`?** Prevents infinite hang if a subscriber is stuck. After timeout, daemon threads die with the process.

</details>

### Q2: "What if a subscriber crashes mid-processing?"

<details>
<summary>👀 Click to reveal</summary>

**In our LLD:** Message is lost (it was popped from queue).

**In production (Kafka-style):**
- Subscriber tracks an **offset** (position in topic's message log)
- Only advances offset AFTER successful processing
- On crash, restarts from last committed offset
- This gives **at-least-once delivery**

```python
# Conceptual — not needed in LLD but great to mention
class Subscriber:
    offset: int = 0  # Position in topic's log
    
    def consume(self, topic):
        message = topic.messages[self.offset]
        process(message)
        self.offset += 1  # Only advance after success
```

</details>

### Q3: "How would you add message filtering?"

<details>
<summary>👀 Click to reveal</summary>

**Strategy pattern for filtering:**
```python
class MessageFilter(ABC):
    def matches(self, message) -> bool: pass

class KeywordFilter(MessageFilter):
    def __init__(self, keyword):
        self.keyword = keyword
    def matches(self, message):
        return self.keyword in message.content

class Subscriber:
    filters: list[MessageFilter] = []
    
    def receive(self, message):
        if all(f.matches(message) for f in self.filters):
            self.message_queue.put(message)
```

</details>

### Q4: "How does Kafka differ from this design?"

<details>
<summary>👀 Click to reveal</summary>

| Feature | Our LLD | Kafka |
|---------|---------|-------|
| Storage | In-memory queue | Persistent log on disk |
| Consumption | Pushed to subscriber | Subscriber pulls by offset |
| Replay | ❌ Message gone after consumption | ✅ Can replay from any offset |
| Consumer Groups | ❌ | ✅ Multiple consumers share partitions |
| Ordering | Per subscriber queue | Per partition |
| Scalability | Single process | Distributed, partitioned topics |

> "Our design is a simplified, in-memory version. In production, I'd use Kafka which stores messages as an immutable log, and consumers track offsets for replayability."

</details>

### Q5: "Can you make this thread-safe without `queue.Queue`?"

<details>
<summary>👀 Click to reveal</summary>

Yes, using `threading.Lock` with a regular `list`:
```python
class Subscriber:
    def __init__(self):
        self.messages = []
        self.lock = threading.Lock()
    
    def receive(self, message):
        with self.lock:
            self.messages.append(message)
    
    def consume(self):
        with self.lock:
            if self.messages:
                return self.messages.pop(0)
```

But `queue.Queue` is preferred — it's built for exactly this pattern and handles all edge cases (blocking gets, timeouts, etc.).

</details>

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "I'd design a Pub-Sub system with **Topic** as the central entity. Publishers push messages to a Topic, which fans out to all subscribers. The key insight is **each subscriber gets its own thread-safe queue** (`queue.Queue`) and a worker thread — so a slow subscriber doesn't block others. Publishers are non-blocking — they drop the message and return. For graceful shutdown, I set a `running` flag to False and join all worker threads. This follows the **Observer + Producer-Consumer** patterns."

---

## ✅ Pre-Implementation Checklist

- [ ] Message class (id, content, topic, timestamp)
- [ ] Topic with subscriber list and publish()
- [ ] Subscriber with `queue.Queue` + worker thread
- [ ] Publisher (stateless, sends via PubSubSystem)
- [ ] PubSubSystem singleton
- [ ] Non-blocking publisher → subscriber queue
- [ ] Graceful shutdown (stop flag + thread join)
- [ ] Demo: multiple subscribers, different speeds

---

*Document created during LLD interview prep session*
