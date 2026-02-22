# 🍕 FOOD DELIVERY SYSTEM (Swiggy/Zomato) — LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design a **Food Delivery System** like Swiggy/Zomato. Customers browse restaurants, place orders, delivery agents are assigned, and orders go through states from placed to delivered.

---

## 🤔 THINK: Before Reading Further...
**How is this different from Uber? They both have location-based matching and delivery.**

<details>
<summary>👀 Click to reveal</summary>

| Feature | Uber | Food Delivery |
|---------|------|---------------|
| Entities matched | Rider ↔ Driver | Customer ↔ Restaurant + Agent |
| **Three-party system** | ❌ Two parties | ✅ Customer + Restaurant + Agent |
| Order items | N/A | MenuItem × Quantity = OrderItem |
| **Restaurant confirms** | N/A | ✅ Restaurant must accept order |
| Preparation time | N/A | ✅ Cooking takes time |
| Delivery fee | Per km | Per km from restaurant → customer |
| Menu management | N/A | ✅ Restaurant manages items |

The extra complexity is the **three-party system** and the **additional states** (CONFIRMED, PREPARING).

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | Register customers, restaurants, delivery agents |
| 2 | **Menu management** — restaurant adds/removes items |
| 3 | Search restaurants — by name, cuisine, location |
| 4 | **Place order** — select items from ONE restaurant |
| 5 | **Order states**: PLACED → CONFIRMED → PREPARING → OUT_FOR_DELIVERY → DELIVERED / CANCELLED |
| 6 | **Delivery agent assignment** — nearest available to restaurant |
| 7 | Payment — Strategy pattern |
| 8 | Rating — restaurant + delivery agent |

---

## 🔥 THE KEY INSIGHT: Order vs OrderItem

### 🤔 THINK: Why do we need a separate OrderItem class?

<details>
<summary>👀 Click to reveal</summary>

Same concept as Book vs BookCopy!

```python
# Order = the transaction
# OrderItem = one line item (MenuItem × Quantity)

class OrderItem:
    menu_item: MenuItem     # What was ordered
    quantity: int           # How many
    subtotal: float         # price × quantity

class Order:
    items: list[OrderItem]  # Multiple items per order
    total: float            # Sum of all subtotals + delivery fee
```

Without OrderItem, you can't track "2 Biryani + 1 Raita" — you'd only know "this order costs ₹500".

</details>

---

## � Order State Machine

### 🤔 THINK: Who triggers each state transition?

<details>
<summary>👀 Click to reveal</summary>

```
PLACED ──→ CONFIRMED ──→ PREPARING ──→ OUT_FOR_DELIVERY ──→ DELIVERED
  │           │              │                                  
  └→CANCELLED └→CANCELLED    └→CANCELLED    (can't cancel after pickup!)
```

| Transition | Who triggers | What happens |
|-----------|-------------|-------------|
| PLACED → CONFIRMED | **Restaurant** | Restaurant accepts the order |
| CONFIRMED → PREPARING | **Restaurant** | Kitchen starts cooking |
| PREPARING → OUT_FOR_DELIVERY | **System** | Assigns nearest agent, agent picks up |
| OUT_FOR_DELIVERY → DELIVERED | **Agent** | Agent delivers to customer, payment processed |
| Any → CANCELLED | **Customer** (before OUT_FOR_DELIVERY) | Cancel and free resources |

**Note:** Can't cancel after OUT_FOR_DELIVERY — food is already picked up!

</details>

---

## 🔗 Entity Relationships

```
FoodDeliverySystem (Singleton)
    ├── customers: dict[id, Customer]
    ├── restaurants: dict[id, Restaurant]
    ├── agents: dict[id, DeliveryAgent]
    └── orders: dict[id, Order]

Restaurant
    ├── menu: list[MenuItem]
    ├── location: Location
    └── order_history

Order (Central Entity)
    ├── customer: Customer
    ├── restaurant: Restaurant
    ├── agent: DeliveryAgent (None until assigned)
    ├── items: list[OrderItem]
    ├── status: OrderStatus
    ├── total_amount (item_total + delivery_fee)
    └── placed_at / delivered_at
```

---

## 💡 Design Patterns

| Pattern | Where | Why |
|---------|-------|-----|
| **Strategy** | PaymentStrategy, SearchStrategy | Interchangeable |
| **State Machine** | OrderStatus | 6 validated states |
| **Singleton** | FoodDeliverySystem | One system |
| **Observer** (optional) | Notify customer on status change | Real-time tracking |

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How to calculate delivery fee?"

