# 📚 LIBRARY MANAGEMENT SYSTEM — LLD
## SDE2 Interview — Complete LLD Guide

---

## 🎯 Problem Statement
> Design a **Library Management System** where members can borrow/return books, reserve books when unavailable, and pay fines for late returns.

---

## 🤔 THINK: Before Reading Further...
**What's the FIRST question you should ask the interviewer?**

<details>
<summary>👀 Click to reveal</summary>

**"Is there a difference between a Book and a physical copy of that Book?"**

This is THE make-or-break question. The answer leads to the **Book vs BookCopy** distinction — the most important design decision in this problem.

| Other Questions | Why? |
|---|---|
| "How many books can a member borrow?" | Borrow limit (5 books max) |
| "Is there a late fee? How is it calculated?" | Fine = days_overdue × rate_per_day |
| "What happens when all copies are borrowed?" | Reservation queue |
| "Can members reserve a specific copy?" | No — they reserve the BOOK, system assigns a copy |
| "Payment methods?" | Strategy pattern |
| "How to search for books?" | Search strategy |

</details>

---

## ✅ Functional Requirements

| # | FR |
|---|-----|
| 1 | Register members |
| 2 | Add books with **multiple copies** |
| 3 | Search books — by title, author, category |
| 4 | **Borrow** a book (system picks an available copy) |
| 5 | **Return** a book (auto-calculate fine if overdue) |
| 6 | **Reserve** a book when no copies available (queue) |
| 7 | **Auto-issue** to next reserved member when a copy returns |
| 8 | **Fine calculation** — ₹X per day overdue |
| 9 | **Borrow limit** — max 5 books per member |
| 10 | **Payment** — Strategy pattern (Cash, Card, UPI) |

---

## 🔥 THE KEY INSIGHT: Book vs BookCopy

### 🤔 THINK: Why can't we just have a single Book class?

<details>
<summary>👀 Click to reveal — this separates juniors from seniors!</summary>

**Library has 3 copies of "Harry Potter":**

**❌ WRONG: Single Book class**
```python
class Book:
    title = "Harry Potter"
    status = AVAILABLE  # ← Which copy? All 3 have different states!
```

**✅ CORRECT: Book (metadata) + BookCopy (physical item)**
```python
class Book:
    title = "Harry Potter"
    author = "JK Rowling"
    copies: list[BookCopy]       # 3 copies

class BookCopy:
    copy_id = 1
    status = AVAILABLE           # THIS copy's status
```

| Book | BookCopy |
|------|----------|
| Metadata (title, author, category) | Physical item |
| One per title | Many per title |
| Has reservation queue | Has a status |
| "What" you're looking for | "Which one" you take home |

> This is the same as **Movie vs Show** in BookMyShow, or **Restaurant vs Order** in Food Delivery.

</details>

---

## 📦 Core Entities

<details>
<summary>👀 Click to reveal all entities</summary>

### Enums
```
BookCopyStatus:      AVAILABLE, BORROWED, RESERVED, LOST
BorrowStatus:        ACTIVE, RETURNED
ReservationStatus:   ACTIVE, FULFILLED, CANCELLED
```

### Observer Pattern
```
Observer (ABC)       → update(book_id, message)
Subject              → add/remove/notify observers
```

### Core
```
BookCopy             → book_id, copy_id, status
Book (extends Subject) → id, title, author, category, copies[], reservation_queue
BorrowingRecord      → user, book_copy, borrow_date, due_date, fine calculation
Reservation          → user_id, book_id, status
```

### Strategies
```
PaymentStrategy (ABC)  → CreditCard, UPI, Cash
SearchStrategy (ABC)   → SearchByTitle, SearchByAuthor, SearchByCategory
```

### User & System
```
User (extends Observer) → borrowed_books, reservations, borrow limit
LibraryManagementSystem (Singleton)
```

</details>

---

## 📊 Borrow & Return Flow

### 🤔 THINK: Walk through what happens when a member returns a book and someone else has it reserved.

<details>
<summary>👀 Click to reveal</summary>

```
BORROW FLOW:
1. User requests to borrow Book X
2. Check: user.active_loans < MAX_LIMIT (5)?
3. Get available copy: book.get_available_copy()
4. If available → create BorrowingRecord, copy.status = BORROWED
5. If not available → suggest reserve_book()

RETURN FLOW:
1. User returns BorrowingRecord
2. Calculate fine: (return_date - due_date).days × FINE_PER_DAY
3. If fine > 0 → payment.pay(fine)
4. copy.status = AVAILABLE
5. Check reservation queue:
   → If someone waiting → notify them (Observer) → auto-borrow for them
```

**The auto-issue on return is what makes this problem interesting!**

```python
def return_book(self, user_id, record, payment=None):
    fine = record.return_book(payment)
    user.remove_loan(record)
    
    # Check reservation queue
    book = self.books[record.book_copy.book_id]
    if book.reservation_queue:
        next_user_id = book.reservation_queue.popleft()
        book.notify_observers(book.book_id, "Book available!")
        self.borrow_book(next_user_id, book.book_id)  # Auto-issue!
```

</details>

---

## 💰 Fine Calculation

### 🤔 THINK: Where should the fine config live? On BorrowingRecord or LibrarySystem?

