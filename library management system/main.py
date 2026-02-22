from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from collections import deque
import uuid


# ═══════════════════════════════════════════════════════════════
#                        ENUMS
# ═══════════════════════════════════════════════════════════════

class BookCopyStatus(Enum):
    AVAILABLE = 1
    BORROWED = 2
    RESERVED = 3
    LOST = 4

class BorrowStatus(Enum):
    ACTIVE = 1
    RETURNED = 2

class ReservationStatus(Enum):
    ACTIVE = 1
    FULFILLED = 2
    CANCELLED = 3


# ═══════════════════════════════════════════════════════════════
#                     OBSERVER PATTERN
# ═══════════════════════════════════════════════════════════════

class Observer(ABC):
    @abstractmethod
    def update(self, book_id: int, message: str):
        pass


class Subject:
    def __init__(self):
        self.observers: list[Observer] = []

    def add_observer(self, observer: Observer):
        self.observers.append(observer)

    def remove_observer(self, observer: Observer):
        self.observers.remove(observer)

    def notify_observers(self, book_id: int, message: str):
        for observer in self.observers:
            observer.update(book_id, message)


# ═══════════════════════════════════════════════════════════════
#                     CORE ENTITIES
# ═══════════════════════════════════════════════════════════════

class BookCopy:
    def __init__(self, book_id: int, copy_id: int):
        self.book_id = book_id
        self.copy_id = copy_id
        self.status = BookCopyStatus.AVAILABLE

    def set_status(self, status: BookCopyStatus):
        self.status = status

    def __str__(self):
        return f"Copy#{self.copy_id} (Book#{self.book_id}, {self.status.name})"


class Book(Subject):
    def __init__(self, book_id: int, title: str, author: str, category: str):
        super().__init__()
        self.book_id = book_id
        self.title = title
        self.author = author
        self.category = category
        self.copies: list[BookCopy] = []
        self.reservation_queue: deque = deque()  # Queue of user_ids waiting

    def add_copy(self, copy: BookCopy):
        self.copies.append(copy)

    def get_available_copy(self) -> BookCopy | None:
        for copy in self.copies:
            if copy.status == BookCopyStatus.AVAILABLE:
                return copy
        return None

    def available_count(self) -> int:
        return sum(1 for c in self.copies if c.status == BookCopyStatus.AVAILABLE)

    def __str__(self):
        return (f"📖 [{self.book_id}] \"{self.title}\" by {self.author} "
                f"({self.category}) — {self.available_count()}/{len(self.copies)} available")


class Reservation:
    _counter = 0

    def __init__(self, user_id: int, book_id: int):
        Reservation._counter += 1
        self.reservation_id = Reservation._counter
        self.user_id = user_id
        self.book_id = book_id
        self.status = ReservationStatus.ACTIVE
        self.created_at = datetime.now()


class BorrowingRecord:
    MAX_BORROW_DAYS = 14
    FINE_PER_DAY = 10

    def __init__(self, user_id: int, book_copy: BookCopy, borrow_date: datetime = None):
        self.user_id = user_id
        self.book_copy = book_copy
        self.borrow_date = borrow_date or datetime.now()
        self.due_date = self.borrow_date + timedelta(days=self.MAX_BORROW_DAYS)
        self.return_date = None
        self.status = BorrowStatus.ACTIVE
        self.fine = 0

    def calculate_fine(self) -> float:
        return_date = self.return_date or datetime.now()
        if return_date > self.due_date:
            overdue_days = (return_date - self.due_date).days
            return overdue_days * self.FINE_PER_DAY
        return 0

    def return_book(self, payment: 'PaymentStrategy' = None) -> float:
        self.return_date = datetime.now()
        self.status = BorrowStatus.RETURNED
        self.book_copy.set_status(BookCopyStatus.AVAILABLE)
        self.fine = self.calculate_fine()
        if self.fine > 0 and payment:
            payment.pay(self.fine)
        elif self.fine > 0:
            print(f"    ⚠️ Fine of ₹{self.fine} pending!")
        return self.fine


# ═══════════════════════════════════════════════════════════════
#                     STRATEGIES
# ═══════════════════════════════════════════════════════════════

class PaymentStrategy(ABC):
    @abstractmethod
    def pay(self, amount: float):
        pass

class CreditCardPayment(PaymentStrategy):
    def pay(self, amount: float):
        print(f"    💳 Paid ₹{amount} via Credit Card")

