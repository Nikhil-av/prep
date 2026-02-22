# 🎬 BOOKMYSHOW — Movie Ticket Booking System
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design a **Movie Ticket Booking System** like BookMyShow. Users search for movies, select shows, choose seats, and book tickets with payment.

---

## 🤔 THINK: Before Reading Further...
**Pause and think:** What are the first 3 clarifying questions YOU would ask the interviewer?

<details>
<summary>👀 Click to reveal suggested questions</summary>

| # | Question | Why Ask This? |
|---|----------|---------------|
| 1 | "Can multiple users try to book the same seat simultaneously?" | Determines if you need **concurrency control** — this is THE key challenge |
| 2 | "Is pricing fixed per seat, or does it vary by show/time?" | Price per Show+SeatType vs fixed per Seat — big design difference |
| 3 | "Should seats be locked temporarily during booking?" | Leads to **seat locking mechanism** with expiry |
| 4 | "Multiple theatres in multiple cities?" | Defines the entity hierarchy: City → Theatre → Screen → Show → Seat |
| 5 | "Can a user cancel a booking?" | Affects booking status flow |
| 6 | "Payment options?" | Strategy pattern opportunity |

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | Register users |
| 2 | Add movies, theatres, screens, and shows |
| 3 | Search movies — by title, by city, by theatre |
| 4 | View available seats for a show |
| 5 | Select seats and **lock them temporarily** (10 min) |
| 6 | Book tickets with payment |
| 7 | Cancel booking |
| 8 | Pricing based on **Show + SeatType** (not fixed per seat) |

## ❌ Non-Functional Requirements

| # | NFR |
|---|------|
| 1 | **Thread-safe** — handle concurrent bookings for same seat |
| 2 | **Seat locking** — temporary lock expires after timeout |
| 3 | **Singleton** for BookMyShow system |
| 4 | **Extensible** — add new search strategies, payment methods |

---

## 🤔 THINK: Entity Identification
**Before looking at the answer, list ALL the classes/entities you think are needed.**

Hint: There are ~12 entities including enums.

<details>
<summary>👀 Click to reveal entities</summary>

### Enums
```
SeatType:       SILVER, GOLD, PLATINUM
SeatStatus:     AVAILABLE, LOCKED, BOOKED     (per-show, NOT per-seat!)
BookingStatus:  PENDING, CONFIRMED, CANCELLED
```

### Core Entities
```
City        → has many Theatres
Theatre     → has many Screens, belongs to a City
Screen      → has many Seats (physical), belongs to a Theatre
Seat        → has seatNumber, seatType. Physical seat — status is NOT here!
Movie       → title, duration, genre
Show        → links Movie + Screen + time. Owns seat statuses and pricing!
Booking     → links User + Show + Seats + Payment
User        → name, email, bookings
```

### Strategy Pattern
```
SearchStrategy (ABC)  → SearchByMovie, SearchByTheatre, SearchByCity
PaymentStrategy (ABC) → CreditCardPayment, UPIPayment, DebitCardPayment
```

### System
```
BookMyShow (Singleton) → manages cities, theatres, shows, bookings
```
</details>

---

## 🔥 THE KEY INSIGHT: Where Does Seat Status Live?

### 🤔 THINK: Should seat status (AVAILABLE/BOOKED) be on the Seat object or somewhere else?

<details>
<summary>👀 Click to reveal — this is the #1 trick question!</summary>

**❌ WRONG: Status on Seat**
```python
class Seat:
    status = AVAILABLE  # ❌ Same physical seat is in multiple shows!
```
If Seat #A1 is booked for 3 PM show, it should still be available for 6 PM show. Putting status on Seat breaks this.

**✅ CORRECT: Status on Show (per-show tracking)**
```python
class Show:
    seat_status: dict[Seat, SeatStatus] = {}   # ✅ Each show tracks its own seats
    pricing: dict[SeatType, float] = {}         # ✅ Pricing also per show
```

**Why?** A physical seat exists once but participates in many shows. Status and price are **per-show properties**, not per-seat properties.

> **Interview tip:** If you put status on Seat, the interviewer will immediately ask "What happens when the same seat is in two different shows?" — That's your cue to move it to Show.

