# 🎫 CONCERT TICKET BOOKING SYSTEM — LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design a **Concert Ticket Booking System** — users browse events, select seats, and book tickets. Handle concurrent bookings for popular concerts.

---

## 🤔 THINK: This is almost identical to BookMyShow — what's DIFFERENT?

<details>
<summary>👀 Click to reveal</summary>

| Feature | BookMyShow | Concert Booking |
|---------|-----------|----------------|
| Events | Movies (scheduled daily) | One-time concerts |
| Venue | Screen (fixed seats) | Venue/Arena (dynamic layouts) |
| **Seat categories** | Silver/Gold/Platinum | **VIP, Premium, General, Standing** |
| **Standing tickets** | ❌ | ✅ No assigned seat, just capacity |
| **Tiered pricing** | Fixed | Early bird, regular, last-minute |
| **Multiple shows** | Same movie many shows | Usually one show per concert |

The key additions: **Standing/General Admission** (no specific seat) and **tiered time-based pricing**.

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | Create events/concerts at venues |
| 2 | Define seat categories: VIP (assigned seat), General (capacity-based) |
| 3 | Search events by artist, date, city |
| 4 | Book tickets — select category, optionally select seat |
| 5 | **Concurrent booking** with seat locking |
| 6 | **Tiered pricing** — early bird discount |
| 7 | Cancel and refund |

---

## 🔥 THE KEY INSIGHT: Assigned Seats vs General Admission

### 🤔 THINK: How do you handle "standing/GA tickets" where there's no specific seat?

<details>
<summary>👀 Click to reveal</summary>

**Two types of ticket categories:**
```python
class TicketCategory:
    name: str        # "VIP", "General"
    price: float
    is_seated: bool  # True = pick a seat, False = just capacity

class SeatedCategory(TicketCategory):
    seats: list[Seat]      # Specific seats to choose from
    seat_status: dict      # seat → AVAILABLE/BOOKED

class GeneralAdmission(TicketCategory):
    total_capacity: int    # 5000 standing spots
    booked_count: int      # How many sold
    
    def book(self):
        if self.booked_count < self.total_capacity:
            self.booked_count += 1
            return True
        return False
```

**VIP/Premium** → customer picks exact seat (like BookMyShow).
**General/Standing** → no seat selection, just decrement capacity.

</details>

---

## 📦 Core Entities

| Entity | Purpose |
|--------|---------|
| **Event** | concert details, artist, date, venue |
| **Venue** | name, city, sections/categories |
| **TicketCategory** | VIP/General, pricing, capacity |
| **Ticket** | event, category, seat (optional), customer |
| **Customer** | name, email, tickets |
| **BookingSystem (Singleton)** | events, bookings, concurrent lock |

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How to implement early bird pricing?"

<details>
<summary>👀 Click to reveal</summary>

```python
class PricingTier:
    def get_price(self, category, current_date, event_date):
        days_before = (event_date - current_date).days
        if days_before > 30: return category.price * 0.7   # 30% off
        if days_before > 7:  return category.price * 0.9   # 10% off
        return category.price                                # Full price
```

</details>

### Q2: "How to prevent scalping (bulk buying)?"

<details>
<summary>👀 Click to reveal</summary>

- Max tickets per customer (e.g., 4)
- Waitlist for high-demand events
- Captcha verification
- Named tickets (ID required at entry)

</details>

### Q3: "What's different about concurrency here vs BookMyShow?"

<details>
<summary>👀 Click to reveal</summary>

**Same seat locking for VIP.** For General Admission, use **atomic counter**:
```python
with self._lock:
    if self.booked_count < self.total_capacity:
        self.booked_count += 1  # Atomic
```

</details>

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "Very similar to BookMyShow with two key differences: **General Admission** tickets (no seat, just capacity counter) and **tiered pricing** (early bird discounts). VIP seats use BookMyShow's seat locking approach. GA tickets use atomic counter decrement. Events are one-time (not scheduled shows). Everything else — Strategy for payment, Singleton for system, Lock for concurrency — is the same."

---

*Document created during LLD interview prep session*
