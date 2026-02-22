# 📝 LOGGING FRAMEWORK (Log4j) — LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design a **Logging Framework** like Log4j/SLF4J. Support multiple log levels, multiple output destinations (console, file, database), and configurable filtering per handler.

---

## 🤔 THINK: Before Reading Further...
**Which design pattern is this problem REALLY about?**

<details>
<summary>👀 Click to reveal</summary>

**Chain of Responsibility!**

A log message passes through a chain of handlers. Each handler decides:
1. Should I handle this? (is level >= my min_level?)
2. If yes → write to my destination
3. Pass to next handler regardless (OR only if not handled — depends on variant)

```
LogMessage("DB down!", ERROR)
    │
    ▼
ConsoleHandler(min=DEBUG) → handles ✅ → prints to console
    │
    ▼
FileHandler(min=WARNING) → handles ✅ → writes to file
    │
    ▼
DatabaseHandler(min=ERROR) → handles ✅ → inserts to DB
```

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | Log levels: DEBUG → INFO → WARNING → ERROR → FATAL (ordered!) |
| 2 | Multiple handlers: Console, File, Database |
| 3 | Each handler has a **configurable minimum level** |
| 4 | Handler processes log if `message.level >= handler.min_level` |
| 5 | Message passes through **chain** — multiple handlers can process same message |
| 6 | Thread-safe logging |
| 7 | Singleton Logger |

---

## 🤔 THINK: Entity Identification

**What are the classes needed? What methods does each handler have?**

<details>
<summary>👀 Click to reveal</summary>

| Entity | Key Attributes |
|--------|---------------|
| **LogLevel (Enum)** | DEBUG=1, INFO=2, WARNING=3, ERROR=4, FATAL=5 |
| **LogMessage** | level, message, timestamp |
| **LogHandler (ABC)** | min_level, next_handler, handle(), **write()** (abstract) |
| **ConsoleHandler** | implements write() → print |
| **FileHandler** | implements write() → file write |
| **DatabaseHandler** | implements write() → DB insert |
| **Logger (Singleton)** | chain_head, log() |

</details>

---

## 🔥 THE KEY INSIGHT: Template Method in Handlers

### 🤔 THINK: Should each handler implement its own `handle()` method? Or should the base class do it?

<details>
<summary>👀 Click to reveal — this is the #1 mistake!</summary>

**❌ WRONG: Each handler implements handle()**
```python
class ConsoleHandler:
    def handle(self, log):
        if log.level >= self.min_level:
            print(log)                    # Duplicated in every handler!
        if self.next:
            self.next.handle(log)         # Duplicated in every handler!

class FileHandler:
    def handle(self, log):
        if log.level >= self.min_level:
            file.write(log)              # Same pattern, different destination
        if self.next:
            self.next.handle(log)        # Same chain logic repeated!
```

**✅ CORRECT: Base class handles the chain + filtering, subclass only implements write()**
```python
class LogHandler(ABC):
    def handle(self, log_message):
        if log_message.level.value >= self.min_level.value:
            self.write(log_message)      # Only subclass method
        if self.next_handler:
            self.next_handler.handle(log_message)  # Chain in base only
    
    @abstractmethod
    def write(self, log_message):         # Subclasses ONLY implement this
        pass

class ConsoleHandler(LogHandler):
    def write(self, log):
        print(f"[{log.level.name}] {log.message}")  # Just the destination logic!
```

This is the **Template Method Pattern** — base class defines the algorithm skeleton, subclasses fill in specific steps.

</details>

---

## 📊 Chain Construction

### 🤔 THINK: How do you link handlers into a chain? What design enables this?

<details>
<summary>👀 Click to reveal</summary>

**Fluent chaining with `set_next()` returning self:**
```python
class LogHandler(ABC):
    def set_next(self, handler):
        self.next_handler = handler
        return handler   # Returns NEXT handler for fluent chaining!

# Build chain:
console = ConsoleHandler(LogLevel.DEBUG)
file_handler = FileHandler(LogLevel.WARNING)
db_handler = DatabaseHandler(LogLevel.ERROR)

console.set_next(file_handler).set_next(db_handler)
#       ↑ returns file_handler    ↑ returns db_handler
```

**⚠️ Common bug:** Calling `set_next()` on the SAME handler twice:
```python
console.set_next(file_handler)    # Console → File ✅
console.set_next(db_handler)      # Console → DB ❌ (overwrites File!)
```
Must chain through: `console → file → db`, not `console → both`.

</details>

---

## 🔗 Entity Relationships