</details>

---

## 📊 Booking Flow

### 🤔 THINK: What are the steps from "user selects seats" to "booking confirmed"? What can go wrong at each step?

<details>
<summary>👀 Click to reveal flow</summary>

```
Step 1: User selects seats for a Show
        → Check: Are all seats AVAILABLE? (in that show's seat_status)
        → If any seat is LOCKED or BOOKED → reject

Step 2: Lock seats (temporary, 10 min)
        → Acquire threading.Lock() on the Show
        → Set seat_status = LOCKED for selected seats
        → Record lock_time for expiry tracking
        → Release lock

Step 3: User confirms payment
        → PaymentStrategy.pay(amount)
        → On success: seat_status = BOOKED, create Booking
        → On failure: seat_status = AVAILABLE (release lock)

Step 4: Booking created
        → booking.status = CONFIRMED
        → Store in user.bookings and show.bookings
```

**What can go wrong:**
- Two users lock the same seat simultaneously → **threading.Lock()** prevents this
- User locks but doesn't pay within 10 min → **Lock expiry** releases seats
- Payment fails → **Rollback** seat status to AVAILABLE

</details>

---

## 🔗 Entity Relationships

```
City ──1:N──→ Theatre
Theatre ──1:N──→ Screen
Screen ──1:N──→ Seat (physical)
Screen ──1:N──→ Show
Show ──N:1──→ Movie
Show ──1:N──→ Booking
Show ──owns──→ seat_status (dict)
Show ──owns──→ pricing (dict)
Booking ──N:1──→ User
Booking ──N:M──→ Seat (which seats booked)
```

---

## 💡 Design Patterns Used

| Pattern | Where | Why |
|---------|-------|-----|
| **Strategy** | SearchStrategy (SearchByMovie, SearchByTheatre) | Open/Closed — add SearchByGenre without changing system |
| **Strategy** | PaymentStrategy (Credit, UPI, Debit) | Different payment methods, same interface |
| **Singleton** | BookMyShow | One system instance |
| **Observer** (optional) | Notify user when locked seats expire | Reactive notification |

---

## 🧵 Concurrency Deep-Dive

### 🤔 THINK: Two users click "Book" for Seat A1 at the exact same time. What happens without locking? With locking?

<details>
<summary>👀 Click to reveal</summary>

**Without locking:**
```
Thread 1: check A1 → AVAILABLE ✅
Thread 2: check A1 → AVAILABLE ✅  (race condition!)
Thread 1: book A1 → BOOKED ✅
Thread 2: book A1 → BOOKED ✅      ← DOUBLE BOOKING! 💀
```

**With threading.Lock() on Show:**
```python
class Show:
    def __init__(self):
        self._lock = threading.Lock()
    
    def lock_seats(self, seats):
        with self._lock:  # Only ONE thread can enter at a time
            for seat in seats:
                if self.seat_status[seat] != SeatStatus.AVAILABLE:
                    return False  # Some seat already taken
            for seat in seats:
                self.seat_status[seat] = SeatStatus.LOCKED
            return True
```

**With locking:**
```
Thread 1: acquire lock → check A1 → AVAILABLE → lock A1 → release lock
Thread 2: WAITING for lock...
Thread 2: acquire lock → check A1 → LOCKED ❌ → reject → release lock
```
No double booking possible! ✅

</details>

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How do you handle seat lock expiry?"

<details>
<summary>👀 Click to reveal answer</summary>

**Option A: Lazy check (simpler, recommended for LLD)**
```python
def is_lock_expired(self, seat):
    if self.seat_status[seat] == SeatStatus.LOCKED:
        if time.time() - self.lock_time[seat] > LOCK_TIMEOUT:
            self.seat_status[seat] = SeatStatus.AVAILABLE
            return True
    return False
```
Check on next access — if expired, reset to AVAILABLE.

**Option B: Background thread (production)**
- Scheduled task runs every minute
- Scans for expired locks
- Releases them

> "For LLD, I'd use lazy check. In production, a background scheduler with Redis TTL keys."

</details>

### Q2: "What if a user books 5 seats but payment fails for 1?"

