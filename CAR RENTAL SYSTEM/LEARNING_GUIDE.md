# 🚗 CAR RENTAL SYSTEM — LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design a **Car Rental System** where customers can browse available vehicles, make reservations, pick up cars, return them, and pay based on rental duration.

---

## 🤔 THINK: Before Reading Further...
**How is this different from a Parking Lot?**

<details>
<summary>👀 Click to reveal</summary>

| Feature | Parking Lot | Car Rental |
|---------|-------------|------------|
| Ownership | Customer owns vehicle | System owns vehicles |
| Duration | Hours | Days/weeks |
| **Reservation** | ❌ | ✅ Reserve in advance |
| **Vehicle selection** | Any spot | Customer picks vehicle type |
| **Pricing** | Per hour | Per day + insurance + fuel |
| **Fleet management** | ❌ | ✅ Track all vehicles |

The key additions: **Reservation system + Vehicle fleet management**.

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | Register customers |
| 2 | Add vehicles to fleet (type, plate, status) |
| 3 | **Search** available vehicles by type, date range |
| 4 | **Reserve** a vehicle for specific dates |
| 5 | **Pick up** vehicle (confirm reservation) |
| 6 | **Return** vehicle (calculate fee) |
| 7 | Pricing: per day × vehicle type + insurance |
| 8 | **Cancel** reservation |

---

## 🔥 THE KEY INSIGHT: Vehicle Status vs Reservation

### 🤔 THINK: Can a vehicle be "AVAILABLE" but still have a future reservation?

<details>
<summary>👀 Click to reveal</summary>

**YES!** Vehicle status and reservation are separate concerns:

```python
class VehicleStatus(Enum):
    AVAILABLE = 1      # Physically in lot, can be rented NOW
    RENTED = 2         # Currently with a customer
    MAINTENANCE = 3    # Being serviced

class Reservation:
    vehicle: Vehicle
    customer: Customer
    start_date: date
    end_date: date
    status: ReservationStatus  # CONFIRMED, PICKED_UP, RETURNED, CANCELLED
```

A vehicle can be AVAILABLE now but have a reservation starting tomorrow. **Search must check both vehicle status AND reservation overlap!**

```python
def search_available(self, vehicle_type, start_date, end_date):
    available = [v for v in self.vehicles
                 if v.vehicle_type == vehicle_type
                 and v.status == VehicleStatus.AVAILABLE
                 and not self._has_overlapping_reservation(v, start_date, end_date)]
    return available
```

</details>

---

## 📦 Core Entities

| Entity | Key Attributes |
|--------|---------------|
| **VehicleType** | SEDAN, SUV, HATCHBACK, LUXURY |
| **Vehicle** | plate, type, status, daily_rate |
| **Customer** | id, name, license_number |
| **Reservation** | customer, vehicle, dates, status |
| **RentalSystem (Singleton)** | vehicles, customers, reservations |

---

## 📊 Rental Flow

```
SEARCH → RESERVE → PICK_UP → RETURN → PAY
```

```python
def return_vehicle(self, reservation_id, payment):
    reservation = self.reservations[reservation_id]
    days = (reservation.actual_return - reservation.start_date).days
    fee = days * reservation.vehicle.daily_rate
    
    # Late return penalty
    if reservation.actual_return > reservation.end_date:
        late_days = (reservation.actual_return - reservation.end_date).days
        fee += late_days * reservation.vehicle.daily_rate * 1.5  # 1.5x late fee
    
    payment.pay(fee)
    reservation.vehicle.status = VehicleStatus.AVAILABLE
```

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How to handle overlapping reservations?"

<details>
<summary>👀 Click to reveal</summary>

```python
def _has_overlap(self, vehicle, start, end):
    for res in self.reservations:
        if res.vehicle == vehicle and res.status != ReservationStatus.CANCELLED:
            if start < res.end_date and end > res.start_date:
                return True  # Overlap!
    return False
```

</details>

### Q2: "How to add insurance options?"

<details>
<summary>👀 Click to reveal</summary>

Strategy pattern:
```python
class InsuranceType(Enum):
    NONE = 0
    BASIC = 200    # per day
    PREMIUM = 500  # per day

total = daily_rate * days + insurance_per_day * days
```

</details>

### Q3: "How to handle one-way rentals (pick up city A, return city B)?"

<details>
<summary>👀 Click to reveal</summary>

Add `pickup_location` and `return_location` to Reservation. Charge extra for different locations.

</details>

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "I'd design with **Vehicle** (fleet item with status), **Reservation** (links customer + vehicle + dates), and **RentalSystem** singleton. The key challenge is ensuring **no overlapping reservations** — search must check date ranges. Pricing is per-day with late return penalties. **Strategy pattern** for payment and insurance. Vehicle status (AVAILABLE/RENTED) is separate from reservation status (CONFIRMED/PICKED_UP/RETURNED)."

---

*Document created during LLD interview prep session*