class UPIPayment(PaymentStrategy):
    def pay(self, amount: float):
        print(f"    📱 Paid ₹{amount} via UPI")


class SearchStrategy(ABC):
    @abstractmethod
    def search(self, query: str, books: list['Book']) -> list['Book']:
        pass

class SearchByTitle(SearchStrategy):
    def search(self, query: str, books: list['Book']) -> list['Book']:
        return [b for b in books if query.lower() in b.title.lower()]

class SearchByAuthor(SearchStrategy):
    def search(self, query: str, books: list['Book']) -> list['Book']:
        return [b for b in books if query.lower() in b.author.lower()]

class SearchByCategory(SearchStrategy):
    def search(self, query: str, books: list['Book']) -> list['Book']:
        return [b for b in books if query.lower() in b.category.lower()]


# ═══════════════════════════════════════════════════════════════
#                        USER / MEMBER
# ═══════════════════════════════════════════════════════════════

class User(Observer):
    MAX_BORROW_LIMIT = 5

    def __init__(self, user_id: int, name: str):
        self.user_id = user_id
        self.name = name
        self.active_loans: list[BorrowingRecord] = []
        self.reservations: list[Reservation] = []

    def can_borrow(self) -> bool:
        return len(self.active_loans) < self.MAX_BORROW_LIMIT

    def add_loan(self, record: BorrowingRecord):
        self.active_loans.append(record)

    def remove_loan(self, record: BorrowingRecord):
        self.active_loans.remove(record)

    def update(self, book_id: int, message: str):
        print(f"    🔔 [{self.name}] Notification: {message}")

    def __str__(self):
        return f"👤 {self.name} (ID:{self.user_id}, Borrowed:{len(self.active_loans)}/{self.MAX_BORROW_LIMIT})"


# ═══════════════════════════════════════════════════════════════
#                  LIBRARY SYSTEM (SINGLETON)
# ═══════════════════════════════════════════════════════════════

class LibraryManagementSystem:
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
        self.books: dict[int, Book] = {}
        self.users: dict[int, User] = {}
        self.all_loans: list[BorrowingRecord] = []

    # --- Book Management ---
    def add_book(self, book_id: int, title: str, author: str, category: str, num_copies: int = 1) -> Book:
        book = Book(book_id, title, author, category)
        for i in range(num_copies):
            book.add_copy(BookCopy(book_id, i + 1))
        self.books[book_id] = book
        return book

    # --- User Management ---
    def register_user(self, user_id: int, name: str) -> User:
        user = User(user_id, name)
        self.users[user_id] = user
        return user

    # --- Search ---
    def search(self, query: str, strategy: SearchStrategy) -> list[Book]:
        return strategy.search(query, list(self.books.values()))

    # --- Borrow ---
    def borrow_book(self, user_id: int, book_id: int) -> BorrowingRecord | None:
        user = self.users.get(user_id)
        book = self.books.get(book_id)

        if not user or not book:
            print(f"    ❌ User or Book not found!")
            return None

        if not user.can_borrow():
            print(f"    ❌ {user.name} has reached the borrow limit ({User.MAX_BORROW_LIMIT} books)!")
            return None

        copy = book.get_available_copy()
        if not copy:
            print(f"    ❌ No copies of \"{book.title}\" available. Use reserve_book() instead.")
            return None

        # Borrow the copy
        copy.set_status(BookCopyStatus.BORROWED)
        record = BorrowingRecord(user_id, copy)
        user.add_loan(record)
        self.all_loans.append(record)
        print(f"    ✅ {user.name} borrowed \"{book.title}\" ({copy}), due: {record.due_date.strftime('%Y-%m-%d')}")
        return record

    # --- Return ---
    def return_book(self, user_id: int, record: BorrowingRecord, payment: PaymentStrategy = None) -> float:
        user = self.users.get(user_id)
        if not user:
            print(f"    ❌ User not found!")
            return 0

        book = self.books.get(record.book_copy.book_id)
        fine = record.return_book(payment)
        user.remove_loan(record)

        if fine == 0:
            print(f"    ✅ {user.name} returned \"{book.title}\" — No fine!")
        else:
            print(f"    ✅ {user.name} returned \"{book.title}\" — Fine: ₹{fine}")

        # Check reservation queue
        if book and book.reservation_queue:
            next_user_id = book.reservation_queue.popleft()
            next_user = self.users.get(next_user_id)
            if next_user:
                book.notify_observers(book.book_id, f"\"{book.title}\" is now available!")
                # Auto-borrow for the reserved user
                print(f"    📌 Auto-issuing to reserved user {next_user.name}...")
                self.borrow_book(next_user_id, book.book_id)

        return fine

    # --- Reserve ---
    def reserve_book(self, user_id: int, book_id: int) -> Reservation | None:
        user = self.users.get(user_id)
        book = self.books.get(book_id)

        if not user or not book:
            print(f"    ❌ User or Book not found!")
            return None

        if book.get_available_copy():
            print(f"    ❌ Copies are available — just borrow it!")
            return None

        # Add to reservation queue and register as observer
        book.reservation_queue.append(user_id)
        book.add_observer(user)
        reservation = Reservation(user_id, book_id)
        user.reservations.append(reservation)
        position = len(book.reservation_queue)
        print(f"    📌 {user.name} reserved \"{book.title}\" — Queue position: {position}")
        return reservation