<details>
<summary>👀 Click to reveal answer</summary>

**Atomicity:** All or nothing. Either all seats get booked, or none.
```python
def book_seats(self, seats, payment):
    # Lock all seats first
    if not self.lock_seats(seats):
        return "Some seats unavailable"
    
    # Try payment
    total = sum(self.pricing[s.seat_type] for s in seats)
    if not payment.pay(total):
        self.release_seats(seats)  # Rollback ALL
        return "Payment failed"
    
    # All good — confirm all
    for seat in seats:
        self.seat_status[seat] = SeatStatus.BOOKED
    return Booking(...)
```

</details>

### Q3: "How would you add a waitlist when a show is full?"

<details>
<summary>👀 Click to reveal answer</summary>

Same as Library Management reservation queue:
```python
class Show:
    waitlist: deque[User] = deque()

def on_cancellation(self, seats):
    for seat in seats:
        self.seat_status[seat] = SeatStatus.AVAILABLE
    if self.waitlist:
        next_user = self.waitlist.popleft()
        notify(next_user, "Seats available!")
```

</details>

### Q4: "How would you support different screen types (IMAX, 3D, Dolby)?"

<details>
<summary>👀 Click to reveal answer</summary>

Add `screen_type` enum to Screen. Pricing becomes `{(SeatType, ScreenType): price}` on Show.
```python
class ScreenType(Enum):
    REGULAR = 1
    IMAX = 2
    DOLBY_ATMOS = 3

class Show:
    pricing: dict[tuple[SeatType, ScreenType], float]
```
No change to existing code — just extend the pricing model. **Open/Closed Principle!**

</details>

### Q5: "Scale to millions of concurrent users — what changes?"

<details>
<summary>👀 Click to reveal answer</summary>

| Concern | Solution |
|---------|----------|
| Seat locking | **Redis distributed locks** with TTL instead of threading.Lock |
| Database | **Optimistic locking** with version numbers on seat status |
| Search | **Elasticsearch** for movie/theatre search |
| Caching | **Redis** for show schedules, seat maps |
| Load balancing | Partition by city — each city's shows handled by separate service |
| Queue | **Message queue** (Kafka) for booking confirmations, payment processing |

</details>

---

## 🧪 Implementation Order

| Step | What | Key Decision |
|------|------|-------------|
| 1 | Enums (SeatType, SeatStatus, BookingStatus) | Status values |
| 2 | Seat, Movie (simple data classes) | Seat has NO status |
| 3 | Screen (has list of Seats) | Physical layout |
| 4 | Show (links Movie+Screen, owns seat_status + pricing) | **THE key entity** |
| 5 | Show.lock_seats() with threading.Lock | Concurrency |
| 6 | PaymentStrategy + implementations | Strategy pattern |
| 7 | Booking (links User+Show+Seats) | Created after payment |
| 8 | SearchStrategy + implementations | Strategy pattern |
| 9 | Theatre, City | Container entities |
| 10 | BookMyShow singleton | Orchestrator |
| 11 | Demo with concurrent booking test | Prove thread safety |

---

## ✅ Pre-Implementation Checklist

- [ ] Seat status lives on **Show**, not on Seat
- [ ] Pricing lives on **Show** per SeatType
- [ ] `threading.Lock()` on Show for concurrent seat locking
- [ ] Lock expiry mechanism (lazy check or background thread)
- [ ] Atomic booking — all-or-nothing for multi-seat
- [ ] PaymentStrategy (ABC + implementations)
- [ ] SearchStrategy (ABC + implementations)
- [ ] BookMyShow singleton with init guard
- [ ] Booking stores: user, show, seats, amount, status
- [ ] Demo: concurrent booking test (threading)

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "I'd design BookMyShow with **City → Theatre → Screen → Show** hierarchy. The key insight is that **seat status and pricing live on the Show**, not the Seat — because the same physical seat participates in multiple shows. I'd use **threading.Lock on Show** for concurrent bookings, **Strategy pattern** for search and payment, and the **Singleton pattern** for the system. Seat locking uses a temporary lock with expiry."

---

*Document created during LLD interview prep session*
