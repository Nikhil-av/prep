# 🏧 ATM MACHINE — LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design an **ATM Machine** that supports authentication, balance inquiry, cash withdrawal, cash deposit, and fund transfer.

---

## 🤔 THINK: Before Reading Further...
**Which design pattern is this problem REALLY about?**

<details>
<summary>👀 Click to reveal</summary>

**State Pattern!** An ATM is a classic **finite state machine**:

```
IDLE → INSERT_CARD → PIN_ENTRY → AUTHENTICATED → TRANSACTION → IDLE
```

Each state has different valid operations. You can't withdraw before entering PIN. You can't enter PIN without inserting a card.

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | Insert card → validate card |
| 2 | Enter PIN → authenticate |
| 3 | Balance inquiry |
| 4 | Cash withdrawal (check balance + dispense) |
| 5 | Cash deposit |
| 6 | Fund transfer |
| 7 | Eject card / return to idle |

---

## 🔥 THE KEY INSIGHT: State Pattern

### 🤔 THINK: How do you prevent "withdraw without PIN" bugs?

<details>
<summary>👀 Click to reveal</summary>

**Each state class only implements valid operations:**

```python
class ATMState(ABC):
    @abstractmethod
    def insert_card(self, atm): pass
    @abstractmethod
    def enter_pin(self, atm, pin): pass
    @abstractmethod
    def withdraw(self, atm, amount): pass
    # ... default: print("Invalid operation in this state")

class IdleState(ATMState):
    def insert_card(self, atm):
        atm.set_state(HasCardState())  # ✅ Valid
    def withdraw(self, atm, amount):
        print("Insert card first!")     # ❌ Invalid in this state

class HasCardState(ATMState):
    def enter_pin(self, atm, pin):
        if atm.bank.validate_pin(pin):
            atm.set_state(AuthenticatedState())  # ✅
    def withdraw(self, atm, amount):
        print("Enter PIN first!")                 # ❌

class AuthenticatedState(ATMState):
    def withdraw(self, atm, amount):
        if atm.cash_available >= amount and atm.account.balance >= amount:
            atm.dispense(amount)       # ✅ Now it works!
```

**Interviewer will love this** — it's clean, extensible, and prevents invalid operations by design.

</details>

---

## 📊 State Machine

```
         insert_card()     enter_pin()       select_txn()        done()
IDLE ──────────→ HAS_CARD ──────────→ AUTHENTICATED ──────────→ TRANSACTION ──→ IDLE
  ↑                  │                     │                         │
  │                  │ eject_card()         │ eject_card()            │
  └──────────────────┴─────────────────────┘                         │
  ↑                                                                  │
  └──────────────────────────────────────────────────────────────────┘
```

---

## 📦 Core Entities

<details>
<summary>👀 Click to reveal</summary>

| Entity | Purpose |
|--------|---------|
| **ATMState (ABC)** | Abstract state with all operations |
| **IdleState, HasCardState, AuthenticatedState, TransactionState** | Concrete states |
| **ATM** | Context — holds current state, cash, connected bank |
| **Card** | card_number, pin, account |
| **Account** | account_number, balance, withdraw(), deposit() |
| **Bank** | accounts[], validate_pin(), process_transaction() |
| **Transaction** | type, amount, timestamp, status |

</details>

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How does the ATM dispense exact denominations?"

<details>
<summary>👀 Click to reveal</summary>

**Chain of Responsibility** for denomination dispensing:
```python
class CashDispenser:
    denominations = [2000, 500, 200, 100]  # Indian currency
    
    def dispense(self, amount):
        notes = {}
        remaining = amount
        for denom in self.denominations:
            count = remaining // denom
            if count > 0:
                notes[denom] = count
                remaining -= count * denom
        if remaining > 0:
            raise Exception("Cannot dispense exact amount")
        return notes
```

</details>

### Q2: "How to handle ATM running out of cash?"

<details>
<summary>👀 Click to reveal</summary>

Track `cash_available` per denomination. Before dispensing, check if sufficient notes exist. If not: "Cannot dispense, try a different amount" or "ATM out of service".

</details>

### Q3: "How to make it thread-safe for multiple ATMs sharing one bank?"

<details>
<summary>👀 Click to reveal</summary>

Lock on account for withdraw/deposit:
```python
class Account:
    def withdraw(self, amount):
        with self._lock:
            if self.balance >= amount:
                self.balance -= amount
                return True
            return False
```

</details>

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "ATM is a classic **State Pattern** problem. States: IDLE → HAS_CARD → AUTHENTICATED → TRANSACTION → IDLE. Each state class implements only valid operations — prevents illegal actions by design. The ATM context holds current state and delegates operations. Cash dispensing uses **Chain of Responsibility** for denominations. Account operations are thread-safe with locks."

---

*Document created during LLD interview prep session*
