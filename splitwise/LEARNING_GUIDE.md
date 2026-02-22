# 💸 SPLITWISE — Expense Sharing LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design a **Splitwise-like expense sharing system**. Users create groups, add expenses (split equally, by percentage, or exact amounts), and the system calculates who owes whom.

---

## 🤔 THINK: Before Reading Further...
**What's the hardest part of Splitwise? It's not splitting — it's simplification!**

<details>
<summary>👀 Click to reveal</summary>

Splitting ₹300 among 3 people is easy. The HARD part:
- A owes B ₹100, B owes C ₹50, C owes A ₹30
- **Simplify to minimum transactions:** A→B ₹70, A→C ₹20 (just 2 transactions instead of 3!)

This is the **debt simplification** algorithm — the key interview question.

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | Register users |
| 2 | Create groups |
| 3 | Add expense — paid by one, split among many |
| 4 | **Split types**: Equal, Exact amount, Percentage |
| 5 | Track balances: who owes whom how much |
| 6 | **Simplify debts** — minimize number of transactions |
| 7 | View balance sheet per user |

---

## 🔥 THE KEY INSIGHT: Split Strategies

### 🤔 THINK: How would you split ₹1000 among 3 people — equally, by exact amounts, and by percentage?

<details>
<summary>👀 Click to reveal</summary>

**Strategy pattern!**
```python
class SplitStrategy(ABC):
    @abstractmethod
    def split(self, amount: float, users: list, splits: list) -> dict[User, float]:
        pass

class EqualSplit(SplitStrategy):
    def split(self, amount, users, splits=None):
        per_person = amount / len(users)
        return {user: per_person for user in users}

class ExactSplit(SplitStrategy):
    def split(self, amount, users, splits):
        # splits = [300, 400, 300] — must sum to amount!
        assert abs(sum(splits) - amount) < 0.01
        return {users[i]: splits[i] for i in range(len(users))}

class PercentageSplit(SplitStrategy):
    def split(self, amount, users, splits):
        # splits = [50, 30, 20] — must sum to 100!
        assert abs(sum(splits) - 100) < 0.01
        return {users[i]: amount * splits[i] / 100 for i in range(len(users))}
```

</details>

---

## 💰 Debt Simplification Algorithm

### 🤔 THINK: A owes B ₹100, B owes C ₹80, A owes C ₹50. How to minimize transactions?

<details>
<summary>👀 Click to reveal</summary>

**Step 1: Calculate net balance per person**
```
A: -150 (owes 100+50)
B: +20  (gets 100, owes 80)
C: +130 (gets 80+50)
```

**Step 2: Greedy — match biggest debtor with biggest creditor**
```
A (-150) pays C (+130) → A pays C ₹130 → A=-20, C=0
A (-20) pays B (+20)   → A pays B ₹20  → A=0, B=0
```
Result: **2 transactions** instead of 3!

```python
def simplify_debts(self, balances: dict[User, float]):
    debtors = [(user, -bal) for user, bal in balances.items() if bal < 0]
    creditors = [(user, bal) for user, bal in balances.items() if bal > 0]
    
    # Sort: biggest amounts first
    debtors.sort(key=lambda x: x[1], reverse=True)
    creditors.sort(key=lambda x: x[1], reverse=True)
    
    transactions = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor, debt = debtors[i]
        creditor, credit = creditors[j]
        settle = min(debt, credit)
        transactions.append((debtor, creditor, settle))
        debtors[i] = (debtor, debt - settle)
        creditors[j] = (creditor, credit - settle)
        if debtors[i][1] == 0: i += 1
        if creditors[j][1] == 0: j += 1
    
    return transactions
```

</details>

---

## 🔗 Entity Relationships

```
Splitwise (Singleton)
    ├── users: dict[id, User]
    ├── groups: dict[id, Group]
    └── expenses: list[Expense]

Group
    ├── members: list[User]
    └── expenses: list[Expense]

Expense
    ├── paid_by: User
    ├── amount: float
    ├── split_strategy: SplitStrategy
    ├── splits: dict[User, float]  (how much each person owes)
    └── group: Group
```

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How to track who owes whom in real-time?"

<details>
<summary>👀 Click to reveal</summary>

**Balance map:** `dict[(user_a, user_b), float]`
```python
def add_expense(self, paid_by, amount, users, strategy):
    splits = strategy.split(amount, users)
    for user, share in splits.items():
        if user != paid_by:
            # user owes paid_by this share
            key = (user.id, paid_by.id)
            self.balances[key] = self.balances.get(key, 0) + share
```

</details>

### Q2: "What if someone pays partially?"

<details>
<summary>👀 Click to reveal</summary>

```python
def settle_up(self, payer, payee, amount):
    key = (payer.id, payee.id)
    self.balances[key] = max(0, self.balances.get(key, 0) - amount)
```

</details>

### Q3: "How to handle multi-currency?"

<details>
<summary>👀 Click to reveal</summary>

Store currency per expense, convert at settlement using exchange rates.
```python
class Expense:
    currency: Currency
    exchange_rate: float  # To base currency
```

</details>

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "I'd use **Strategy pattern** for split types (Equal, Exact, Percentage). Each expense records who paid and how much each user owes. The key algorithm is **debt simplification** — calculate net balance per person, then greedily match biggest debtor with biggest creditor to minimize transactions. I'd track balances in a `dict[(user_a, user_b) → amount]` for real-time who-owes-whom. The system is a **Singleton** with Group-based expense management."

---

*Document created during LLD interview prep session*
