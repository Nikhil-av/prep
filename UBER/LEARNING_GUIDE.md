# 🚕 CAB BOOKING SYSTEM (Uber/Ola) — Complete LLD Guide
## From Zero to Interview-Ready

---

## 📖 Table of Contents
1. [Problem Statement & Context](#-problem-statement)
2. [Clarifying Questions](#-clarifying-questions)
3. [Requirements](#-requirements)
4. [Entity Identification](#-entity-identification)
5. [Complete Class Design with Code](#-complete-class-design)
6. [Driver Matching Algorithm](#-driver-matching-algorithm)
7. [Ride State Machine](#-ride-state-machine)
8. [Pricing & Surge](#-pricing--surge)
9. [Design Patterns](#-design-patterns)
10. [Concurrency](#-concurrency)
11. [Full Working Implementation](#-full-implementation)
12. [Interviewer Follow-Up Questions (15+)](#-follow-up-questions)
13. [Comparison with Similar Problems](#-comparison)
14. [Production Scaling](#-production-scaling)
15. [Quick Recall Script](#-quick-recall)

---

## 🎯 Problem Statement

> Design a **Cab Booking System** like Uber/Ola. Riders request rides, the system finds nearby available drivers, drivers accept, rides go through lifecycle states, and fare is calculated based on vehicle type + distance + duration + surge.

**Real World Context:**
Uber processes millions of ride requests per day. The core challenges: (1) efficiently matching riders with nearby drivers in real-time, (2) handling the ride lifecycle from request to completion, (3) dynamic pricing based on supply/demand, (4) preventing race conditions when multiple riders request the same driver.

**Why this is a top interview question:**
- Tests **location-based matching** algorithm
- Tests **state machine** design (ride lifecycle)
- Tests **pricing strategy** (dynamic surge)
- Tests **concurrency** (two riders request same driver)
- Tests understanding of **real-world system trade-offs**

---

## 🗣️ Clarifying Questions

### 🤔 THINK: What are the first 10 questions you'd ask? This problem has MANY dimensions.

<details>
<summary>👀 Click to reveal — Complete question list</summary>

| # | Question | Why? | Answer |
|---|----------|------|--------|
| 1 | "Shared rides?" | Pool vs individual — big design difference | Individual only (1 rider, 1 driver) |
| 2 | "Vehicle types?" | Pricing + matching | AUTO, MINI, SEDAN, SUV |
| 3 | "Can driver reject?" | Affects matching flow | Yes — offer to next nearest |
| 4 | "Surge pricing?" | Dynamic pricing model | Yes — multiplier based on demand |
| 5 | "How to represent location?" | Coordinate system | (x, y) for LLD, GPS in production |
| 6 | "How to find nearby drivers?" | THE key algorithm | Distance-based within radius |
| 7 | "Both rider and driver can cancel?" | Cancellation rules | Yes, with conditions |
| 8 | "Rating system?" | Mutual rating | Yes — rider rates driver AND driver rates rider |
| 9 | "Payment options?" | Strategy pattern | Cash, Card, UPI |
| 10 | "ETA / route planning?" | Out of scope | Mention but don't implement |
| 11 | "Driver goes offline during ride?" | Error handling | Stop matching, but complete current ride |
| 12 | "Multiple ride requests simultaneously?" | Concurrency | Thread-safe driver assignment |

</details>

---

## ✅ Requirements

### Functional Requirements

| # | FR | Priority |
|---|-----|---------|
| 1 | Register riders and drivers (with vehicle type + location) | Must |
| 2 | Rider requests ride with pickup, drop, vehicle type | Must |
| 3 | **Find nearby available drivers** within radius, sorted by distance | Must |
| 4 | Driver accepts ride | Must |
| 5 | Ride states: REQUESTED → ASSIGNED → IN_PROGRESS → COMPLETED / CANCELLED | Must |
| 6 | Fare = (base + per_km × distance + per_min × duration) × surge | Must |
| 7 | Payment via Strategy (Cash, Card, UPI) | Must |
| 8 | Rating system (mutual) | Should |
| 9 | Ride history for riders and drivers | Should |
| 10 | Surge pricing control | Should |

### Non-Functional Requirements

| # | NFR |
|---|------|
| 1 | Thread-safe driver assignment (two riders can't get same driver) |
| 2 | State validation — can't skip states |
| 3 | Driver location updates after ride completion |
| 4 | Extensible — add new vehicle types, pricing rules |

---

## 📦 Entity Identification

### 🤔 THINK: What distinguishes a Rider from a Driver? What entities link them?

<details>
<summary>👀 Click to reveal — Complete entity map</summary>

### Enums (3)
```python
class RideStatus(Enum):
    REQUESTED = 1
    DRIVER_ASSIGNED = 2
    IN_PROGRESS = 3
    COMPLETED = 4
    CANCELLED = 5

class DriverStatus(Enum):
    AVAILABLE = 1
    ON_RIDE = 2
    OFFLINE = 3

class VehicleType(Enum):
    AUTO = 1
    MINI = 2
    SEDAN = 3
    SUV = 4
```

### All Entities
| Entity | Responsibility |
|--------|---------------|
| **Location** | (x, y) coordinates + distance calculation |
| **Rider** | Requests rides, has ride history + rating |
| **Driver** | Has vehicle type, status, location, rating |
| **Ride** | Links rider + driver + locations + status + fare |
| **PaymentStrategy** | ABC — Cash, Card, UPI |
| **CabBookingSystem** | Singleton — manages all entities |

</details>

---

## 🏗️ Complete Class Design

### Location — With Distance Calculation

```python
import math

class Location:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def distance_to(self, other: 'Location') -> float:
        """Euclidean distance — sufficient for LLD."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def __str__(self):
        return f"({self.x}, {self.y})"
```

### 🤔 THINK: Why Euclidean distance instead of Haversine?
> For LLD: Euclidean is simple and demonstrates the concept. In production, you'd use Haversine (for lat/lng on a sphere) or Google Maps API for actual road distance. **Always mention the real-world alternative.**

---

### Rider

```python
class Rider:
    def __init__(self, rider_id: int, name: str, location: Location):
        self.rider_id = rider_id
        self.name = name
        self.location = location
        self.ride_history: list['Ride'] = []
        self.rating: float = 5.0
        self.total_ratings: int = 0

    def update_rating(self, new_rating: float):
        total = self.rating * self.total_ratings + new_rating
        self.total_ratings += 1
        self.rating = round(total / self.total_ratings, 2)

    def __str__(self):
        return f"👤 {self.name} (⭐{self.rating})"
```

### Driver

```python
class Driver:
    def __init__(self, driver_id: int, name: str,
                 vehicle_type: VehicleType, location: Location):
        self.driver_id = driver_id
        self.name = name
        self.vehicle_type = vehicle_type
        self.location = location
        self.status = DriverStatus.AVAILABLE
        self.ride_history: list['Ride'] = []
        self.rating: float = 5.0
        self.total_ratings: int = 0

    def update_rating(self, new_rating: float):
        total = self.rating * self.total_ratings + new_rating
        self.total_ratings += 1
        self.rating = round(total / self.total_ratings, 2)

    def __str__(self):
        return f"🚗 {self.name} ({self.vehicle_type.name}, {self.status.name}, ⭐{self.rating})"
```

### 🤔 THINK: Why does Driver have a `location` that changes, but Rider's location is set at registration?

<details>
<summary>👀 Click to reveal</summary>

In our LLD, Rider specifies pickup location per ride (not stored on Rider). Driver's location is tracked and **updates to the drop location after each ride** — because the driver is physically AT the drop location after completing a ride.

```python
# After completing a ride:
driver.location = ride.drop_location  # Driver is now HERE
driver.status = DriverStatus.AVAILABLE
```

This is critical for **next ride matching** — without this update, drivers appear at their old location.

</details>

---

### Ride — The Central Entity

```python
class Ride:
    _counter = 0

    def __init__(self, rider: Rider, pickup: Location, drop: Location,
                 vehicle_type: VehicleType):
        Ride._counter += 1
        self.ride_id = Ride._counter
        self.rider = rider
        self.driver: Driver | None = None
        self.pickup = pickup
        self.drop = drop
        self.vehicle_type = vehicle_type
        self.status = RideStatus.REQUESTED
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.fare: float = 0
        self.distance: float = pickup.distance_to(drop)

    def __str__(self):
        driver_name = self.driver.name if self.driver else "None"
        return (f"🚕 Ride#{self.ride_id}: {self.rider.name} → {driver_name} | "
                f"{self.status.name} | {self.distance:.1f}km | ₹{self.fare:.0f}")
```

---

## ⚡ Driver Matching Algorithm

### 🤔 THINK: You have 1000 drivers. A rider requests a ride. How do you find the best driver?

<details>
<summary>👀 Click to reveal — Complete matching algorithm</summary>

**Step-by-step filtering pipeline:**

```python
def find_nearby_drivers(self, location: Location, vehicle_type: VehicleType,
                        radius: float = 10.0) -> list[Driver]:
    """
    Pipeline:
    1. ALL drivers
    2. → Filter AVAILABLE only
    3. → Filter matching vehicle_type
    4. → Filter within radius
    5. → Sort by distance (closest first)
    """
    # Step 1 + 2: Available + matching type
    candidates = [d for d in self.drivers.values()
                  if d.status == DriverStatus.AVAILABLE
                  and d.vehicle_type == vehicle_type]

    # Step 3: Within radius
    nearby = [d for d in candidates
              if d.location.distance_to(location) <= radius]

    # Step 4: Sort by distance
    nearby.sort(key=lambda d: d.location.distance_to(location))

    return nearby
```

**Complexity:**
- Brute force: **O(D)** where D = total drivers
- In production: **O(log D)** using QuadTree or Google S2 cells

**When to mention spatial indexing:**
> "For LLD, I'll scan all drivers. But in production, I'd use a **QuadTree** or **GeoHash** for O(log n) spatial queries. Uber uses Google S2 cells to partition the map into cells and index drivers by cell."

</details>

### 🤔 THINK: What if the nearest driver rejects? What if NO drivers are available?

<details>
<summary>👀 Click to reveal</summary>

**Driver rejection — offer to next:**
```python
def request_ride(self, rider_id, pickup, drop, vehicle_type):
    nearby = self.find_nearby_drivers(pickup, vehicle_type)
    
    if not nearby:
        print("❌ No drivers available!")
        ride.status = RideStatus.CANCELLED
        return None
    
    # In our LLD: auto-assign first available
    # In production: broadcast to top 3-5, first to accept wins
    ride.driver = nearby[0]
    ride.driver.status = DriverStatus.ON_RIDE
    ride.status = RideStatus.DRIVER_ASSIGNED
    return ride
```

**In production (broadcast model):**
1. Send ride request to top 5 nearest drivers simultaneously
2. First driver to tap "Accept" wins
3. If none accept within 30 seconds → expand radius, try more drivers
4. If still no one → tell rider "No drivers available"

</details>

---

## 📊 Ride State Machine

### 🤔 THINK: Draw ALL valid transitions. Which ones need validation? Who triggers each?

<details>
<summary>👀 Click to reveal — Complete state machine</summary>

```
                 accept()              start()              complete()
REQUESTED ───────────→ DRIVER_ASSIGNED ──────────→ IN_PROGRESS ──────────→ COMPLETED
    │                       │                          │
    │ cancel()              │ cancel()                 │ cancel()
    ▼                       ▼                          ▼
CANCELLED              CANCELLED                  CANCELLED
```

| Transition | Who Triggers | Validation | Side Effects |
|-----------|-------------|-----------|-------------|
| REQUESTED → ASSIGNED | Driver accepts | Ride is REQUESTED, Driver is AVAILABLE | Driver → ON_RIDE |
| ASSIGNED → IN_PROGRESS | Driver starts | Ride is ASSIGNED | Record start_time |
| IN_PROGRESS → COMPLETED | Driver completes | Ride is IN_PROGRESS | Calculate fare, process payment, update driver location |
| Any → CANCELLED | Rider or driver | Ride is NOT COMPLETED/CANCELLED | Free driver if assigned |
| COMPLETED → anything | ❌ | Terminal state | — |
| CANCELLED → anything | ❌ | Terminal state | — |

**Every method validates current state before transitioning:**
```python
def accept_ride(self, driver_id, ride_id):
    ride = self.rides.get(ride_id)
    driver = self.drivers.get(driver_id)
    
    # ──── VALIDATIONS ────
    if not ride or not driver:
        return False
    if ride.status != RideStatus.REQUESTED:      # Must be REQUESTED
        print(f"❌ Ride is {ride.status.name}, cannot accept")
        return False
    if driver.status != DriverStatus.AVAILABLE:   # Must be AVAILABLE
        print(f"❌ Driver is {driver.status.name}")
        return False
    
    # ──── TRANSITION ────
    ride.driver = driver
    ride.status = RideStatus.DRIVER_ASSIGNED
    driver.status = DriverStatus.ON_RIDE
    return True
```

</details>

---

## 💰 Pricing & Surge

### Pricing Config

### 🤔 THINK: Should pricing be a Strategy pattern or a config dict?

<details>
<summary>👀 Click to reveal</summary>

**Config dict — because the FORMULA is the same, only the NUMBERS differ:**

```python
PRICING = {
    VehicleType.AUTO:  {"base": 25,  "per_km": 8,   "per_min": 1.0},
    VehicleType.MINI:  {"base": 40,  "per_km": 10,  "per_min": 1.5},
    VehicleType.SEDAN: {"base": 50,  "per_km": 12,  "per_min": 2.0},
    VehicleType.SUV:   {"base": 70,  "per_km": 15,  "per_min": 2.5},
}
```

**Formula:**
```
fare = (base + distance × per_km + duration_min × per_min) × surge_multiplier
```

**Use Strategy when the calculation LOGIC differs** (not just numbers).
Use config dict when the same formula is applied with different parameters.

</details>

### Fare Calculation

```python
def calculate_fare(self, ride: Ride, duration_min: float) -> float:
    config = PRICING[ride.vehicle_type]
    base = config["base"]
    distance_charge = ride.distance * config["per_km"]
    time_charge = duration_min * config["per_min"]
    
    raw_fare = base + distance_charge + time_charge
    final_fare = round(raw_fare * self.surge_multiplier, 2)
    
    return final_fare
```

### Surge Pricing

### 🤔 THINK: When should surge be applied? How does Uber actually calculate it?

<details>
<summary>👀 Click to reveal</summary>

**For LLD — simple multiplier:**
```python
class CabBookingSystem:
    surge_multiplier: float = 1.0  # Default: no surge
    
    def set_surge(self, multiplier: float):
        self.surge_multiplier = multiplier
```

**In production — supply-demand ratio per geographic area:**
```python
def calculate_surge(self, location, radius=5.0):
    supply = len([d for d in self.drivers.values()
                  if d.status == DriverStatus.AVAILABLE
                  and d.location.distance_to(location) <= radius])
    
    demand = len([r for r in self.rides.values()
                  if r.status == RideStatus.REQUESTED
                  and r.pickup.distance_to(location) <= radius])
    
    ratio = demand / max(supply, 1)
    
    if ratio > 3:   return 2.5   # Extreme demand
    if ratio > 2:   return 2.0
    if ratio > 1.5: return 1.5
    if ratio > 1:   return 1.2
    return 1.0
```

**Real Uber:**
- City divided into hexagonal cells (H3 grid)
- Each cell has its own surge multiplier
- Updated every few seconds based on real-time supply/demand
- ML models predict demand and pre-position drivers

</details>

---

### Complete `complete_ride()` — Putting It All Together

```python
def complete_ride(self, ride_id: int, payment: PaymentStrategy,
                  duration_min: float = None) -> float:
    ride = self.rides.get(ride_id)
    if not ride or ride.status != RideStatus.IN_PROGRESS:
        print("❌ Invalid ride state")
        return 0

    # Calculate duration
    ride.end_time = datetime.now()
    if duration_min is None:
        duration_min = (ride.end_time - ride.start_time).total_seconds() / 60

    # Calculate fare
    fare = self.calculate_fare(ride, duration_min)
    ride.fare = fare

    # Process payment
    payment.pay(fare)

    # Update states
    ride.status = RideStatus.COMPLETED

    # ⚠️ CRITICAL: Update driver location to DROP location
    ride.driver.location = ride.drop
    ride.driver.status = DriverStatus.AVAILABLE

    # Record in history
    ride.rider.ride_history.append(ride)
    ride.driver.ride_history.append(ride)

    print(f"✅ Ride#{ride.ride_id} completed! Fare: ₹{fare:.0f}")
    return fare
```

---

## 💡 Design Patterns

| Pattern | Where | Why | Alternative |
|---------|-------|-----|-------------|
| **Singleton** | CabBookingSystem | One system | — |
| **Strategy** | PaymentStrategy | Swap payment methods | Config (less extensible) |
| **State Machine** | RideStatus transitions | Clear lifecycle with validation | String-based status (error-prone) |
| **Observer** (optional) | Notify rider of driver arrival | Decouple notification | Polling (less efficient) |

---

## 🧵 Concurrency

### 🤔 THINK: Two riders request the same driver simultaneously. What's the race condition?

<details>
<summary>👀 Click to reveal</summary>

**Without locking:**
```
Rider A: find drivers → Driver X is AVAILABLE ✅
Rider B: find drivers → Driver X is AVAILABLE ✅  ← RACE!
Rider A: assign Driver X → status = ON_RIDE ✅
Rider B: assign Driver X → status = ON_RIDE ✅  ← DOUBLE ASSIGNMENT! 💀
```

**With locking:**
```python
def request_ride(self, ...):
    with self._lock:
        nearby = self.find_nearby_drivers(pickup, vehicle_type)
        if nearby:
            driver = nearby[0]
            driver.status = DriverStatus.ON_RIDE  # Atomic
            ride.driver = driver
```

**Only one thread can assign a driver at a time.**

**Production approach:**
- Optimistic locking in database (version column)
- Redis distributed lock per driver
- Or: broadcast to driver, let DRIVER accept (no server-side race)

</details>

---

## 🎤 Interviewer Follow-Up Questions (15+)

### Q1: "How does Uber actually match drivers?"

<details>
<summary>👀 Click to reveal</summary>

1. **Partition the city** using H3 hexagonal grid or S2 cells
2. **Index drivers** by cell — each cell has a list of available drivers
3. **On ride request:** look at the rider's cell + adjacent cells
4. **Score drivers** by: distance, ETA (actual road time), acceptance rate, rating
5. **Broadcast** to top 3-5, first to accept wins
6. If no one accepts → expand search radius, try again

Our LLD simplifies this to: scan all → filter → sort by distance.

</details>

### Q2: "How to handle driver going offline mid-ride?"

<details>
<summary>👀 Click to reveal</summary>

```python
def driver_offline(self, driver_id):
    driver = self.drivers[driver_id]
    if driver.status == DriverStatus.ON_RIDE:
        # Don't interrupt current ride — let it complete
        print("⚠️ Driver will go offline after current ride")
        driver.go_offline_after_ride = True
    else:
        driver.status = DriverStatus.OFFLINE
```

</details>

### Q3: "How to implement ride cancellation with penalty?"

<details>
<summary>👀 Click to reveal</summary>

```python
def cancel_ride(self, ride_id, cancelled_by: str):
    ride = self.rides[ride_id]
    
    if ride.status in (RideStatus.COMPLETED, RideStatus.CANCELLED):
        return "Cannot cancel"
    
    penalty = 0
    if ride.status == RideStatus.IN_PROGRESS:
        penalty = 50  # Cancellation during ride = penalty
    elif ride.status == RideStatus.DRIVER_ASSIGNED:
        if cancelled_by == "rider":
            # Check if driver has been waiting > 5 min
            wait_time = (datetime.now() - ride.assigned_time).total_seconds() / 60
            if wait_time > 5:
                penalty = 30  # Late cancellation fee
    
    # Free driver
    if ride.driver:
        ride.driver.status = DriverStatus.AVAILABLE
        ride.driver = None
    
    ride.status = RideStatus.CANCELLED
    return penalty
```

</details>

### Q4: "How to add ride sharing (pool rides)?"

<details>
<summary>👀 Click to reveal</summary>

```python
class Ride:
    max_passengers: int = 1  # Regular
    riders: list[Rider] = []
    
    # For pool:
    max_passengers = 3
    status per rider (some may have dropped off)

class Driver:
    current_passengers: int = 0
    max_capacity: int = 4
    
    def is_full(self):
        return self.current_passengers >= self.max_capacity
    
    # Driver status: AVAILABLE → PARTIALLY_OCCUPIED → FULL
```

**Match riders going in similar direction:**
```python
def direction_similarity(pickup1, drop1, pickup2, drop2):
    angle1 = math.atan2(drop1.y - pickup1.y, drop1.x - pickup1.x)
    angle2 = math.atan2(drop2.y - pickup2.y, drop2.x - pickup2.x)
    return abs(angle1 - angle2) < math.pi / 4  # Within 45 degrees
```

</details>

### Q5: "How to implement ETA (Estimated Time of Arrival)?"

<details>
<summary>👀 Click to reveal</summary>

```python
AVERAGE_SPEED_KM_PER_MIN = 0.5  # 30 km/h in city

def estimate_eta(self, driver, pickup):
    distance = driver.location.distance_to(pickup)
    eta_minutes = distance / AVERAGE_SPEED_KM_PER_MIN
    return round(eta_minutes, 1)
```

In production: Google Maps Directions API for actual road-based ETA with traffic.

</details>

### Q6: "How to handle peak hours automatically?"

<details>
<summary>👀 Click to reveal</summary>

```python
def auto_surge(self):
    hour = datetime.now().hour
    if hour in [8, 9, 18, 19]:      # Rush hours
        self.surge_multiplier = 1.5
    elif hour in [23, 0, 1, 2]:     # Late night
        self.surge_multiplier = 1.8
    else:
        self.surge_multiplier = 1.0
```

Real systems: ML-based demand prediction, not hardcoded hours.

</details>

### Q7: "How to implement driver earnings dashboard?"

<details>
<summary>👀 Click to reveal</summary>

```python
class Driver:
    def total_earnings(self):
        return sum(r.fare for r in self.ride_history if r.status == RideStatus.COMPLETED)
    
    def rides_today(self):
        today = datetime.now().date()
        return [r for r in self.ride_history
                if r.end_time and r.end_time.date() == today]
    
    def average_rating(self):
        return self.rating
    
    def completion_rate(self):
        completed = sum(1 for r in self.ride_history if r.status == RideStatus.COMPLETED)
        total = len(self.ride_history)
        return completed / total if total else 0
```

</details>

### Q8: "How to implement favorite drivers?"

<details>
<summary>👀 Click to reveal</summary>

```python
class Rider:
    favorite_drivers: list[int] = []  # driver_ids

def find_nearby_drivers(self, location, vehicle_type, rider_id=None):
    nearby = [...standard matching...]
    
    if rider_id:
        rider = self.riders[rider_id]
        # Boost favorite drivers to top
        nearby.sort(key=lambda d: (
            0 if d.driver_id in rider.favorite_drivers else 1,
            d.location.distance_to(location)
        ))
    return nearby
```

</details>

### Q9-15 (Quick)

| Q | Question | Key Answer |
|---|----------|-----------|
| 9 | "How to add vehicle categories (Mini, Sedan, SUV)?" | Already covered — VehicleType enum + PRICING dict |
| 10 | "How to handle payment failure?" | Retry → fallback to cash → block future rides |
| 11 | "How to implement ride scheduling?" | Store `scheduled_time`, trigger matching near that time |
| 12 | "Driver hotspots suggestion?" | Heatmap of recent ride demand → recommend idle drivers to move there |
| 13 | "How to handle route deviation?" | Compare actual GPS path vs expected path, alert rider |
| 14 | "SOS/emergency button?" | Send location to emergency contacts + support, record trip |
| 15 | "How to add tipping?" | Optional tip after completion, 100% goes to driver |

---

## 📊 Comparison with Similar Problems

| Feature | Uber | BookMyShow | Food Delivery |
|---------|------|-----------|---------------|
| **Resource matched** | Driver | Seat | Agent |
| **Location-based** | ✅ Must match nearby | ❌ Fixed theatre | ✅ Agent near restaurant |
| **Status on entity** | Driver (AVAILABLE/ON_RIDE) | Show (per-seat) | Agent (AVAILABLE) |
| **Pricing model** | Dynamic (surge) | Fixed (per show) | Menu + delivery fee |
| **State count** | 5 | 3 (seat) | 6 |
| **Two-sided acceptance** | ✅ Driver accepts | ❌ | ❌ (agent assigned) |
| **Real-time location** | ✅ Driver moves | ❌ | ✅ Agent moves |

---

## 🌐 Production Scaling

| Concern | Solution |
|---------|----------|
| Location indexing | **Google S2 cells / H3 hexagons** for spatial queries |
| Real-time tracking | **WebSocket** for driver location updates |
| Driver location store | **Redis GeoSet** (`GEOADD`, `GEORADIUS`) |
| Matching | **Dedicated matching service** with priority queue |
| Surge calcuation | **Per-cell surge** updated every 30s |
| Payment | Async via **message queue** (Kafka → payment service) |
| ETA | **Google Maps API** / internal routing engine |
| Analytics | **Event streaming** (every ride event → Kafka → data lake) |

---

## 🧠 Quick Recall Script

> **First 30 seconds:**
> "I'd design Uber with **Rider, Driver, Ride** as core entities. The key algorithm is **driver matching** — filter AVAILABLE drivers by vehicle type, filter within radius, sort by distance. Rides go through a **state machine**: REQUESTED → ASSIGNED → IN_PROGRESS → COMPLETED/CANCELLED with validation on each transition."

> **If they ask about pricing:**
> "Fare = (base + per_km × distance + per_min × duration) × surge. Pricing is a **config dict** per vehicle type (not Strategy, because the formula is the same, only numbers differ). Surge multiplier is supply/demand based."

> **If they ask about concurrency:**
> "Lock on `request_ride()` — two riders can't get the same driver. In production: broadcast to driver, let driver accept (eliminates server-side race)."

> **If they ask about driver location:**
> "**Critical:** after ride completion, update driver location to DROP location. Otherwise matching finds drivers at their OLD location."

---

## ✅ Pre-Implementation Checklist

- [ ] Enums: RideStatus, DriverStatus, VehicleType
- [ ] Location with distance_to() (Euclidean)
- [ ] Rider (ride_history, rating)
- [ ] Driver (vehicle_type, status, location, rating)
- [ ] Ride (rider + driver + locations + status + fare)
- [ ] PRICING config dict per vehicle type
- [ ] find_nearby_drivers() — filter → sort
- [ ] request_ride() — find drivers → assign → create ride
- [ ] accept_ride() — validate state → assign driver
- [ ] start_ride() — validate → record start_time
- [ ] complete_ride() — calculate fare → payment → update driver location
- [ ] cancel_ride() — free driver → update status
- [ ] PaymentStrategy (Cash, Card, UPI)
- [ ] Surge multiplier
- [ ] Rating system (running average)
- [ ] CabBookingSystem singleton with Lock
- [ ] Demo: full ride, surge, cancel, state validation

---

*Version 2.0 — Comprehensive Edition*
