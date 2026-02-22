# 🗄️ LRU CACHE — LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design an **LRU (Least Recently Used) Cache** with O(1) get and put operations, with a fixed capacity that evicts the least recently used item when full.

---

## 🤔 THINK: Before Reading Further...
**Why can't you just use a dictionary? What are you missing if you do?**

<details>
<summary>👀 Click to reveal</summary>

A dict gives O(1) get/put, but:
- ❌ **No ordering** — you don't know which key was used least recently
- ❌ **No eviction** — when capacity is reached, which key to remove?

You need a dict + **something that tracks access order**. That something is a **Doubly Linked List**.

</details>

---

## 🔥 THE KEY INSIGHT: HashMap + Doubly Linked List

### 🤔 THINK: What data structure gives O(1) for: lookup, insert, delete, AND move-to-front?

<details>
<summary>👀 Click to reveal</summary>

**Neither alone works:**
| Structure | Lookup | Insert | Delete | Order |
|-----------|--------|--------|--------|-------|
| HashMap | O(1) | O(1) | O(1) | ❌ No order |
| Array | O(n) | O(n) | O(n) | ✅ Ordered |
| Linked List | O(n) | O(1) | O(1)* | ✅ Ordered |

**Combined: HashMap + Doubly Linked List = O(1) everything!**

```
HashMap: key → Node (for O(1) lookup)
DLL:    Head ←→ Node ←→ Node ←→ ... ←→ Tail
        (most recent)              (least recent = evict)
```

```python
class Node:
    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.prev = None
        self.next = None

class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.cache = {}          # key → Node
        self.head = Node(0, 0)   # Dummy head (most recent)
        self.tail = Node(0, 0)   # Dummy tail (least recent)
        self.head.next = self.tail
        self.tail.prev = self.head
```

**Why dummy head/tail?** Eliminates null checks when inserting/removing at boundaries. Cleaner code!

</details>

---

## 📊 Operations

### 🤔 THINK: Walk through GET and PUT operations step by step.

<details>
<summary>👀 Click to reveal</summary>

**GET(key):**
```python
def get(self, key):
    if key in self.cache:
        node = self.cache[key]
        self._remove(node)           # Remove from current position
        self._add_to_front(node)     # Move to most recent
        return node.value
    return -1                        # Cache miss
```

**PUT(key, value):**
```python
def put(self, key, value):
    if key in self.cache:
        self._remove(self.cache[key])  # Remove old
    
    node = Node(key, value)
    self._add_to_front(node)           # Add as most recent
    self.cache[key] = node
    
    if len(self.cache) > self.capacity:
        # Evict LRU (node just before tail)
        lru = self.tail.prev
        self._remove(lru)
        del self.cache[lru.key]        # KEY stored in node for this!
```

**Helper methods:**
```python
def _remove(self, node):
    node.prev.next = node.next
    node.next.prev = node.prev

def _add_to_front(self, node):
    node.next = self.head.next
    node.prev = self.head
    self.head.next.prev = node
    self.head.next = node
```

**Why does Node store the key?** When evicting LRU, we need to also delete it from the HashMap. Without the key in the node, we can't find it in the HashMap!

</details>

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How to make it thread-safe?"

<details>
<summary>👀 Click to reveal</summary>

```python
import threading

class LRUCache:
    def __init__(self, capacity):
        self.lock = threading.Lock()
        # ...
    
    def get(self, key):
        with self.lock:
            # ... same logic
    
    def put(self, key, value):
        with self.lock:
            # ... same logic
```

For high concurrency: **segment locks** (like ConcurrentHashMap) — lock per hash bucket, not entire cache.

</details>

### Q2: "How to add TTL (expiry) per key?"

<details>
<summary>👀 Click to reveal</summary>

```python
class Node:
    def __init__(self, key, value, ttl_seconds=None):
        self.expires_at = time.time() + ttl_seconds if ttl_seconds else None

def get(self, key):
    node = self.cache.get(key)
    if node and node.expires_at and time.time() > node.expires_at:
        self._remove(node)
        del self.cache[key]
        return -1  # Expired = cache miss
    # ... normal get
```

</details>

### Q3: "LRU vs LFU — when to use which?"

<details>
<summary>👀 Click to reveal</summary>

| Feature | LRU | LFU |
|---------|-----|-----|
| Evicts | Least **recently** used | Least **frequently** used |
| Data structure | HashMap + DLL | HashMap + FreqMap + DLL per freq |
| Good for | Temporal locality | Repeated access patterns |
| Example | Browser cache | CDN, DB query cache |

</details>

### Q4: "Can you implement LRU using Python's OrderedDict?"

<details>
<summary>👀 Click to reveal</summary>

```python
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity):
        self.cache = OrderedDict()
        self.capacity = capacity
    
    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)  # Move to most recent
            return self.cache[key]
        return -1
    
    def put(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)  # Remove least recent
```

**But in interviews, implement from scratch with DLL** — they want to see you build the data structure!

</details>

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "LRU Cache combines a **HashMap + Doubly Linked List** for O(1) everything. HashMap maps key to DLL Node for O(1) lookup. DLL maintains access order — most recent at head, least recent at tail. On GET: move node to front. On PUT: add to front, evict from tail if over capacity. **Node stores the key** so we can delete from HashMap during eviction. Dummy head/tail nodes simplify edge cases."

---

## ✅ Pre-Implementation Checklist

- [ ] Node class (key, value, prev, next) — key is critical for eviction!
- [ ] Dummy head/tail nodes
- [ ] _remove(node) — O(1) DLL removal
- [ ] _add_to_front(node) — O(1) DLL insertion
- [ ] get() — lookup + move to front
- [ ] put() — insert/update + evict if over capacity
- [ ] HashMap (key → Node) for O(1) lookup
- [ ] Demo: put, get, eviction

---

*Document created during LLD interview prep session*
