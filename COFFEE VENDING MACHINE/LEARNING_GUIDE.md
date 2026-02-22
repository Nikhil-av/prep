# ☕ COFFEE VENDING MACHINE — LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design a **Coffee Vending Machine** that makes different types of coffee, manages inventory of ingredients, accepts payment, and dispenses drinks.

---

## 🤔 THINK: Before Reading Further...
**Which design pattern is this problem REALLY about?**

<details>
<summary>👀 Click to reveal</summary>

**State Pattern!** (Same as ATM)

```
IDLE → SELECTING_DRINK → PAYMENT → DISPENSING → IDLE
```

Plus **Builder/Strategy** for creating drinks:
- Each drink has a different recipe (ingredients + quantities)
- Strategy for drink recipes OR a recipe config dict

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | Display available drinks |
| 2 | Select a drink |
| 3 | Show price, accept payment |
| 4 | Check ingredient availability |
| 5 | Dispense drink (deduct ingredients) |
| 6 | Refund if insufficient ingredients |
| 7 | Admin: refill ingredients |

---

## 🔥 THE KEY INSIGHT: Recipe as Config

### 🤔 THINK: How to define what goes into each coffee?

<details>
<summary>👀 Click to reveal</summary>

**Recipe = dict of ingredient → quantity needed:**
```python
RECIPES = {
    DrinkType.ESPRESSO:    {"coffee": 2, "water": 1},
    DrinkType.LATTE:       {"coffee": 2, "milk": 3, "water": 1},
    DrinkType.CAPPUCCINO:  {"coffee": 2, "milk": 2, "foam": 1, "water": 1},
    DrinkType.HOT_CHOCOLATE: {"chocolate": 3, "milk": 3, "water": 1},
}

PRICES = {
    DrinkType.ESPRESSO: 50,
    DrinkType.LATTE: 80,
    DrinkType.CAPPUCCINO: 90,
    DrinkType.HOT_CHOCOLATE: 70,
}
```

**To add a new drink** → just add to RECIPES and PRICES. No code changes! **Open/Closed.**

</details>

---

## 📊 Dispensing Flow

```python
def make_drink(self, drink_type, payment):
    recipe = RECIPES[drink_type]
    
    # Check inventory
    for ingredient, qty in recipe.items():
        if self.inventory[ingredient] < qty:
            return f"Out of {ingredient}!"
    
    # Accept payment
    price = PRICES[drink_type]
    if payment < price:
        return f"Need ₹{price - payment} more"
    
    # Deduct ingredients
    for ingredient, qty in recipe.items():
        self.inventory[ingredient] -= qty
    
    # Dispense
    change = payment - price
    return f"☕ {drink_type.name} dispensed! Change: ₹{change}"
```

---

## 📦 Core Entities

| Entity | Purpose |
|--------|---------|
| **DrinkType (Enum)** | ESPRESSO, LATTE, CAPPUCCINO, etc. |
| **MachineState (Enum)** | IDLE, SELECTING, PAYMENT, DISPENSING |
| **Inventory** | dict[ingredient, quantity] |
| **VendingMachine** | state, inventory, recipes, dispense() |

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How to add customizations (extra sugar, no milk)?"

<details>
<summary>👀 Click to reveal</summary>

**Decorator pattern** for drink customization:
```python
class Drink:
    def cost(self): return PRICES[self.type]
    def description(self): return self.type.name

class ExtraSugarDecorator(Drink):
    def __init__(self, drink):
        self.drink = drink
    def cost(self): return self.drink.cost() + 10
    def description(self): return self.drink.description() + " + Extra Sugar"
```

Or simpler: add `customizations: dict` to the order.

</details>

### Q2: "How to handle multiple payments (coins + card)?"

<details>
<summary>👀 Click to reveal</summary>

Strategy pattern for payment. Track total received:
```python
class PaymentProcessor:
    def __init__(self):
        self.received = 0
    
    def add_payment(self, amount, strategy: PaymentStrategy):
        strategy.pay(amount)
        self.received += amount
    
    def is_sufficient(self, price):
        return self.received >= price
```

</details>

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "I'd use **State Pattern** for the machine lifecycle (IDLE → SELECTING → PAYMENT → DISPENSING → IDLE). Drink recipes are stored as **config dicts** mapping ingredients to quantities — adding a new drink means adding one dict entry. Before dispensing, check inventory. After dispensing, deduct ingredients. For customizations, I'd use the **Decorator pattern**."

---

*Document created during LLD interview prep session*
