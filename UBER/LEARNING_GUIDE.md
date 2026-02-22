# 🚕 CAB BOOKING SYSTEM (Uber/Ola) — LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design a **Cab Booking System** like Uber/Ola. Riders request rides, the system finds nearby available drivers, drivers accept/reject, rides go through states, and fare is calculated based on vehicle type + distance + surge.

---

## 🤔 THINK: Before Reading Further...
**What makes this problem different from BookMyShow?**

<details>
<summary>👀 Click to reveal</summary>

Both are booking systems, but Uber has **dynamic state** that BookMyShow doesn't:
1. **Location-based matching** — driver location changes after every ride
2. **Driver availability is real-time** — a driver goes from AVAILABLE → ON_RIDE → AVAILABLE
3. **Pricing is dynamic** — surge pricing changes based on demand
4. **Two-sided acceptance** — driver can accept OR reject (BookMyShow seat doesn't reject you!)

</details>

---

## 🤔 THINK: Clarifying Questions
**List 5 questions you'd ask the interviewer.**

<details>
<summary>👀 Click to reveal</summary>

| # | Question | Answer |
|---|----------|--------|
| 1 | Shared rides? | No — 1 rider, 1 driver |
| 2 | Vehicle types? | AUTO, MINI, SEDAN, SUV — different pricing |
| 3 | Can driver reject? | Yes — offer to next nearest |
| 4 | Surge pricing? | Yes — multiplier on base fare |
| 5 | How to find nearby drivers? | Distance-based (Euclidean for LLD) |
| 6 | Cancellation? | Both rider and driver can cancel |
| 7 | Rating? | Mutual — rider rates driver, driver rates rider |

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | Register riders and drivers (with vehicle type + location) |
| 2 | Rider requests ride with pickup, drop, vehicle type |
| 3 | Find nearby available drivers within radius |
| 4 | Driver accepts/rejects ride |
| 5 | Ride states: REQUESTED → ASSIGNED → IN_PROGRESS → COMPLETED / CANCELLED |
| 6 | Fare = (base + per_km + per_min) × surge |
| 7 | Payment via Strategy (Cash, Card, UPI) |
| 8 | Rating (mutual) |

---

## 🔥 THE KEY INSIGHT: Finding Nearby Drivers

### 🤔 THINK: How would you efficiently find drivers near a location?

<details>
<summary>👀 Click to reveal</summary>

**For LLD interview — keep it simple:**
```python
def find_nearby_drivers(self, location, vehicle_type, radius=10.0):
    # Step 1: Filter AVAILABLE drivers
    available = [d for d in self.drivers.values()
                 if d.status == DriverStatus.AVAILABLE]
    
    # Step 2: Filter by vehicle type
    matching = [d for d in available if d.vehicle_type == vehicle_type]
    
    # Step 3: Filter within radius
    nearby = [d for d in matching
              if d.location.distance_to(location) <= radius]
    
    # Step 4: Sort by distance (closest first)
    nearby.sort(key=lambda d: d.location.distance_to(location))
    
    return nearby
```

**Then say:** "In production, I'd use a **QuadTree** or **Google S2 cells** for O(log n) spatial queries instead of scanning all drivers."

**Distance function:**
```python
class Location:
    def distance_to(self, other):
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
```

</details>

---

## 📊 Ride State Machine

### 🤔 THINK: Draw the state transitions. Which transitions need validation?

<details>
<summary>👀 Click to reveal</summary>

```
REQUESTED ──→ DRIVER_ASSIGNED ──→ IN_PROGRESS ──→ COMPLETED
    │               │                   │
    └──→ CANCELLED  └──→ CANCELLED      └──→ CANCELLED
```

**Valid transitions:**
| From | To | Who triggers |
|------|----|-------------|
| REQUESTED | DRIVER_ASSIGNED | Driver accepts |
| DRIVER_ASSIGNED | IN_PROGRESS | Driver starts ride |
| IN_PROGRESS | COMPLETED | Driver ends ride |
| REQUESTED | CANCELLED | Rider cancels |
| DRIVER_ASSIGNED | CANCELLED | Either cancels |
| IN_PROGRESS | CANCELLED | Either cancels |
| COMPLETED | ❌ | Terminal state |
| CANCELLED | ❌ | Terminal state |

**Every method must validate:** `if ride.status != expected: reject!`

</details>

---

## 💰 Pricing

### 🤔 THINK: Strategy pattern or config dict for pricing? Which is simpler?

<details>
<summary>👀 Click to reveal</summary>

**Config dict is cleaner for this case:**
```python
PRICING = {
    VehicleType.AUTO:  {"base": 25, "per_km": 8,  "per_min": 1.0},
    VehicleType.MINI:  {"base": 40, "per_km": 10, "per_min": 1.5},
    VehicleType.SEDAN: {"base": 50, "per_km": 12, "per_min": 2.0},
    VehicleType.SUV:   {"base": 70, "per_km": 15, "per_min": 2.5},
}

fare = (base + distance × per_km + duration × per_min) × surge_multiplier
```

Strategy pattern would create 4 classes (AutoPricing, MiniPricing...) that all do the same formula with different numbers. Overkill — just use a dict.

**Use Strategy when:** The calculation LOGIC differs (not just the numbers).

</details>

---

## 🔗 Entity Relationships

```
CabBookingSystem (Singleton)
    ├── riders: dict[id, Rider]
    ├── drivers: dict[id, Driver]
    ├── rides: dict[id, Ride]
    └── surge_multiplier: float

Ride (Central Entity)
    ├── rider: Rider
    ├── driver: Driver (None until accepted)
    ├── pickup/drop: Location
    ├── status: RideStatus
    ├── vehicle_type: VehicleType
    ├── fare: float (calculated on completion)
    └── start_time / end_time

Driver
    ├── location: Location (updates after each ride!)
    ├── status: DriverStatus (AVAILABLE / ON_RIDE / OFFLINE)
    └── vehicle_type: VehicleType
```

---

## 💡 Design Patterns

| Pattern | Where | Why |
|---------|-------|-----|
| **Strategy** | PaymentStrategy (Cash/Card/UPI) | Different payment methods |
| **State Machine** | RideStatus transitions | Clear lifecycle |
| **Singleton** | CabBookingSystem | One system |

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How to handle driver rejecting?"

<details>
<summary>👀 Click to reveal</summary>

```python
def offer_ride_to_drivers(self, ride, nearby_drivers):
    for driver in nearby_drivers:
        accepted = self.offer_to_driver(driver, ride)
        if accepted:
            return True
    print("No drivers accepted!")
    ride.status = RideStatus.CANCELLED
    return False
```
Linear — offer to next nearest. In production: broadcast to multiple drivers simultaneously, first to accept wins.

</details>

### Q2: "How does surge pricing actually work?"

<details>
<summary>👀 Click to reveal</summary>

**Supply-demand ratio per geographic area:**
```python
def calculate_surge(self, location, radius=5.0):
    supply = len([d for d in self.drivers.values() 
                  if d.status == DriverStatus.AVAILABLE 
                  and d.location.distance_to(location) <= radius])
    demand = len([r for r in self.rides.values()
                  if r.status == RideStatus.REQUESTED])
    
    ratio = demand / max(supply, 1)
    if ratio > 2: return 2.0
    if ratio > 1.5: return 1.5
    if ratio > 1: return 1.2
    return 1.0
```

</details>

### Q3: "Thread safety — two riders request the same driver?"

<details>
<summary>👀 Click to reveal</summary>

Lock on driver status transition:
```python
def accept_ride(self, driver_id, ride_id):
    with self._lock:
        if driver.status != DriverStatus.AVAILABLE:
            return False  # Already taken by another ride
        driver.status = DriverStatus.ON_RIDE
        ride.driver = driver
```

</details>

### Q4: "How to add ride sharing (pool rides)?"

<details>
<summary>👀 Click to reveal</summary>

- Driver can have `max_passengers` (e.g., 3 seats)
- Driver status: AVAILABLE → PARTIALLY_OCCUPIED → FULL
- Match riders going in similar direction (angle-based or waypoint-based)
- Split fare proportionally by distance

</details>

### Q5: "Real-world driver location tracking?"

<details>
<summary>👀 Click to reveal</summary>

- Driver app sends GPS coordinates every 5-10 seconds via **WebSocket**
- Server updates driver location in **Redis** (fast writes)
- Use **GeoHash/S2 cells** to index locations for spatial queries
- For ETA: Google Maps Directions API

</details>

---

## ⚠️ Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Location representation | Simple (x,y) | Sufficient for LLD |
| Driver matching | Filter → Sort → Offer | O(n) but simple |
| Pricing | Config dict, not Strategy | Same formula, different constants |
| Driver location after ride | Update to drop location | Realistic — driver is at destination |
| Rating | Running average formula | No need to store all historical ratings |

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "I'd design Uber with **Rider, Driver, Ride** as core entities. The key challenge is **driver matching** — filter AVAILABLE drivers by vehicle type, filter within radius, sort by distance. Rides go through a **state machine**: REQUESTED → ASSIGNED → IN_PROGRESS → COMPLETED/CANCELLED, with validation on each transition. Fare uses a **pricing config dict** per vehicle type with surge multiplier. **Payment uses Strategy pattern**. Driver location updates to drop location after each ride. The system is a **Singleton**."

---

## ✅ Pre-Implementation Checklist

- [ ] Enums: RideStatus, DriverStatus, VehicleType
- [ ] Location with distance_to() (Euclidean)
- [ ] Rider with ride history + rating
- [ ] Driver with status, vehicle_type, location, rating
- [ ] Ride: links rider + driver + locations + status + fare
- [ ] State validation on every transition
- [ ] find_nearby_drivers (filter → sort)
- [ ] Pricing config dict per vehicle type
- [ ] Surge multiplier support
- [ ] PaymentStrategy (Cash, Card, UPI)
- [ ] Rating (running average)
- [ ] CabBookingSystem singleton
- [ ] Driver location updates after ride completes
- [ ] Demo: full ride, surge, cancellation, no drivers

---

*Document created during LLD interview prep session*
