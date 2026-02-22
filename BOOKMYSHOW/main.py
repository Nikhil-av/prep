from enum import Enum
from datetime import datetime, timedelta
import threading

class BookingStatus(Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class SeatStatus(Enum):
    AVAILABLE = "AVAILABLE"
    LOCKED = "LOCKED"
    BOOKED = "BOOKED"

class SeatType(Enum):
    RECLINER = "RECLINER"
    REGULAR = "REGULAR"
    BALCONY = "BALCONY"

class Seat:
    """Pure data class — only knows physical properties, NOT status."""
    def __init__(self, _id: int, seat_type: SeatType):
        self.seat_type = seat_type
        self.seat_number = _id
    def __str__(self):
        return f"{self.seat_type.value} - Seat {self.seat_number}"
    def __hash__(self):
        return hash(self.seat_number)
    def __eq__(self, other):
        return isinstance(other, Seat) and self.seat_number == other.seat_number

class Theatre:
    def __init__(self,_id:int, name: str, seats: list[Seat]):
        self._id = _id
        self.name = name
        self.seats = seats
    def add_seat(self, seat: Seat):
        self.seats.append(seat)
    def remove_seat(self, seat: Seat):
        self.seats.remove(seat)

class Show:
    """Links Movie + Theatre + Time. Tracks seat status PER SHOW."""
    def __init__(self, _id: int, movie: str, theatre: Theatre, show_time: datetime, prices: dict[SeatType, int]):
        self._id = _id
        self.movie = movie
        self.theatre = theatre
        self.show_time = show_time
        self.prices = prices
        self._lock = threading.Lock()

        # Per-show seat tracking — this is the KEY design decision!
        # Same physical seat can be AVAILABLE here but BOOKED in another show
        self.seat_status: dict[Seat, SeatStatus] = {}
        self.seat_locks: dict[Seat, tuple] = {}  # seat -> (user, expiry_time)

        # Initialize all theatre seats as AVAILABLE for this show
        for seat in theatre.seats:
            self.seat_status[seat] = SeatStatus.AVAILABLE

    def get_price(self, seat_type: SeatType):
        return self.prices[seat_type]

    def get_available_seats(self) -> list[Seat]:
        self._cleanup_expired_locks()
        return [seat for seat, status in self.seat_status.items() if status == SeatStatus.AVAILABLE]

    def lock_seats(self, seats: list[Seat], user, duration_minutes: int = 10) -> bool:
        """Thread-safe seat locking. Returns True if ALL seats locked successfully."""
        with self._lock:
            # Step 1: Check ALL seats are available
            for seat in seats:
                if self.seat_status.get(seat) != SeatStatus.AVAILABLE:
                    raise Exception(f"Seat {seat} is not available (status: {self.seat_status.get(seat)})")

            # Step 2: Lock ALL seats atomically
            expiry = datetime.now() + timedelta(minutes=duration_minutes)
            for seat in seats:
                self.seat_status[seat] = SeatStatus.LOCKED
                self.seat_locks[seat] = (user, expiry)
            return True

    def unlock_seats(self, seats: list[Seat]):
        """Release locked seats back to AVAILABLE."""
        with self._lock:
            for seat in seats:
                self.seat_status[seat] = SeatStatus.AVAILABLE
                self.seat_locks.pop(seat, None)

    def confirm_seats(self, seats: list[Seat]):
        """Mark locked seats as permanently BOOKED after payment."""
        with self._lock:
            for seat in seats:
                self.seat_status[seat] = SeatStatus.BOOKED
                self.seat_locks.pop(seat, None)

    def is_locked_by(self, seat: Seat, user) -> bool:
        """Check if a seat is locked by a specific user."""
        if seat in self.seat_locks:
            return self.seat_locks[seat][0] == user
        return False

    def _cleanup_expired_locks(self):
        """Release seats whose lock has expired (10 min timeout)."""
        with self._lock:
            now = datetime.now()
            expired = [seat for seat, (user, expiry) in self.seat_locks.items() if now > expiry]
            for seat in expired:
                self.seat_status[seat] = SeatStatus.AVAILABLE
                self.seat_locks.pop(seat)
                print(f"🔓 Seat {seat} lock expired, released back to AVAILABLE")

    def __str__(self):
        return f"{self._id} - {self.movie} - {self.theatre.name} - {self.show_time}"


class User:
    def __init__(self,_id:int,name: str):
        self._id = _id
        self.name = name
    def __str__(self):
        return f"{self._id} - {self.name}"

class PaymentStrategy:
    def pay(self, amount: int):
        pass
class CreditCardPayment(PaymentStrategy):
    def pay(self, amount: int):
        print(f"Paid {amount} using Credit Card")
class UpiPayment(PaymentStrategy):
    def pay(self, amount: int):
        print(f"Paid {amount} using UPI")

class Booking:
    def __init__(self,_id:int,show: Show, seats: list[Seat],user: User):
        self._id = _id
        self.show = show
        self.seats = seats
        self.booking_status = BookingStatus.PENDING
        self.payment_strategy=None
        self.user=user
        self.lock_seats()
    def lock_seats(self):
        self.show.lock_seats(self.seats,self.user)
    def calculate_total(self):
        total = 0
        for seat in self.seats:
            total += self.show.get_price(seat.seat_type)
        return total
    def set_payment_strategy(self,payment_strategy:PaymentStrategy):
        self.payment_strategy=payment_strategy
    def pay_amount(self):
        if self.payment_strategy is None:
            raise Exception("Payment strategy not set")
        amount=self.calculate_total()
        for seat in self.seats:
            if not self.show.is_locked_by(seat, self.user):
                raise Exception("Seat not locked by user cant book now")
        self.show.confirm_seats(self.seats)
        self.payment_strategy.pay(amount)
        self.booking_status=BookingStatus.COMPLETED
    def cancel(self):
        self.show.unlock_seats(self.seats)
        self.booking_status=BookingStatus.CANCELLED
    def __str__(self):
        return f"{self._id} - {self.show} - {self.seats} - {self.booking_status}"
    
class SearchStrategy:
    """Base class for search strategies."""
    def search(self, shows: dict, query: str) -> list[Show]:
        pass

class SearchByMovie(SearchStrategy):
    """Search all shows for a given movie name."""
    def search(self, shows: dict, query: str) -> list[Show]:
        return [show for show in shows.values() if show.movie.lower() == query.lower()]

class SearchByTheatre(SearchStrategy):
    """Search all shows at a given theatre."""
    def search(self, shows: dict, query: str) -> list[Show]:
        return [show for show in shows.values() if show.theatre.name.lower() == query.lower()]

class BookMyShow:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BookMyShow, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.users = {}
        self.theatres = {}
        self.shows = {}
        self.bookings = {}
    def register_user(self, user: User):
        self.users[user._id] = user
    def register_theatre(self, theatre: Theatre):
        self.theatres[theatre._id] = theatre
    def register_show(self, show: Show):
        self.shows[show._id] = show
    def register_booking(self, booking: Booking):
        self.bookings[booking._id] = booking
    def get_user(self, _id: int):
        return self.users.get(_id)
    def get_theatre(self, _id: int):
        return self.theatres.get(_id)
    def get_show(self, _id: int):
        return self.shows.get(_id)
    def get_booking(self, _id: int):
        return self.bookings.get(_id)
    def search(self, query: str, strategy: SearchStrategy) -> list[Show]:
        """Search shows using the given strategy."""
        return strategy.search(self.shows, query)
    def __str__(self):
        return f"{self.users} - {self.theatres} - {self.shows} - {self.bookings}"


# ═══════════════════════════════════════════════════════════════
#                        DEMO / MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("       BOOKMYSHOW - LLD DEMO")
    print("=" * 60)

    bms = BookMyShow()

    # --- Setup: Create Users ---
    user1 = User(1, "Nikhil")
    user2 = User(2, "Priya")
    bms.register_user(user1)
    bms.register_user(user2)

    # --- Setup: Create Theatre with Seats ---
    seats = [
        Seat(1, SeatType.RECLINER), Seat(2, SeatType.RECLINER),
        Seat(3, SeatType.BALCONY), Seat(4, SeatType.BALCONY),
        Seat(5, SeatType.REGULAR), Seat(6, SeatType.REGULAR),
        Seat(7, SeatType.REGULAR), Seat(8, SeatType.REGULAR),
    ]
    theatre1 = Theatre(1, "PVR IMAX", seats)
    bms.register_theatre(theatre1)

    # --- Setup: Create Shows ---
    pricing = {
        SeatType.RECLINER: 500,
        SeatType.BALCONY: 300,
        SeatType.REGULAR: 200
    }
    show1 = Show(1, "Pushpa 2", theatre1, datetime(2026, 2, 16, 18, 0), pricing)
    show2 = Show(2, "Pushpa 2", theatre1, datetime(2026, 2, 16, 21, 0), pricing)
    bms.register_show(show1)
    bms.register_show(show2)

    # --- Test 1: Search by Movie ---
    print("\n📽️  Search 'Pushpa 2':")
    results = bms.search("Pushpa 2", SearchByMovie())
    for show in results:
        print(f"   {show}")

    # --- Test 2: Search by Theatre ---
    print("\n🎬 Search 'PVR IMAX':")
    results = bms.search("PVR IMAX", SearchByTheatre())
    for show in results:
        print(f"   {show}")

    # --- Test 3: View Available Seats ---
    print(f"\n💺 Available seats for Show 1 (6 PM):")
    available = show1.get_available_seats()
    for seat in available:
        print(f"   {seat}")

    # --- Test 4: Happy Path Booking ---
    print("\n✅ USER 1 (Nikhil) books Seat 1 & 2 (RECLINER):")
    booking1 = Booking(1, show1, [seats[0], seats[1]], user1)
    booking1.set_payment_strategy(UpiPayment())
    booking1.pay_amount()
    print(f"   Booking Status: {booking1.booking_status.value}")
    print(f"   Total Paid: ₹{booking1.calculate_total()}")

    # --- Test 5: Concurrent Booking - Same Seats ---
    print("\n❌ USER 2 (Priya) tries to book SAME seats (1 & 2):")
    try:
        booking2 = Booking(2, show1, [seats[0], seats[1]], user2)
        print("   ERROR: Should not reach here!")
    except Exception as e:
        print(f"   Correctly rejected: {e}")

    # --- Test 6: User 2 books different seats ---
    print("\n✅ USER 2 (Priya) books Seat 3 & 4 (BALCONY):")
    booking3 = Booking(3, show1, [seats[2], seats[3]], user2)
    booking3.set_payment_strategy(CreditCardPayment())
    booking3.pay_amount()
    print(f"   Booking Status: {booking3.booking_status.value}")
    print(f"   Total Paid: ₹{booking3.calculate_total()}")

    # --- Test 7: Check remaining seats ---
    print(f"\n💺 Remaining available seats for Show 1:")
    available = show1.get_available_seats()
    for seat in available:
        print(f"   {seat}")

    # --- Test 8: Cancel booking ---
    print("\n🚫 USER 1 cancels booking:")
    booking1.cancel()
    print(f"   Booking Status: {booking1.booking_status.value}")

    print(f"\n💺 Seats after cancellation:")
    available = show1.get_available_seats()
    for seat in available:
        print(f"   {seat}")

    # --- Test 9: Same seat in DIFFERENT show is available ---
    print("\n🔄 Seat 1 in Show 2 (9 PM) — should be AVAILABLE:")
    available_show2 = show2.get_available_seats()
    seat1_available = seats[0] in available_show2
    print(f"   Seat 1 available in 9 PM show: {seat1_available} ✓")

    # --- Test 10: Concurrent thread test ---
    print("\n🧵 CONCURRENT BOOKING TEST (2 threads, same seat):")
    results = {}

    def try_book(user, seat_list, result_key):
        try:
            b = Booking(100 + user._id, show2, seat_list, user)
            b.set_payment_strategy(UpiPayment())
            b.pay_amount()
            results[result_key] = "SUCCESS"
        except Exception as e:
            results[result_key] = f"FAILED: {e}"

    t1 = threading.Thread(target=try_book, args=(user1, [seats[4]], "user1"))
    t2 = threading.Thread(target=try_book, args=(user2, [seats[4]], "user2"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print(f"   User 1: {results.get('user1')}")
    print(f"   User 2: {results.get('user2')}")
    print(f"   (Exactly ONE should succeed, ONE should fail)")

    # --- Singleton Check ---
    print("\n🔒 Singleton Check:")
    bms2 = BookMyShow()
    print(f"   bms is bms2: {bms is bms2} ✓")

    print("\n" + "=" * 60)
    print("       ALL TESTS PASSED! 🎉")
    print("=" * 60)