<details>
<summary>👀 Click to reveal</summary>

```python
DELIVERY_FEE_PER_KM = 5

class Order:
    def __init__(self, customer, restaurant, items):
        distance = restaurant.location.distance_to(customer.location)
        self.delivery_fee = round(distance * DELIVERY_FEE_PER_KM)
        self.total = sum(i.subtotal for i in items) + self.delivery_fee
```

In production: Surge delivery fee during rain/peak hours. Minimum order for free delivery.

</details>

### Q2: "How to handle restaurant rejecting an order?"

<details>
<summary>👀 Click to reveal</summary>

```python
def reject_order(self, order_id, reason):
    order.status = OrderStatus.CANCELLED
    refund(order.customer, order.total)
    notify(order.customer, f"Restaurant rejected: {reason}")
```
Reasons: Out of stock, closing time, too busy. Refund immediately.

</details>

### Q3: "How to show estimated delivery time?"

<details>
<summary>👀 Click to reveal</summary>

```python
def estimated_delivery(self, order):
    prep_time = 20  # minutes (restaurant's avg)
    agent_to_restaurant = agent.location.distance_to(restaurant.location) / SPEED
    restaurant_to_customer = restaurant.location.distance_to(customer.location) / SPEED
    return prep_time + agent_to_restaurant + restaurant_to_customer
```

</details>

### Q4: "How to handle multiple cuisines/categories per restaurant?"

<details>
<summary>👀 Click to reveal</summary>

```python
class MenuItem:
    category: str  # "Biryani", "Starters", "Desserts"

class Restaurant:
    cuisines: list[str]  # ["Indian", "Chinese"]
    
    def get_menu_by_category(self, category):
        return [i for i in self.menu if i.category == category]
```

</details>

### Q5: "How to add coupon/discount system?"

<details>
<summary>👀 Click to reveal</summary>

**Strategy pattern:**
```python
class DiscountStrategy(ABC):
    def apply(self, total) -> float: pass

class PercentageDiscount(DiscountStrategy):
    def __init__(self, percent): self.percent = percent
    def apply(self, total): return total * (1 - self.percent/100)

class FlatDiscount(DiscountStrategy):
    def __init__(self, amount): self.amount = amount
    def apply(self, total): return max(0, total - self.amount)

class Coupon:
    code: str
    discount: DiscountStrategy
    min_order: float
    expires_at: datetime
```

</details>

---

## ⚠️ Comparison with Similar Problems

| Feature | BookMyShow | Uber | Food Delivery |
|---------|-----------|------|---------------|
| **Booking target** | Seats | Ride | Food items |
| **Parties** | User + Theatre | Rider + Driver | Customer + Restaurant + Agent |
| **Dynamic matching** | ❌ | ✅ Driver | ✅ Agent |
| **Pricing** | Fixed per show | Dynamic + surge | Menu price + delivery fee |
| **State transitions** | 2 (LOCKED → BOOKED) | 5 (ride states) | **6** (order states) |
| **Who confirms?** | System | Driver | **Restaurant** |

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "This is a **three-party system**: Customer, Restaurant, Delivery Agent. Orders go through 6 states — the key difference from Uber is the **Restaurant confirmation and preparation** phases. I use **OrderItem** to track MenuItem × Quantity. Agent matching works like Uber — nearest AVAILABLE agent to the restaurant. Delivery fee is distance-based. Can't cancel after pickup. **Strategy pattern** for payment and search, **Singleton** for the system."

---

## ✅ Pre-Implementation Checklist

- [ ] Enums: OrderStatus (6 states), AgentStatus
- [ ] Location with distance_to()
- [ ] MenuItem (id, name, price, is_available)
- [ ] Restaurant (menu, location, rating)
- [ ] OrderItem (MenuItem × Quantity = subtotal)
- [ ] Order (customer + restaurant + agent + items + status)
- [ ] State validation (can't cancel after OUT_FOR_DELIVERY)
- [ ] Agent matching (nearest available to restaurant)
- [ ] Delivery fee (distance × rate)
- [ ] PaymentStrategy + SearchStrategy
- [ ] Rating (restaurant + agent)
- [ ] FoodDeliverySystem singleton
- [ ] Demo: full order flow, cancellation, state validation

---

*Document created during LLD interview prep session*
