# 🅿️ PARKING LOT SYSTEM — LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design a **Parking Lot System** — vehicles enter, get assigned a spot based on size, park, and pay based on duration when they leave.

---

## 🤔 THINK: Before Reading Further...
**What are the first 3 questions you'd ask?**

<details>
<summary>👀 Click to reveal</summary>

| # | Question | Why? |
|---|----------|------|
| 1 | "What vehicle types?" | Determines spot sizes (Bike, Car, Truck) |
| 2 | "Multiple floors?" | Adds hierarchy: ParkingLot → Floor → Spot |
| 3 | "How is spot assigned?" | Nearest to entrance? First available? |
| 4 | "Pricing model?" | Flat rate? Per hour? Per vehicle type? |
| 5 | "Multiple entry/exit points?" | Concurrency at gates |

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | Support vehicle types: BIKE, CAR, TRUCK |
| 2 | Spot types: SMALL (bike), MEDIUM (car), LARGE (truck) |
| 3 | Assign **nearest available spot** matching vehicle size |
| 4 | **Park** and **unpark** vehicles |
| 5 | Calculate fee based on **duration × rate** |
| 6 | Track availability per floor |
| 7 | Display board showing available spots |

---

## 🔥 THE KEY INSIGHT: Vehicle-Spot Mapping

### 🤔 THINK: Can a car park in a truck spot? Can a truck park in a car spot?

<details>
<summary>👀 Click to reveal</summary>

**Rules:**
- Bike → SMALL spot only
- Car → MEDIUM spot only (or LARGE if you allow upsizing)
- Truck → LARGE spot only

**Simple approach:** 1:1 mapping (BIKE→SMALL, CAR→MEDIUM, TRUCK→LARGE)
**Flexible approach:** Vehicle can park in any spot >= its size (less common in interviews)

```python
VEHICLE_TO_SPOT = {
    VehicleType.BIKE: SpotType.SMALL,
    VehicleType.CAR: SpotType.MEDIUM,
    VehicleType.TRUCK: SpotType.LARGE,
}
```

</details>

---

## 📦 Core Entities

<details>
<summary>👀 Click to reveal</summary>

```
VehicleType: BIKE, CAR, TRUCK
SpotType:    SMALL, MEDIUM, LARGE

Vehicle:     license_plate, vehicle_type
ParkingSpot: spot_id, spot_type, floor, is_occupied, vehicle
ParkingFloor: floor_number, spots[]
Ticket:      vehicle, spot, entry_time, exit_time, fee
ParkingLot (Singleton): floors[], tickets, park(), unpark()
```

**Pricing:**
```python
RATE_PER_HOUR = {
    VehicleType.BIKE: 10,
    VehicleType.CAR: 20,
    VehicleType.TRUCK: 40,
}
```

</details>

---

## 📊 Park/Unpark Flow

### 🤔 THINK: What are the steps when a vehicle enters?

<details>
<summary>👀 Click to reveal</summary>

```
PARK:
1. Vehicle arrives at entry gate
2. Check vehicle type → find matching spot type
3. Scan floors → find first available spot of that type
4. If found → occupy spot, create Ticket, print ticket
5. If not found → "Parking Full for this vehicle type"

UNPARK:
1. Vehicle arrives at exit with Ticket
2. Calculate duration = exit_time - entry_time
3. Calculate fee = duration_hours × rate_per_hour[vehicle_type]
4. Free the spot (is_occupied = False, vehicle = None)
5. Process payment
```

</details>

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How to find the nearest available spot efficiently?"

<details>
<summary>👀 Click to reveal</summary>

**Simple (for LLD):** Iterate floors top-down, return first available.
**Optimized:** Use a **min-heap per spot type** storing (floor, spot_id). Pop from heap = nearest spot. When freed, push back.

```python
import heapq

class ParkingLot:
    def __init__(self):
        self.available_spots = {
            SpotType.SMALL: [],   # min-heap of (floor, spot_id)
            SpotType.MEDIUM: [],
            SpotType.LARGE: [],
        }
    
    def find_spot(self, spot_type):
        heap = self.available_spots[spot_type]
        if heap:
            return heapq.heappop(heap)
        return None
```

</details>

### Q2: "How to handle multiple entry/exit gates?"

<details>
<summary>👀 Click to reveal</summary>

Each gate is a thread → need **locking on spot assignment**:
```python
def park(self, vehicle):
    with self._lock:
        spot = self.find_available_spot(vehicle.vehicle_type)
        if spot:
            spot.occupy(vehicle)
```

</details>

### Q3: "How to add EV charging spots?"

<details>
<summary>👀 Click to reveal</summary>

Extend SpotType: `EV_CHARGING = 4`. Add `has_charger: bool` to ParkingSpot. Filter by both type AND charger availability. **Open/Closed principle!**

</details>

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "I'd design with **ParkingLot → Floor → Spot** hierarchy. Each vehicle type maps to a spot type. On entry, scan floors for first available matching spot, create a Ticket. On exit, calculate fee = hours × rate. For optimization, use a **min-heap per spot type** for O(log n) nearest spot lookup. Thread-safe with Lock on spot assignment."

---

*Document created during LLD interview prep session*