# ═══════════════════════════════════════════════════════════════
#                        DEMO
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("       LIBRARY MANAGEMENT SYSTEM - LLD DEMO")
    print("=" * 60)

    lib = LibraryManagementSystem()

    # --- Add Books ---
    print("\n📚 Adding Books:")
    lib.add_book(1, "Harry Potter", "JK Rowling", "Fiction", num_copies=2)
    lib.add_book(2, "Clean Code", "Robert Martin", "Technology", num_copies=1)
    lib.add_book(3, "Sapiens", "Yuval Harari", "History", num_copies=3)
    for book in lib.books.values():
        print(f"  {book}")

    # --- Register Users ---
    print("\n👥 Registering Users:")
    lib.register_user(1, "Nikhil")
    lib.register_user(2, "Priya")
    lib.register_user(3, "Rahul")
    for user in lib.users.values():
        print(f"  {user}")

    # --- Search ---
    print("\n🔍 Search by Title: 'harry'")
    results = lib.search("harry", SearchByTitle())
    for b in results:
        print(f"  {b}")

    print("\n🔍 Search by Author: 'robert'")
    results = lib.search("robert", SearchByAuthor())
    for b in results:
        print(f"  {b}")

    print("\n🔍 Search by Category: 'fiction'")
    results = lib.search("fiction", SearchByCategory())
    for b in results:
        print(f"  {b}")

    # --- Borrow Flow ---
    print("\n" + "─" * 60)
    print("📖 BORROW FLOW")
    print("─" * 60)

    print("\n  Nikhil borrows Harry Potter:")
    loan1 = lib.borrow_book(1, 1)

    print("\n  Priya borrows Harry Potter:")
    loan2 = lib.borrow_book(2, 1)

    print("\n  Rahul tries to borrow Harry Potter (no copies left!):")
    loan3 = lib.borrow_book(3, 1)

    # --- Reservation Flow ---
    print("\n" + "─" * 60)
    print("📌 RESERVATION FLOW")
    print("─" * 60)

    print("\n  Rahul reserves Harry Potter:")
    reservation = lib.reserve_book(3, 1)

    print(f"\n  Book status after reservation:")
    print(f"  {lib.books[1]}")

    # --- Return with auto-issue to reserved user ---
    print("\n" + "─" * 60)
    print("📤 RETURN FLOW (triggers reservation)")
    print("─" * 60)

    print("\n  Nikhil returns Harry Potter:")
    lib.return_book(1, loan1)

    # --- Return with fine (simulate overdue) ---
    print("\n" + "─" * 60)
    print("💰 LATE RETURN WITH FINE")
    print("─" * 60)

    print("\n  Priya borrows Clean Code:")
    loan_cc = lib.borrow_book(2, 2)

    # Simulate overdue by backdating
    loan_cc.borrow_date = datetime.now() - timedelta(days=20)
    loan_cc.due_date = loan_cc.borrow_date + timedelta(days=14)

    print("\n  Priya returns Clean Code (6 days late!):")
    lib.return_book(2, loan_cc, UPIPayment())

    # --- Final State ---
    print("\n" + "─" * 60)
    print("📊 FINAL STATE")
    print("─" * 60)
    for user in lib.users.values():
        print(f"  {user}")
    for book in lib.books.values():
        print(f"  {book}")

    # --- Singleton Check ---
    print(f"\n🔒 Singleton: {lib is LibraryManagementSystem()} ✓")

    print("\n" + "=" * 60)
    print("       ALL TESTS COMPLETE! 🎉")
    print("=" * 60)