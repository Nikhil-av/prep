# 🛗 ELEVATOR SYSTEM — LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design an **Elevator System** for a building with multiple elevators. Handle up/down requests from any floor, efficiently dispatch elevators, and manage elevator state.

---

## 🤔 THINK: Before Reading Further...
**What makes elevator design tricky? It's not moving up and down — it's DISPATCHING.**

<details>
<summary>👀 Click to reveal</summary>

The real question: **When someone presses "Up" on floor 5, which elevator should serve them?**

Options:
- Nearest elevator? (but it might be moving away)
- Nearest elevator **moving in the same direction**? ✅ Best
- Any idle elevator?

This is the **elevator scheduling algorithm** — the key interview topic.

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | Multiple elevators in a building |
| 2 | External request: press Up/Down button on any floor |
| 3 | Internal request: press destination floor inside elevator |
| 4 | **Smart dispatching** — choose best elevator for a request |
| 5 | Elevator picks up passengers along the way (same direction) |
| 6 | Status display: current floor, direction, doors |

---

## 🔥 THE KEY INSIGHT: Direction-Aware Dispatching

### 🤔 THINK: Elevator A is on floor 3 going UP. Elevator B is on floor 7, idle. Someone presses UP on floor 5. Which elevator?

<details>
<summary>👀 Click to reveal</summary>

**Elevator A!** Even though B is closer (2 floors vs 2 floors), A is already **moving toward floor 5 in the RIGHT direction**. It can pick up the person on the way.

**LOOK Algorithm (Elevator Algorithm):**
1. Continue in current direction, serving all requests along the way
2. When no more requests in current direction → reverse
3. Like a disk head — sweep up, then sweep down

**Dispatching priority:**
```
1. Elevator moving TOWARD requester in SAME direction → BEST
2. Idle elevator closest to requester → GOOD
3. Elevator moving AWAY but will eventually return → LAST RESORT
```

```python
def find_best_elevator(self, floor, direction):
    best = None
    best_score = float('inf')
    
    for elevator in self.elevators:
        score = self._calculate_score(elevator, floor, direction)
        if score < best_score:
            best_score = score
            best = elevator
    
    return best

def _calculate_score(self, elevator, floor, direction):
    distance = abs(elevator.current_floor - floor)
    
    if elevator.state == ElevatorState.IDLE:
        return distance  # Good — can go directly
    
    if elevator.direction == direction:
        if (direction == Direction.UP and elevator.current_floor <= floor) or \
           (direction == Direction.DOWN and elevator.current_floor >= floor):
            return distance  # BEST — on the way!
    
    return distance + 1000  # Penalty — wrong direction
```

</details>

---

## 📦 Core Entities

<details>
<summary>👀 Click to reveal</summary>

| Entity | Key Attributes |
|--------|---------------|
| **Direction** | UP, DOWN |
| **ElevatorState** | IDLE, MOVING_UP, MOVING_DOWN, DOOR_OPEN |
| **Request** | floor, direction (UP/DOWN), type (EXTERNAL/INTERNAL) |
| **Elevator** | id, current_floor, direction, state, requests (sorted set) |
| **ElevatorController** | elevators[], dispatch(), process requests |
| **Building** | num_floors, controller |

</details>

---

## 📊 Elevator Movement Loop

```python
def move(self):
    while self.has_requests():
        if self.direction == Direction.UP:
            self.current_floor += 1
            if self.current_floor in self.stops:
                self.open_doors()
                self.stops.remove(self.current_floor)
            if not any(s > self.current_floor for s in self.stops):
                self.direction = Direction.DOWN  # Reverse!
        # ... similar for DOWN
```

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How to handle peak morning traffic (everyone going up)?"

<details>
<summary>👀 Click to reveal</summary>

**Zone-based dispatching:** Assign elevators to floor ranges.
- Elevator A: floors 1-10
- Elevator B: floors 11-20
- Reduces wait time by avoiding overlap.

</details>

### Q2: "How to add priority for VIP floors?"

<details>
<summary>👀 Click to reveal</summary>

```python
class Request:
    priority: int  # Higher = more urgent
    
# Use priority queue instead of regular set for stops
import heapq
self.stops = []  # Min-heap by (-priority, floor)
```

</details>

### Q3: "How to handle emergency mode?"

<details>
<summary>👀 Click to reveal</summary>

All elevators go to ground floor, doors open, stop accepting requests. Separate `EmergencyState`.

</details>

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "I'd use the **LOOK algorithm** — elevator continues in its current direction serving all requests, then reverses when none remain. For dispatching, I pick the elevator **closest AND moving toward the requester in the same direction**. Elevator has states: IDLE, MOVING_UP, MOVING_DOWN. Each elevator maintains a sorted set of stops. The **ElevatorController** handles dispatching across multiple elevators."

---

*Document created during LLD interview prep session*