```
Logger (Singleton)
    └── chain_head: LogHandler
            │
            ▼
        ConsoleHandler (min=DEBUG)
            │ next_handler
            ▼
        FileHandler (min=WARNING)
            │ next_handler
            ▼
        DatabaseHandler (min=ERROR)
            │ next_handler
            ▼
          None (end of chain)
```

---

## 💡 Design Patterns

| Pattern | Where | Why |
|---------|-------|-----|
| **Chain of Responsibility** | Handler chain | Log passes through multiple handlers |
| **Template Method** | LogHandler.handle() + write() | Base defines algorithm, subclass fills step |
| **Singleton** | Logger | One logger instance |

---

## 🧵 Thread Safety

### 🤔 THINK: Why does logging need to be thread-safe?

<details>
<summary>👀 Click to reveal</summary>

Multiple threads logging simultaneously → garbled output, lost messages.

```python
class Logger:
    def __init__(self):
        self.lock = threading.Lock()
    
    def log(self, level, message):
        log_message = LogMessage(level, message)
        with self.lock:
            self.chain_head.handle(log_message)
```

The lock ensures only one thread traverses the chain at a time.

</details>

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How would you add a timestamp and thread name to each log?"

<details>
<summary>👀 Click to reveal</summary>

**Formatter class (Decorator pattern):**
```python
class LogFormatter:
    def format(self, log_message):
        return (f"[{datetime.now()}] [{threading.current_thread().name}] "
                f"[{log_message.level.name}] {log_message.message}")
```
Each handler uses a formatter before writing. Configurable per handler.

</details>

### Q2: "How would you support log rotation (new file every day/every 10MB)?"

<details>
<summary>👀 Click to reveal</summary>

```python
class RotatingFileHandler(LogHandler):
    def __init__(self, max_size_mb=10):
        self.max_size = max_size_mb * 1024 * 1024
        self.current_file = self._new_file()
    
    def write(self, log):
        if os.path.getsize(self.current_file) > self.max_size:
            self.current_file = self._new_file()  # Rotate!
        with open(self.current_file, 'a') as f:
            f.write(str(log))
```

</details>

### Q3: "What if we want async logging (don't block the caller)?"

<details>
<summary>👀 Click to reveal</summary>

Same as Pub-Sub! Put log messages in a `queue.Queue`, have a background thread process them:
```python
class AsyncLogger:
    def __init__(self):
        self.queue = queue.Queue()
        self.worker = threading.Thread(target=self._process, daemon=True)
        self.worker.start()
    
    def log(self, level, message):
        self.queue.put(LogMessage(level, message))  # Non-blocking!
    
    def _process(self):
        while True:
            msg = self.queue.get()
            self.chain_head.handle(msg)
```

</details>

### Q4: "How to dynamically change log level at runtime?"

<details>
<summary>👀 Click to reveal</summary>

```python
class Logger:
    def set_level(self, handler_type, new_level):
        """Walk the chain, find handler by type, update level."""
        current = self.chain_head
        while current:
            if isinstance(current, handler_type):
                current.min_level = new_level
                return
            current = current.next_handler
```
Useful for debugging in production — temporarily set console to DEBUG.

</details>

---

## ⚠️ Common Bugs

| Bug | Fix |
|-----|-----|
| LogLevel ordering wrong (ERROR < WARNING) | DEBUG=1, INFO=2, WARN=3, ERROR=4, FATAL=5 |
| Chain logic duplicated in subclasses | Move `handle()` to base, subclasses only `write()` |
| `set_next()` called on same handler twice | Chain through: `a.set_next(b).set_next(c)` |
| Singleton `__init__` resets chain | Guard with `_initialized` flag |
| String comparison for log levels | Use Enum with numeric values for `>=` comparison |

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "I'd use **Chain of Responsibility** pattern. Each handler has a `min_level` and a `next_handler`. The base class `handle()` checks if the message level meets the threshold, calls `write()` (abstract, implemented by subclasses), then passes to next handler. This is **Template Method** — base defines the algorithm, subclasses fill in the destination. Console, File, and Database handlers each implement `write()`. The **Logger is a Singleton** with a `threading.Lock` for thread safety."

---

## ✅ Pre-Implementation Checklist

- [ ] LogLevel enum with CORRECT ordering (DEBUG=1 → FATAL=5)
- [ ] LogMessage with level, message, timestamp
- [ ] LogHandler ABC with handle() in base, write() abstract
- [ ] Fluent set_next() returning the next handler
- [ ] ConsoleHandler, FileHandler, DatabaseHandler (only write())
- [ ] Chain building: console → file → db
- [ ] Logger singleton with init guard
- [ ] Thread-safe logging with Lock
- [ ] Demo showing filtering at different levels

---

*Document created during LLD interview prep session*
