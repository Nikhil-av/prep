# ✈️ AIRLINE MANAGEMENT SYSTEM — LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design an **Airline Management System** where users search flights, book seats, and manage reservations. Airlines manage routes, schedules, and aircraft.

---

## 🤔 THINK: Before Reading Further...
**How is this similar to AND different from BookMyShow?**

<details>
<summary>👀 Click to reveal</summary>

| Feature | BookMyShow | Airline |
|---------|-----------|---------|
| Entity hierarchy | City→Theatre→Screen→Show | Airline→Route→Flight→Seat |
| Seat selection | ✅ Pick exact seat | ✅ Pick exact seat (or class) |
| **Date-based** | Shows at fixed times | Flights on specific dates |
| **Pricing** | Fixed per show | **Dynamic** — changes by demand |
| **Layovers** | ❌ | ✅ Multi-leg journeys |
| **Classes** | Silver/Gold/Platinum | Economy/Business/First |
| Cancellation | Simple refund | Complex — partial refund policies |

Same core: **seat booking with concurrency**. Extra: flight schedules, classes, layovers.

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | Search flights by source, destination, date |
| 2 | View available seats by **class** (Economy, Business, First) |
| 3 | **Book** a seat → create reservation |
| 4 | **Cancel** reservation with refund policy |
| 5 | Manage aircraft and routes |
| 6 | **Check-in** (online or at counter) |
| 7 | Pricing per class with dynamic adjustments |

---

## 🔥 THE KEY INSIGHT: Flight vs Aircraft

### 🤔 THINK: What's the relationship between a flight and an aircraft?

<details>
<summary>👀 Click to reveal</summary>

Same as **Book vs BookCopy** or **Movie vs Show**!

```
Aircraft = physical plane (seats, type, capacity)
Flight   = one instance of service (aircraft + route + date + time)
```

**Aircraft A320** can fly:
- Flight AI-101: Delhi→Mumbai, 10 AM, Feb 20
- Flight AI-102: Mumbai→Delhi, 2 PM, Feb 20
- Flight AI-201: Delhi→Bangalore, 8 AM, Feb 21

Seat status is per-FLIGHT, not per-aircraft!

```python
class Aircraft:
    model: str          # "A320"
    total_seats: dict    # {SeatClass.ECONOMY: 150, SeatClass.BUSINESS: 30}

class Flight:
    flight_number: str
    aircraft: Aircraft
    route: Route
    date: date
    seat_status: dict[str, SeatStatus]  # seat_number → status (per flight!)
    pricing: dict[SeatClass, float]     # class → price (per flight!)
```

</details>

---

## 📦 Core Entities

<details>
<summary>👀 Click to reveal</summary>

| Entity | Purpose |
|--------|---------|
| **SeatClass** | ECONOMY, BUSINESS, FIRST |
| **Airport** | code (DEL, BOM), name, city |
| **Route** | source, destination, distance |
| **Aircraft** | model, seat layout |
| **Flight** | aircraft + route + date + seat status + pricing |
| **Passenger** | name, passport, bookings |
| **Booking** | passenger, flight, seat, status, PNR |
| **AirlineSystem (Singleton)** | flights, bookings, search, book |

</details>

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How to handle connecting flights?"

<details>
<summary>👀 Click to reveal</summary>

```python
class Itinerary:
    legs: list[Flight]  # [DEL→BOM, BOM→GOA]
    
    def total_price(self):
        return sum(flight.pricing[self.seat_class] for flight in self.legs)
    
    def total_duration(self):
        return self.legs[-1].arrival_time - self.legs[0].departure_time
```
Search algorithm: BFS/DFS to find paths with max 1-2 layovers.

</details>

### Q2: "How to implement dynamic pricing?"

<details>
<summary>👀 Click to reveal</summary>

```python
def calculate_price(self, flight, seat_class):
    base = flight.base_pricing[seat_class]
    occupancy = flight.get_occupancy_percentage(seat_class)
    
    if occupancy > 80: return base * 1.5    # High demand
    if occupancy > 50: return base * 1.2
    return base
```

</details>

### Q3: "How to handle overbooking?"

<details>
<summary>👀 Click to reveal</summary>

Airlines overbook by ~5% (expecting cancellations). If overbooked:
- Waitlist passengers
- Offer compensation for volunteers to take next flight
- Priority by check-in time and fare class

</details>

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "I'd separate **Aircraft** (physical plane) from **Flight** (specific journey with date). Seat status and pricing are per-flight. Search by source, destination, date. Book with concurrent seat locking (like BookMyShow). For connecting flights, use an **Itinerary** with multiple flight legs. Dynamic pricing adjusts based on occupancy. **Singleton** system, **Strategy** for payment."

---

*Document created during LLD interview prep session*