<details>
<summary>👀 Click to reveal</summary>

**Config on the system/record class constants, calculation on BorrowingRecord:**

```python
class BorrowingRecord:
    MAX_BORROW_DAYS = 14
    FINE_PER_DAY = 10

    def __init__(self, user_id, book_copy):
        self.due_date = datetime.now() + timedelta(days=self.MAX_BORROW_DAYS)
    
    def calculate_fine(self):
        if self.return_date > self.due_date:
            overdue_days = (self.return_date - self.due_date).days
            return overdue_days * self.FINE_PER_DAY
        return 0
```

**Why on BorrowingRecord?** It owns the dates. Single Responsibility.
**Why constants?** One place to change. Tomorrow if fine is ₹20 → change one constant.

</details>

---

## 🔗 Entity Relationships

```
LibraryManagementSystem (Singleton)
    ├── books: dict[id, Book]
    ├── users: dict[id, User]
    └── all_loans: list[BorrowingRecord]

Book (extends Subject)
    ├── copies: list[BookCopy]
    ├── reservation_queue: deque[user_id]
    └── observers: list[Observer]  (from Subject)

User (extends Observer)
    ├── active_loans: list[BorrowingRecord]
    └── reservations: list[Reservation]

BorrowingRecord
    ├── user_id
    ├── book_copy: BookCopy  (actual physical copy)
    ├── due_date, return_date
    └── fine: float
```

---

## 💡 Design Patterns

| Pattern | Where | Why |
|---------|-------|-----|
| **Observer** | Book notifies reserved users on return | Decoupled notification |
| **Strategy** | SearchStrategy, PaymentStrategy | Multiple interchangeable algorithms |
| **Singleton** | LibraryManagementSystem | One system instance |

---

## 🎤 Interviewer Follow-Up Questions

### Q1: "How would you handle a member losing a book?"

<details>
<summary>👀 Click to reveal</summary>

```python
def report_lost(self, user_id, record):
    record.book_copy.set_status(BookCopyStatus.LOST)
    record.status = BorrowStatus.LOST
    lost_fee = BOOK_REPLACEMENT_COST
    # Charge user
    user.remove_loan(record)
```
BookCopy becomes LOST (not destroyed — can be found later).

</details>

### Q2: "How to implement a book recommendation system?"

<details>
<summary>👀 Click to reveal</summary>

**Strategy pattern for recommendation:**
```python
class RecommendationStrategy(ABC):
    def recommend(self, user, books) -> list[Book]: pass

class CategoryBased(RecommendationStrategy):
    def recommend(self, user, books):
        # Find categories user has borrowed most
        # Return unread books in those categories
        pass

class PopularityBased(RecommendationStrategy):
    def recommend(self, user, books):
        # Sort by borrow_count, return top N
        pass
```

</details>

### Q3: "How would you add a librarian role with admin privileges?"

<details>
<summary>👀 Click to reveal</summary>

```python
class Role(Enum):
    MEMBER = 1
    LIBRARIAN = 2

class User:
    role: Role

# Add permission checks
def add_book(self, user_id, book):
    user = self.users[user_id]
    if user.role != Role.LIBRARIAN:
        raise PermissionError("Only librarians can add books")
```

</details>

### Q4: "What if two users try to borrow the last copy simultaneously?"

<details>
<summary>👀 Click to reveal</summary>

Same as BookMyShow! Use `threading.Lock`:
```python
class LibraryManagementSystem:
    def borrow_book(self, user_id, book_id):
        with self._lock:
            copy = book.get_available_copy()
            if copy:
                copy.set_status(BookCopyStatus.BORROWED)
                # ...
```

</details>

---

## ⚠️ Common Bugs

| Bug | Fix |
|-----|-----|
| Reservation uses `BorrowStatus.ACTIVE` | Use `ReservationStatus.ACTIVE` |
| BorrowingRecord stores `book_id` not `book_copy` | Store `BookCopy` reference to change status on return |
| Book has no title/author | Must have searchable fields |
| `get_available_copy()` doesn't set status | Status set by system after validation, not by getter |
| Subject needs `book_id` in constructor | Clean Subject(), pass book_id in notify() |

---

## 🧠 Quick Recall — What to Say in 1 Minute

> "The key insight is **Book vs BookCopy** — Book is metadata (title, author), BookCopy is the physical item with a status. Members borrow copies, not books. I use **Observer pattern** — when a copy is returned, the Book notifies reserved members and auto-issues to the next in queue. **BorrowingRecord** tracks dates and calculates fines. Search uses **Strategy pattern** (by title, author, category). The system is a **Singleton** with a borrow limit of 5 books per member."

---

## ✅ Pre-Implementation Checklist

- [ ] Book vs BookCopy distinction (status on COPY, not Book)
- [ ] Observer pattern: Subject (Book) + Observer (User)
- [ ] Reservation queue (deque) on Book
- [ ] BorrowingRecord with due_date + fine calculation
- [ ] Auto-issue on return (check reservation queue)
- [ ] Borrow limit (5 books max)
- [ ] SearchStrategy (title, author, category)
- [ ] PaymentStrategy (Cash, Card, UPI)
- [ ] LibraryManagementSystem singleton
- [ ] Demo: borrow, return with fine, reservation auto-issue

---

*Document created during LLD interview prep session*
