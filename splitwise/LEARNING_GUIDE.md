# 💸 SPLITWISE — Expense Sharing System
## From Zero to Interview-Ready — Complete LLD Guide

---

## 📖 Table of Contents
1. [Problem Statement & Context](#-problem-statement)
2. [Clarifying Questions](#-clarifying-questions)
3. [Requirements](#-requirements)
4. [Entity Identification](#-entity-identification)
5. [The Key Insight: Split Strategy Pattern](#-the-key-insight)
6. [Complete Class Design with Code](#-complete-class-design)
7. [Balance Tracking — Two Approaches](#-balance-tracking)
8. [Debt Simplification Algorithm](#-debt-simplification-algorithm)
9. [Design Patterns](#-design-patterns)
10. [Error Handling & Edge Cases](#-error-handling)
11. [Full Working Implementation](#-full-working-implementation)
12. [Interviewer Follow-Up Questions (15+)](#-interviewer-follow-up-questions)
13. [Comparison with Similar Problems](#-comparison)
14. [Production Scaling](#-production-scaling)
15. [Quick Recall Script](#-quick-recall)

---

## 🎯 Problem Statement

> Design an **Expense Sharing System** like Splitwise. Users create groups, add expenses with different split types (equal, exact, percentage), and the system tracks who owes whom. Minimize the number of transactions needed to settle all debts.

**Real World Context:**
Splitwise manages shared expenses among friends, roommates, and travel groups. The core challenges: (1) supporting multiple ways to split an expense, (2) maintaining a real-time balance sheet between every pair of users, (3) simplifying complex multi-person debts into minimum transactions.

**Why this is a top interview question:**
- Tests **Strategy Pattern** — multiple split algorithms with runtime selection
- Tests **algorithm design** — debt simplification is a real algorithm problem
- Tests **financial precision** — rounding, validation, split-sum invariants
- Tests **data modeling** — pairwise balances vs net balances
- Clean problem with surprising depth

---

## 🗣️ Clarifying Questions

### 🤔 THINK: Write down 10 questions before looking. Financial systems have many edge cases.

<details>
<summary>👀 Click to reveal — Complete question list</summary>

| # | Question | Why You Ask This | Answer |
|---|----------|-----------------|--------|
| 1 | "How can an expense be split?" | THE key question — reveals Strategy Pattern | Equal, Exact amounts, Percentage |
| 2 | "Can one person pay for multiple people?" | Core flow | Yes — one payer, N participants |
| 3 | "Groups?" | Scope of balances | Yes — expenses within groups |
| 4 | "Can someone pay but also owe?" | Payer is also a participant | Yes — payer owes their own share |
| 5 | "How to settle up (pay back)?" | Reduces balance | Direct payment between two users |
| 6 | "Simplify debts across group?" | Algorithm question | Yes — minimize total transactions |
| 7 | "Multi-currency?" | Extension | Discuss as follow-up |
| 8 | "Split validation?" | Exact amounts must sum to total | Yes — reject invalid splits |
| 9 | "Decimal precision?" | Financial calculations | Round to 2 decimal places |
| 10 | "Can payer be outside the group?" | Edge case | No — payer must be a participant |

</details>

---

## ✅ Requirements

### Functional Requirements

| # | FR | Priority |
|---|-----|---------|
| 1 | Register users | Must |
| 2 | Create groups with members | Must |
| 3 | Add expense: who paid, how much, split among whom | Must |
| 4 | **Split types:** Equal, Exact, Percentage | Must |
| 5 | Track pairwise balances (A owes B ₹X) | Must |
| 6 | View individual balances (net owed/owed-to) | Must |
| 7 | Settle up (partial or full payment between two users) | Must |
| 8 | Simplify group debts (minimize transactions) | Should |
| 9 | Expense history per group | Should |

### Non-Functional Requirements

| # | NFR |
|---|------|
| 1 | Validate split sums (must equal total for Exact, 100% for Percentage) |
| 2 | Handle rounding errors for odd splits (₹100 ÷ 3 = ?) |
| 3 | Thread-safe balance updates |
| 4 | Extensible — easy to add new split types |

---

## 📦 Entity Identification

### 🤔 THINK: List ALL entities. There are ~8 including the split strategies.

<details>
<summary>👀 Click to reveal — Complete entity map</summary>

| Entity | Responsibility |
|--------|---------------|
| **User** | Name, email, balance tracking |
| **Group** | Collection of users, expenses within group |
| **Expense** | Who paid, how much, split among whom, how |
| **SplitStrategy** | ABC — Equal, Exact, Percentage |
| **BalanceSheet** | Tracks pairwise balances globally |
| **SplitwiseSystem** | Singleton orchestrator |

### Entity Relationships
```
User ──has-many──→ Groups
Group ──has-many──→ Users
Group ──has-many──→ Expenses
Expense ──uses-one──→ SplitStrategy
Expense ──modifies──→ BalanceSheet
```

</details>

---

## 🔥 The Key Insight: Split Strategy Pattern

### 🤔 THINK: ₹300 dinner with 3 friends. Equal split is easy. But what about "I had the expensive dish, you had salad"?

<details>
<summary>👀 Click to reveal — Three split types with full code</summary>

**The SAME expense can be split DIFFERENTLY depending on context.** This is the Strategy Pattern.

### Strategy 1: Equal Split

```python
from abc import ABC, abstractmethod
import math

class SplitStrategy(ABC):
    """Base class for all split types."""
    
    @abstractmethod
    def validate(self, total_amount: float, num_participants: int, 
                 split_values: list[float] = None) -> bool:
        """Check if the split is valid."""
        pass
    
    @abstractmethod
    def calculate_shares(self, total_amount: float, participants: list['User'],
                        split_values: list[float] = None) -> dict['User', float]:
        """Return {user: share_amount} for each participant."""
        pass


class EqualSplit(SplitStrategy):
    """Split equally among all participants."""
    
    def validate(self, total_amount, num_participants, split_values=None):
        return total_amount > 0 and num_participants > 0
    
    def calculate_shares(self, total_amount, participants, split_values=None):
        n = len(participants)
        # Handle rounding: ₹100 ÷ 3 = 33.33, 33.33, 33.34
        base_share = math.floor(total_amount * 100 / n) / 100
        remainder = round(total_amount - base_share * n, 2)
        
        shares = {}
        for i, user in enumerate(participants):
            if i == 0:
                shares[user] = round(base_share + remainder, 2)  # First person gets the extra penny
            else:
                shares[user] = base_share
        return shares
```

### 🤔 THINK: Why not just `total / n`? What happens with ₹100 ÷ 3?

<details>
<summary>👀 Click to reveal — The rounding problem!</summary>

```
₹100 / 3 = 33.333333...

Naive: Each pays 33.33 → total = 99.99 → WHERE DID ₹0.01 GO? 💀

Our fix: 
  base = floor(100 * 100 / 3) / 100 = floor(3333.33) / 100 = 33.33
  remainder = 100 - 33.33 * 3 = 100 - 99.99 = 0.01
  Person 1 pays: 33.33 + 0.01 = 33.34
  Person 2 pays: 33.33
  Person 3 pays: 33.33
  Total: 33.34 + 33.33 + 33.33 = 100.00 ✅
```

**Always handle the rounding remainder.** In financial systems, even ₹0.01 discrepancy is a bug.

</details>

### Strategy 2: Exact Split

```python
class ExactSplit(SplitStrategy):
    """Each participant pays an exact specified amount."""
    
    def validate(self, total_amount, num_participants, split_values=None):
        if split_values is None or len(split_values) != num_participants:
            return False
        # ⚠️ Split amounts MUST sum to total
        return abs(sum(split_values) - total_amount) < 0.01
    
    def calculate_shares(self, total_amount, participants, split_values=None):
        return {participants[i]: split_values[i] for i in range(len(participants))}
```

### 🤔 THINK: Why `abs(...) < 0.01` instead of `==`?

<details>
<summary>👀 Click to reveal</summary>

**Floating point imprecision!**
```python
>>> 33.33 + 33.33 + 33.34
99.99999999999999  # NOT exactly 100.0!
```

Never compare floats with `==`. Use epsilon comparison: `abs(a - b) < 0.01`.

</details>

### Strategy 3: Percentage Split

```python
class PercentageSplit(SplitStrategy):
    """Each participant pays a percentage of the total."""
    
    def validate(self, total_amount, num_participants, split_values=None):
        if split_values is None or len(split_values) != num_participants:
            return False
        # Percentages MUST sum to 100
        return abs(sum(split_values) - 100) < 0.01
    
    def calculate_shares(self, total_amount, participants, split_values=None):
        shares = {}
        for i, user in enumerate(participants):
            shares[user] = round(total_amount * split_values[i] / 100, 2)
        
        # Fix rounding — adjust last person to make sum exact
        total_shares = sum(shares.values())
        diff = round(total_amount - total_shares, 2)
        if abs(diff) > 0:
            last_user = participants[-1]
            shares[last_user] = round(shares[last_user] + diff, 2)
        
        return shares
```

### 🤔 Why fix rounding on percentage too?

```
₹1000, percentages [33.33%, 33.33%, 33.34%]
Person 1: 1000 * 0.3333 = 333.30
Person 2: 1000 * 0.3333 = 333.30
Person 3: 1000 * 0.3334 = 333.40
Sum: 1000.00 ✅ (works here)

But: ₹999, percentages [33.33%, 33.33%, 33.34%]
Person 1: 999 * 0.3333 = 332.97
Person 2: 999 * 0.3333 = 332.97
Person 3: 999 * 0.3334 = 333.07
Sum: 999.01 → ₹0.01 EXTRA! Fix by adjusting last person.
```

</details>

---

## 🏗️ Complete Class Design

### User

```python
class User:
    def __init__(self, user_id: int, name: str, email: str):
        self.user_id = user_id
        self.name = name
        self.email = email
    
    def __str__(self):
        return f"👤 {self.name}"
    
    def __hash__(self):
        return hash(self.user_id)
    
    def __eq__(self, other):
        return isinstance(other, User) and self.user_id == other.user_id
```

### 🤔 Why `__hash__` and `__eq__`?

> Because we use User objects as **dictionary keys** in `shares` and `balances`. Python requires `__hash__` and `__eq__` to use objects as dict keys. Same pattern as Seat in BookMyShow.

### Group

```python
class Group:
    _counter = 0
    
    def __init__(self, name: str, members: list[User]):
        Group._counter += 1
        self.group_id = Group._counter
        self.name = name
        self.members = members
        self.expenses: list['Expense'] = []
    
    def add_member(self, user: User):
        if user not in self.members:
            self.members.append(user)
    
    def __str__(self):
        member_names = ", ".join(m.name for m in self.members)
        return f"👥 {self.name} ({member_names})"
```

### Expense

```python
class Expense:
    _counter = 0
    
    def __init__(self, description: str, amount: float, paid_by: User,
                 participants: list[User], strategy: SplitStrategy,
                 split_values: list[float] = None):
        Expense._counter += 1
        self.expense_id = Expense._counter
        self.description = description
        self.amount = amount
        self.paid_by = paid_by
        self.participants = participants
        self.strategy = strategy
        self.split_values = split_values
        self.created_at = datetime.now()
        
        # Calculate shares at creation time
        self.shares: dict[User, float] = strategy.calculate_shares(
            amount, participants, split_values
        )
    
    def __str__(self):
        return (f"💰 Expense#{self.expense_id}: '{self.description}' "
                f"₹{self.amount:.2f} paid by {self.paid_by.name}")
```

---

## 💰 Balance Tracking — Two Approaches

### 🤔 THINK: Alice pays ₹300 for dinner split equally among Alice, Bob, Carol. After this, what does the balance sheet look like?

<details>
<summary>👀 Think for 30 seconds, then click</summary>

```
Alice paid ₹300. Each share = ₹100.

Alice owes herself: ₹100 (but she paid, so net = ₹200 owed TO her)
Bob owes Alice: ₹100
Carol owes Alice: ₹100

Balance sheet:
  Alice: +₹200 (others owe her)
  Bob:   -₹100 (owes Alice)
  Carol: -₹100 (owes Alice)
  Net: +200 - 100 - 100 = 0 ✅ (must always be zero!)
```

</details>

### Approach 1: Pairwise Balances (Detailed view — who owes whom)

```python
class BalanceSheet:
    """
    Tracks PAIRWISE balances: balances[(A, B)] > 0 means B owes A.
    
    Uses a normalized key: always (smaller_id, larger_id) to avoid
    having both (A,B) and (B,A) entries.
    """
    
    def __init__(self):
        self.balances: dict[tuple[int, int], float] = {}
    
    def _key(self, user_a: User, user_b: User) -> tuple[int, int]:
        """Normalize: always (smaller_id, larger_id)."""
        return (min(user_a.user_id, user_b.user_id),
                max(user_a.user_id, user_b.user_id))
    
    def update(self, payer: User, shares: dict[User, float]):
        """
        After an expense: payer paid for everyone.
        Each participant (except payer) now OWES the payer their share.
        """
        for participant, share in shares.items():
            if participant == payer:
                continue  # You don't owe yourself
            
            key = self._key(payer, participant)
            current = self.balances.get(key, 0)
            
            # If payer has smaller ID → positive means participant owes payer
            if payer.user_id < participant.user_id:
                self.balances[key] = round(current + share, 2)
            else:
                self.balances[key] = round(current - share, 2)
    
    def get_balance(self, user_a: User, user_b: User) -> float:
        """
        Returns how much user_b owes user_a.
        Positive = user_b owes user_a.
        Negative = user_a owes user_b.
        """
        key = self._key(user_a, user_b)
        raw = self.balances.get(key, 0)
        if user_a.user_id < user_b.user_id:
            return raw
        return -raw
    
    def settle_up(self, payer: User, receiver: User, amount: float):
        """Payer pays receiver to reduce debt."""
        key = self._key(payer, receiver)
        current = self.balances.get(key, 0)
        
        if payer.user_id < receiver.user_id:
            self.balances[key] = round(current - amount, 2)
        else:
            self.balances[key] = round(current + amount, 2)
        
        print(f"   💸 {payer.name} paid ₹{amount:.2f} to {receiver.name}")
    
    def get_user_summary(self, user: User, all_users: list[User]) -> dict:
        """Get total owed and total owing for a user."""
        owes = 0      # This user owes others
        owed_to = 0   # Others owe this user
        details = []
        
        for other in all_users:
            if other == user:
                continue
            balance = self.get_balance(user, other)
            if balance > 0.01:
                owed_to += balance
                details.append(f"   {other.name} owes you ₹{balance:.2f}")
            elif balance < -0.01:
                owes += abs(balance)
                details.append(f"   You owe {other.name} ₹{abs(balance):.2f}")
        
        return {"owes": owes, "owed_to": owed_to, "details": details}
    
    def display(self, all_users: list[User]):
        """Print complete balance sheet."""
        print("\n   ┌──────────── BALANCE SHEET ────────────┐")
        for user in all_users:
            summary = self.get_user_summary(user, all_users)
            net = summary["owed_to"] - summary["owes"]
            emoji = "🟢" if net >= 0 else "🔴"
            print(f"   │ {emoji} {user.name}: net ₹{net:+.2f}")
            for detail in summary["details"]:
                print(f"   │   {detail}")
        print("   └────────────────────────────────────────┘")
```

### 🤔 Why normalized keys?

<details>
<summary>👀 Click to reveal</summary>

**Without normalization:**
```python
balances[(Alice, Bob)] = 100   # Alice is owed 100 by Bob
balances[(Bob, Alice)] = -100  # Duplicate! Same info, different sign
```

Now you have TWO entries for the same relationship. Update one, forget the other → inconsistency.

**With normalization:** Always `(smaller_id, larger_id)`. One entry per pair. No duplication.

```python
balances[(1, 2)] = 100  # User 1 is owed 100 by User 2 (positive = first owes second? or reverse?)
```

Convention: `balances[(A, B)] > 0` means **B owes A** (when A has smaller ID).

</details>

### Approach 2: Net Balance Per User (For Simplification)

```python
def get_net_balances(self, users: list[User]) -> dict[User, float]:
    """
    Calculate net balance per user (for debt simplification).
    Positive = owed money (creditor)
    Negative = owes money (debtor)
    """
    net = {user: 0.0 for user in users}
    
    for user in users:
        summary = self.get_user_summary(user, users)
        net[user] = round(summary["owed_to"] - summary["owes"], 2)
    
    return net
```

---

## 🧮 Debt Simplification Algorithm — The Core Algorithm

### 🤔 THINK: 4 friends, 6 pairwise debts. What's the minimum number of payments to settle everything?

<details>
<summary>👀 Consider this example, then click</summary>

**Before simplification — 5 pairwise debts:**
```
Alice owes Bob:   ₹100
Alice owes Carol: ₹50
Bob owes Carol:   ₹80
Bob owes Dave:    ₹30
Carol owes Dave:  ₹20
```

**Step 1: Calculate NET balance per person**
```
Alice: paid 0, owes 100+50 = 150     → net: -150 (debtor)
Bob:   gets 100, owes 80+30 = 110    → net: -10  (debtor)
Carol: gets 50+80, owes 20 = 20      → net: +110 (creditor)
Dave:  gets 30+20 = 50               → net: +50  (creditor)

Check: -150 + (-10) + 110 + 50 = 0 ✅ (must ALWAYS be zero!)
```

**Step 2: Separate into debtors and creditors**
```
Debtors (owe money):   Alice: -150,  Bob: -10
Creditors (owed money): Carol: +110,  Dave: +50
```

**Step 3: Greedy matching — settle largest amounts first**
```
Transaction 1: Alice (-150) pays Carol (+110) → ₹110
               Alice: -40 remaining,  Carol: settled ✅

Transaction 2: Alice (-40) pays Dave (+50) → ₹40
               Alice: settled ✅,  Dave: +10 remaining

Transaction 3: Bob (-10) pays Dave (+10) → ₹10
               Bob: settled ✅,  Dave: settled ✅
```

**Result: 3 transactions** (down from 5 pairwise debts!) 🎉

</details>

### Complete Implementation

```python
def simplify_debts(self, users: list[User]) -> list[tuple[User, User, float]]:
    """
    Minimize the number of transactions to settle all debts.
    
    Algorithm:
    1. Calculate net balance per person
    2. Separate into debtors (negative) and creditors (positive)
    3. Greedy: match largest debtor with largest creditor
    4. Repeat until all settled
    
    Returns: list of (payer, receiver, amount) — minimum transactions
    """
    # Step 1: Net balances
    net = self.balance_sheet.get_net_balances(users)
    
    # Step 2: Separate
    debtors = []    # [(user, amount_they_owe)]  — amount is POSITIVE
    creditors = []  # [(user, amount_owed_to_them)]
    
    for user, balance in net.items():
        if balance < -0.01:
            debtors.append([user, round(-balance, 2)])    # Make positive
        elif balance > 0.01:
            creditors.append([user, round(balance, 2)])
    
    # Step 3: Sort by amount (largest first) for greedy matching
    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)
    
    # Step 4: Greedy matching
    transactions = []
    i, j = 0, 0
    
    while i < len(debtors) and j < len(creditors):
        debtor_user, debt_amount = debtors[i]
        creditor_user, credit_amount = creditors[j]
        
        # Settle the smaller of the two
        settle_amount = round(min(debt_amount, credit_amount), 2)
        transactions.append((debtor_user, creditor_user, settle_amount))
        
        # Update remaining amounts
        debtors[i][1] = round(debt_amount - settle_amount, 2)
        creditors[j][1] = round(credit_amount - settle_amount, 2)
        
        # Move to next if fully settled
        if debtors[i][1] < 0.01:
            i += 1
        if creditors[j][1] < 0.01:
            j += 1
    
    return transactions
```

### 🤔 THINK: Is the greedy approach always optimal (minimum transactions)?

<details>
<summary>👀 Click to reveal — Important interview question!</summary>

**No!** The minimum number of transactions is actually an NP-hard problem (related to set partition).

**Example where greedy is suboptimal:**
```
A: -5, B: -5, C: +3, D: +3, E: +4

Greedy: A→E(4), A→C(1), B→D(3), B→C(2) = 4 transactions

Optimal: A→C(3), A→D(2), B→D(1), B→E(4) = 4 transactions
         OR: A→C(3), A→E(2), B→E(2), B→D(3) = 4 transactions

Actually equal here! But for certain distributions, greedy gives N-1 transactions 
while optimal might give fewer (involves subset-sum to find groups that cancel out).
```

**For interviews:** Greedy is O(n log n) and produces good-enough results. Mention that true optimal is NP-hard and requires subset-sum optimization. Real Splitwise uses greedy.

**Upper bound:** For N people, you need at most **N-1 transactions** (one person settles with everyone else). Greedy usually does much better.

</details>

---

## 💡 Design Patterns

| Pattern | Where | Why | Alternative |
|---------|-------|-----|-------------|
| **Strategy** | SplitStrategy (Equal, Exact, Percentage) | Swap split algorithm at runtime | if-else on split type (violates OCP) |
| **Singleton** | SplitwiseSystem | One global system | None needed |
| **Observer** (optional) | Notify affected users when expense is added | Decouple notification | Polling |
| **Factory** (optional) | Create appropriate SplitStrategy from type enum | Decouple creation | Direct instantiation |

### Factory for Strategy Creation

```python
class SplitType(Enum):
    EQUAL = 1
    EXACT = 2
    PERCENTAGE = 3

class SplitFactory:
    @staticmethod
    def create(split_type: SplitType) -> SplitStrategy:
        strategies = {
            SplitType.EQUAL: EqualSplit(),
            SplitType.EXACT: ExactSplit(),
            SplitType.PERCENTAGE: PercentageSplit(),
        }
        strategy = strategies.get(split_type)
        if not strategy:
            raise ValueError(f"Unknown split type: {split_type}")
        return strategy
```

---

## ⚠️ Error Handling & Edge Cases

| Edge Case | How to Handle |
|-----------|---------------|
| Exact split amounts don't sum to total | `validate()` returns False, reject expense |
| Percentage split doesn't sum to 100% | `validate()` returns False, reject expense |
| ₹100 ÷ 3 rounding | First person pays 33.34, others 33.33 |
| Payer not in participants | Add payer to participants (payer's share = ₹0 if they only paid) |
| Self-expense (1 participant = payer) | Valid but no balance changes |
| Negative amount | Reject: `if amount <= 0: return None` |
| Zero participants | Reject: `if len(participants) == 0: return None` |
| Settle more than owed | Cap at the amount actually owed |
| User not in group | Reject: check membership before adding expense |
| Float precision drift | Use `round(x, 2)` on every calculation |

---

## 🔧 Full Working Implementation

### SplitwiseSystem — Complete Orchestrator

```python
import threading
from datetime import datetime
from abc import ABC, abstractmethod
from enum import Enum
import math


class SplitwiseSystem:
    """Singleton system managing all users, groups, and expenses."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.users: dict[int, User] = {}
        self.groups: dict[int, Group] = {}
        self.balance_sheet = BalanceSheet()
        self._lock = threading.Lock()
    
    # ──── User Management ────
    def register_user(self, user_id: int, name: str, email: str) -> User:
        user = User(user_id, name, email)
        self.users[user_id] = user
        print(f"   ✅ Registered: {user}")
        return user
    
    # ──── Group Management ────
    def create_group(self, name: str, member_ids: list[int]) -> Group:
        members = [self.users[uid] for uid in member_ids if uid in self.users]
        group = Group(name, members)
        self.groups[group.group_id] = group
        print(f"   ✅ Created group: {group}")
        return group
    
    # ──── Add Expense ────
    def add_expense(self, group_id: int, description: str, amount: float,
                    paid_by_id: int, participant_ids: list[int],
                    split_type: SplitType,
                    split_values: list[float] = None) -> Expense | None:
        """
        Core method: Add an expense and update balances.
        
        Args:
            group_id: Which group this expense belongs to
            description: "Dinner at Pizza Hut"
            amount: Total amount paid
            paid_by_id: Who paid the bill
            participant_ids: Who was part of the expense
            split_type: EQUAL, EXACT, or PERCENTAGE
            split_values: For EXACT/PERCENTAGE — amounts or percentages per person
        """
        with self._lock:
            group = self.groups.get(group_id)
            if not group:
                print("   ❌ Group not found!")
                return None
            
            payer = self.users.get(paid_by_id)
            participants = [self.users[uid] for uid in participant_ids]
            
            if not payer or not participants:
                print("   ❌ Invalid users!")
                return None
            
            if amount <= 0:
                print("   ❌ Amount must be positive!")
                return None
            
            # Create strategy and validate
            strategy = SplitFactory.create(split_type)
            if not strategy.validate(amount, len(participants), split_values):
                print(f"   ❌ Invalid {split_type.name} split! "
                      f"Values must sum to {'amount' if split_type == SplitType.EXACT else '100%'}")
                return None
            
            # Create expense
            expense = Expense(description, amount, payer, participants,
                            strategy, split_values)
            group.expenses.append(expense)
            
            # Update balance sheet
            self.balance_sheet.update(payer, expense.shares)
            
            # Display
            print(f"\n   ✅ {expense}")
            for user, share in expense.shares.items():
                if user != payer:
                    print(f"      {user.name} owes ₹{share:.2f}")
            
            return expense
    
    # ──── Settle Up ────
    def settle_up(self, payer_id: int, receiver_id: int, amount: float):
        payer = self.users.get(payer_id)
        receiver = self.users.get(receiver_id)
        
        if not payer or not receiver:
            print("   ❌ Invalid users!")
            return
        
        owed = self.balance_sheet.get_balance(receiver, payer)
        if owed <= 0:
            print(f"   ❌ {payer.name} doesn't owe {receiver.name} anything!")
            return
        
        actual_amount = min(amount, owed)
        self.balance_sheet.settle_up(payer, receiver, actual_amount)
        
        remaining = round(owed - actual_amount, 2)
        if remaining > 0:
            print(f"   💰 Remaining: {payer.name} still owes {receiver.name} ₹{remaining:.2f}")
        else:
            print(f"   ✅ {payer.name} and {receiver.name} are settled!")
    
    # ──── Simplify Debts ────
    def simplify_debts(self, group_id: int) -> list[tuple]:
        group = self.groups.get(group_id)
        if not group:
            return []
        
        transactions = self._simplify(group.members)
        
        print(f"\n   ┌──── SIMPLIFIED DEBTS for '{group.name}' ────┐")
        for payer, receiver, amount in transactions:
            print(f"   │  {payer.name} ──₹{amount:.2f}──→ {receiver.name}")
        print(f"   │  Total transactions: {len(transactions)}")
        print(f"   └──────────────────────────────────────────────┘")
        
        return transactions
    
    def _simplify(self, users):
        net = self.balance_sheet.get_net_balances(users)
        
        debtors = []
        creditors = []
        for user, balance in net.items():
            if balance < -0.01:
                debtors.append([user, round(-balance, 2)])
            elif balance > 0.01:
                creditors.append([user, round(balance, 2)])
        
        debtors.sort(key=lambda x: x[1], reverse=True)
        creditors.sort(key=lambda x: x[1], reverse=True)
        
        transactions = []
        i, j = 0, 0
        while i < len(debtors) and j < len(creditors):
            settle = round(min(debtors[i][1], creditors[j][1]), 2)
            transactions.append((debtors[i][0], creditors[j][0], settle))
            debtors[i][1] = round(debtors[i][1] - settle, 2)
            creditors[j][1] = round(creditors[j][1] - settle, 2)
            if debtors[i][1] < 0.01: i += 1
            if creditors[j][1] < 0.01: j += 1
        
        return transactions
    
    # ──── View Balances ────
    def show_balances(self, user_id: int = None):
        if user_id:
            user = self.users[user_id]
            summary = self.balance_sheet.get_user_summary(user, list(self.users.values()))
            print(f"\n   ── {user.name}'s Balances ──")
            for detail in summary["details"]:
                print(detail)
            if not summary["details"]:
                print("   All settled! ✅")
        else:
            self.balance_sheet.display(list(self.users.values()))


# ═══════════════════════════════════════════════
#                    DEMO
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("        SPLITWISE SYSTEM - COMPLETE DEMO")
    print("=" * 60)
    
    system = SplitwiseSystem()
    
    # Register users
    print("\n--- Register Users ---")
    alice = system.register_user(1, "Alice", "alice@mail.com")
    bob = system.register_user(2, "Bob", "bob@mail.com")
    carol = system.register_user(3, "Carol", "carol@mail.com")
    dave = system.register_user(4, "Dave", "dave@mail.com")
    
    # Create group
    print("\n--- Create Group ---")
    group = system.create_group("Weekend Trip", [1, 2, 3, 4])
    
    # Test 1: Equal split
    print("\n--- Test 1: Equal Split ---")
    system.add_expense(group.group_id, "Hotel", 4000, 1, [1, 2, 3, 4], SplitType.EQUAL)
    
    # Test 2: Exact split
    print("\n--- Test 2: Exact Split ---")
    system.add_expense(group.group_id, "Dinner", 3000, 2, [1, 2, 3, 4],
                       SplitType.EXACT, [500, 1000, 800, 700])
    
    # Test 3: Percentage split
    print("\n--- Test 3: Percentage Split ---")
    system.add_expense(group.group_id, "Activities", 2000, 3, [1, 2, 3, 4],
                       SplitType.PERCENTAGE, [20, 30, 25, 25])
    
    # Show balances
    print("\n--- Current Balances ---")
    system.show_balances()
    
    # Simplify debts
    print("\n--- Simplify Debts ---")
    transactions = system.simplify_debts(group.group_id)
    
    # Test 4: Invalid splits
    print("\n--- Test 4: Invalid Split Validation ---")
    system.add_expense(group.group_id, "Bad Split", 1000, 1, [1, 2, 3],
                       SplitType.EXACT, [300, 300, 300])  # Sums to 900, not 1000!
    
    system.add_expense(group.group_id, "Bad %", 1000, 1, [1, 2, 3],
                       SplitType.PERCENTAGE, [40, 40, 10])  # Sums to 90%, not 100!
    
    # Test 5: Settle up
    print("\n--- Test 5: Settle Up ---")
    if transactions:
        payer, receiver, amount = transactions[0]
        system.settle_up(payer.user_id, receiver.user_id, amount)
    
    print("\n" + "=" * 60)
    print("        ALL TESTS COMPLETE! 🎉")
    print("=" * 60)
```

---

## 🎤 Interviewer Follow-Up Questions (15+)

### Q1: "How to handle multi-currency expenses?"

<details>
<summary>👀 Click to reveal</summary>

```python
class Expense:
    currency: str = "INR"
    exchange_rate: float = 1.0  # To base currency (INR)

# All balances stored in base currency
# Display in original currency with conversion
def add_expense(self, ..., currency="INR"):
    rate = self.exchange_rates.get(currency, 1.0)
    amount_in_base = amount * rate
    # Split in base currency
    shares = strategy.calculate_shares(amount_in_base, participants, split_values)
```

Show: "₹100 expense in USD → converted to INR at current rate → balances in INR."

</details>

### Q2: "How to edit or delete an expense?"

<details>
<summary>👀 Click to reveal</summary>

```python
def delete_expense(self, expense_id):
    expense = self._find_expense(expense_id)
    
    # REVERSE the balance updates
    reverse_shares = {user: -share for user, share in expense.shares.items()}
    self.balance_sheet.update(expense.paid_by, reverse_shares)
    
    # Remove from group
    expense.group.expenses.remove(expense)
```

Edit = delete old + add new. Never try to "calculate the difference" — too error-prone.

</details>

### Q3: "What if the payer is not one of the participants?"

<details>
<summary>👀 Click to reveal</summary>

```python
# Example: Boss pays ₹1000 for dinner but doesn't eat
# Boss is owed ₹1000 total, split among participants

# Our code already handles this:
# shares = {Alice: 250, Bob: 250, Carol: 250, Dave: 250}
# balance_sheet.update(Boss, shares)
# → Boss doesn't appear in shares, so he's purely owed money

# But: validate that payer IS in the group
```

</details>

### Q4: "How to add recurring expenses?"

<details>
<summary>👀 Click to reveal</summary>

```python
class RecurringExpense:
    def __init__(self, template_expense, frequency_days):
        self.template = template_expense
        self.frequency_days = frequency_days
        self.next_due = datetime.now() + timedelta(days=frequency_days)
    
    def trigger(self, system):
        # Create a new expense based on template
        system.add_expense(
            self.template.group_id,
            self.template.description + " (recurring)",
            self.template.amount,
            self.template.paid_by.user_id,
            [p.user_id for p in self.template.participants],
            self.template.split_type
        )
        self.next_due += timedelta(days=self.frequency_days)
```

Use case: Monthly rent, weekly grocery runs.

</details>

### Q5: "How to handle partial participation?"

<details>
<summary>👀 Click to reveal</summary>

```python
# Example: Group of 5, but only 3 people ordered drinks
# Just specify participants = [Alice, Bob, Carol] (not everyone in group)
# The strategy splits only among specified participants

# Our add_expense already supports this:
# participant_ids can be a SUBSET of group members
```

</details>

### Q6: "How to generate monthly expense reports?"

<details>
<summary>👀 Click to reveal</summary>

```python
def monthly_report(self, group_id, year, month):
    group = self.groups[group_id]
    monthly = [e for e in group.expenses
               if e.created_at.year == year and e.created_at.month == month]
    
    total = sum(e.amount for e in monthly)
    per_user = {}
    for e in monthly:
        per_user[e.paid_by.name] = per_user.get(e.paid_by.name, 0) + e.amount
    
    print(f"Month: {year}-{month}")
    print(f"Total spent: ₹{total:.2f}")
    print(f"Expenses: {len(monthly)}")
    for name, amount in per_user.items():
        print(f"  {name} paid: ₹{amount:.2f}")
```

</details>

### Q7: "Activity feed — who should be notified?"

<details>
<summary>👀 Click to reveal</summary>

```python
# When expense added → notify ALL affected users
# Observer pattern:
class ExpenseObserver(ABC):
    @abstractmethod
    def on_expense_added(self, expense): pass

class EmailNotifier(ExpenseObserver):
    def on_expense_added(self, expense):
        for user, share in expense.shares.items():
            if user != expense.paid_by:
                send_email(user.email, 
                          f"You owe {expense.paid_by.name} ₹{share:.2f}")
```

</details>

### Q8: "How does the balance change when the same two people keep splitting?"

<details>
<summary>👀 Click to reveal — Complete trace</summary>

```
Start: Alice and Bob, balance = 0

Expense 1: Alice pays ₹200, split equally (Alice+Bob)
  Bob's share: 100 → Bob owes Alice ₹100
  Pairwise: Alice → Bob = +100

Expense 2: Bob pays ₹300, split equally (Alice+Bob)
  Alice's share: 150 → Alice owes Bob ₹150
  Pairwise: Alice → Bob = +100 - 150 = -50

Net: Alice owes Bob ₹50 (sign flipped!)

Settle: Alice pays Bob ₹50 → balance = 0 ✅
```

Running balance — each expense either increases or decreases the pairwise balance.

</details>

### Q9-15 (Quick)

| Q | Question | Key Answer |
|---|----------|-----------|
| 9 | "Debt simplification — is greedy always optimal?" | No — optimal is NP-hard. Greedy is O(n log n) and good enough |
| 10 | "Can a group have overlapping members with another group?" | Yes — user appears in multiple groups. Balances tracked globally |
| 11 | "Offline support?" | Queue operations locally, sync when online. Conflict resolution on merge |
| 12 | "Why not store balance on User?" | User can be in multiple groups. Balance is per-pair, not per-user |
| 13 | "How to add notes/receipts to expense?" | `Expense.note: str`, `Expense.receipt_url: str` |
| 14 | "Concurrency?" | `threading.Lock` on `add_expense` and `settle_up` |
| 15 | "How to handle payment integrations?" | Deep link to UPI/PayTM for settle-up amount |

---

## 📊 Comparison with Similar Problems

| Feature | Splitwise | Parking Lot | BookMyShow |
|---------|----------|-------------|-----------|
| **Core pattern** | Strategy (split types) | Strategy (payment) | Strategy (search + payment) |
| **Key algorithm** | Debt simplification | Spot assignment | Seat locking |
| **State tracking** | Pairwise balances | Spot occupied/free | Seat available/locked/booked |
| **Validation** | Split sums | Vehicle-spot match | Seat availability |
| **Concurrency** | Balance update lock | Spot assignment lock | Seat lock + expiry |
| **Financial precision** | ✅ Critical | Fee calculation | Fixed pricing |

---

## 🌐 Production Scaling

| Concern | Solution |
|---------|----------|
| Balance accuracy | **Decimal arithmetic** (not float) — `from decimal import Decimal` |
| Concurrent updates | **Database transactions** with row-level locking |
| Real-time sync | **WebSocket** for live balance updates |
| Expense storage | **PostgreSQL** for relational data |
| Simple debts cache | **Redis** for quick net balance lookup |
| Notifications | **Push notifications** via Firebase |
| Receipt scanning | **OCR** to auto-extract amount, split equally |
| International | **Multi-currency** with live exchange rates via API |

---

## 🧠 Quick Recall Script

> **First 30 seconds:**
> "Splitwise uses **Strategy pattern** for split types — Equal, Exact, Percentage. Each strategy validates (Exact sums to total, Percentage sums to 100%) and calculates shares. Balances are tracked pairwise with a normalized key `(min_id, max_id)`. The key algorithm is **debt simplification** — calculate net balance per person, separate debtors and creditors, greedily match largest debtor with largest creditor."

> **If they ask about rounding:**
> "₹100 ÷ 3: base = 33.33, remainder = 0.01 goes to first person. For percentages, adjust last person to fix rounding drift. Always use `round(x, 2)` and compare with `abs(a-b) < 0.01`."

> **If they ask about optimal simplification:**
> "Greedy is O(n log n) and works in practice. True minimum transactions is NP-hard (subset-sum related). For N people, upper bound is N-1 transactions."

> **If they ask about patterns:**
> "**Strategy** for splits, **Singleton** for the system, **Factory** for strategy creation, **Observer** for notifications."

---

## ✅ Pre-Implementation Checklist

- [ ] User class with `__hash__` and `__eq__` (used as dict key)
- [ ] SplitStrategy ABC → EqualSplit, ExactSplit, PercentageSplit
- [ ] EqualSplit handles rounding remainder (₹100 ÷ 3)
- [ ] ExactSplit validates sum equals amount
- [ ] PercentageSplit validates sum equals 100%, fixes rounding
- [ ] Expense (description, amount, paid_by, participants, shares)
- [ ] BalanceSheet — pairwise with normalized key
- [ ] BalanceSheet.update() — after each expense
- [ ] BalanceSheet.settle_up() — reduce debt
- [ ] BalanceSheet.get_user_summary() — total owed/owing
- [ ] Debt simplification — net balances → greedy matching
- [ ] Group with members and expenses
- [ ] SplitwiseSystem singleton with Lock
- [ ] SplitFactory for strategy creation
- [ ] Demo: equal split, exact split, percentage split, invalid validation, simplify, settle

---

*Version 3.0 — Truly Comprehensive Edition*
