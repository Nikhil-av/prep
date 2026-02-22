from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import uuid

# ============ ENUMS ============

class SeatType(Enum):
    VIP = "VIP"
    PREMIUM = "PREMIUM"
    REGULAR = "REGULAR"

class SeatStatus(Enum):
    AVAILABLE = "AVAILABLE"
    LOCKED = "LOCKED"
    BOOKED = "BOOKED"

class BookingStatus(Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


# ============ ENTITIES ============

class User:
    def __init__(self, user_id: int, name: str, email: str, phone: str):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.phone = phone

    def __str__(self):
        return f"User({self.name}, {self.email})"


class Seat:
    def __init__(self, seat_id: int, row: str, number: int, category: SeatType):
        self.seat_id = seat_id
        self.row = row
        self.number = number
        self.category = category
        self.status = SeatStatus.AVAILABLE

    def set_status(self, status: SeatStatus):
        self.status = status

    def is_available(self) -> bool:
        return self.status == SeatStatus.AVAILABLE

    def __str__(self):
        return f"Seat({self.row}{self.number}, {self.category.value}, {self.status.value})"


class Venue:
    def __init__(self, venue_id: int, name: str, address: str):
        self.venue_id = venue_id
        self.name = name
        self.address = address
        self.seats = []

    def add_seat(self, seat: Seat):
        self.seats.append(seat)

    def add_seats(self, seats: list):
        self.seats.extend(seats)

    def get_seats_by_category(self, category: SeatType) -> list:
        return [seat for seat in self.seats if seat.category == category]

    def __str__(self):
        return f"Venue({self.name}, {len(self.seats)} seats)"


class Concert:
    def __init__(self, concert_id: int, name: str, artist: str, venue: Venue, 
                 date_time: datetime, prices: dict):
        self.concert_id = concert_id
        self.name = name
        self.artist = artist
        self.venue = venue
        self.date_time = date_time
        self.prices = prices  # {SeatType: price}

    def get_available_seats(self) -> list:
        return [seat for seat in self.venue.seats if seat.status == SeatStatus.AVAILABLE]

    def get_available_seats_by_category(self, category: SeatType) -> list:
        return [seat for seat in self.venue.seats 
                if seat.category == category and seat.status == SeatStatus.AVAILABLE]

    def get_price(self, category: SeatType) -> int:
        return self.prices.get(category, 0)

    def __str__(self):
        return f"Concert({self.name} by {self.artist} at {self.venue.name})"


# ============ PAYMENT STRATEGY ============

class PaymentStrategy(ABC):
    @abstractmethod
    def pay(self, amount: int) -> bool:
        pass


class CreditCardPayment(PaymentStrategy):
    def pay(self, amount: int) -> bool:
        print(f"💳 Paid ₹{amount} using Credit Card")
        return True


class PayPalPayment(PaymentStrategy):
    def pay(self, amount: int) -> bool:
        print(f"🅿️ Paid ₹{amount} using PayPal")
        return True


class UPIPayment(PaymentStrategy):
    def pay(self, amount: int) -> bool:
        print(f"📱 Paid ₹{amount} using UPI")
        return True


# ============ BOOKING ============

class Booking:
    def __init__(self, booking_id: int, user: User, concert: Concert, seats: list):
        self.booking_id = booking_id
        self.user = user
        self.concert = concert
        self.seats = seats
        self.status = BookingStatus.PENDING
        self.total_amount = self._calculate_total()
        self.created_at = datetime.now()

    def _calculate_total(self) -> int:
        """Calculate total price based on concert's pricing for each seat category."""
        total = 0
        for seat in self.seats:
            total += self.concert.get_price(seat.category)
        return total

    def confirm(self):
        """Mark booking as confirmed and seats as BOOKED."""
        for seat in self.seats:
            seat.set_status(SeatStatus.BOOKED)
        self.status = BookingStatus.CONFIRMED

    def cancel(self):
        """Cancel booking and release seats."""
        for seat in self.seats:
            seat.set_status(SeatStatus.AVAILABLE)
        self.status = BookingStatus.CANCELLED

    def pay(self, payment_strategy: PaymentStrategy) -> bool:
        """Process payment and confirm booking."""
        if payment_strategy.pay(self.total_amount):
            self.confirm()
            return True
        return False

    def __str__(self):
        seat_list = ", ".join([f"{s.row}{s.number}" for s in self.seats])
        return f"Booking({self.booking_id}, {self.user.name}, {self.concert.name}, [{seat_list}], ₹{self.total_amount}, {self.status.value})"


# ============ BOOKING SERVICE ============

class BookingService:
    def __init__(self):
        self.bookings = {}
        self._booking_counter = 0

    def create_booking(self, user: User, concert: Concert, seats: list) -> Booking:
        """Create a new booking after validating seat availability."""
        # Validate all seats are available
        for seat in seats:
            if not seat.is_available():
                raise Exception(f"Seat {seat.row}{seat.number} is not available")

        # Validate seat limit (max 10)
        if len(seats) > 10:
            raise Exception("Maximum 10 seats per booking")

        if len(seats) == 0:
            raise Exception("Must select at least one seat")

        # Mark seats as LOCKED (reserved for this booking)
        for seat in seats:
            seat.set_status(SeatStatus.LOCKED)

        # Create booking
        self._booking_counter += 1
        booking = Booking(self._booking_counter, user, concert, seats)
        self.bookings[booking.booking_id] = booking

        print(f"✅ Booking created: {booking}")
        return booking

    def confirm_booking(self, booking_id: int, payment_strategy: PaymentStrategy) -> Booking:
        """Confirm booking by processing payment."""
        booking = self.get_booking(booking_id)
        if booking.status != BookingStatus.PENDING:
            raise Exception(f"Booking {booking_id} is not in PENDING status")

        if booking.pay(payment_strategy):
            print(f"✅ Booking confirmed: {booking}")
            return booking
        else:
            raise Exception("Payment failed")

    def cancel_booking(self, booking_id: int) -> Booking:
        """Cancel a booking and release seats."""
        booking = self.get_booking(booking_id)
        booking.cancel()
        print(f"❌ Booking cancelled: {booking}")
        return booking

    def get_booking(self, booking_id: int) -> Booking:
        if booking_id not in self.bookings:
            raise Exception(f"Booking {booking_id} not found")
        return self.bookings[booking_id]


# ============ CONCERT BOOKING SYSTEM (Singleton) ============

class ConcertBookingSystem:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConcertBookingSystem, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.venues = {}
        self.concerts = {}
        self.users = {}
        self.booking_service = BookingService()

    # ---- Venue Management ----
    def add_venue(self, venue: Venue):
        self.venues[venue.venue_id] = venue

    def get_venue(self, venue_id: int) -> Venue:
        if venue_id not in self.venues:
            raise Exception(f"Venue {venue_id} not found")
        return self.venues[venue_id]

    # ---- Concert Management ----
    def add_concert(self, concert: Concert):
        self.concerts[concert.concert_id] = concert

    def get_concert(self, concert_id: int) -> Concert:
        if concert_id not in self.concerts:
            raise Exception(f"Concert {concert_id} not found")
        return self.concerts[concert_id]

    def get_all_concerts(self) -> list:
        return list(self.concerts.values())

    # ---- User Management ----
    def add_user(self, user: User):
        self.users[user.user_id] = user

    def get_user(self, user_id: int) -> User:
        if user_id not in self.users:
            raise Exception(f"User {user_id} not found")
        return self.users[user_id]

    # ---- Booking Operations (Delegate to BookingService) ----
    def book_seats(self, user: User, concert: Concert, seats: list) -> Booking:
        return self.booking_service.create_booking(user, concert, seats)

    def confirm_booking(self, booking_id: int, payment_strategy: PaymentStrategy) -> Booking:
        return self.booking_service.confirm_booking(booking_id, payment_strategy)

    def cancel_booking(self, booking_id: int) -> Booking:
        return self.booking_service.cancel_booking(booking_id)

    # ---- Display ----
    def show_available_seats(self, concert_id: int):
        concert = self.get_concert(concert_id)
        available = concert.get_available_seats()
        print(f"\n--- Available Seats for {concert.name} ---")
        for seat in available:
            price = concert.get_price(seat.category)
            print(f"  {seat} - ₹{price}")
        print(f"Total available: {len(available)}")


# ============ DEMO ============

if __name__ == "__main__":
    print("=" * 60)
    print("CONCERT TICKET BOOKING SYSTEM - DEMO")
    print("=" * 60)

    # Get the singleton instance
    system = ConcertBookingSystem()

    # 1. Create a venue with seats
    print("\n--- 1. Creating Venue ---")
    venue = Venue(1, "Madison Square Garden", "New York, NY")
    
    # Add VIP seats (Row A)
    for i in range(1, 6):
        venue.add_seat(Seat(i, "A", i, SeatType.VIP))
    
    # Add Premium seats (Row B, C)
    for i in range(6, 16):
        row = "B" if i < 11 else "C"
        venue.add_seat(Seat(i, row, (i - 5) % 5 + 1, SeatType.PREMIUM))
    
    # Add Regular seats (Row D, E)
    for i in range(16, 26):
        row = "D" if i < 21 else "E"
        venue.add_seat(Seat(i, row, (i - 15) % 5 + 1, SeatType.REGULAR))

    system.add_venue(venue)
    print(f"Created: {venue}")

    # 2. Create a concert
    print("\n--- 2. Creating Concert ---")
    concert = Concert(
        concert_id=1,
        name="Summer Music Festival",
        artist="Taylor Swift",
        venue=venue,
        date_time=datetime(2024, 6, 15, 19, 0),
        prices={
            SeatType.VIP: 5000,
            SeatType.PREMIUM: 2000,
            SeatType.REGULAR: 500
        }
    )
    system.add_concert(concert)
    print(f"Created: {concert}")

    # 3. Create a user
    print("\n--- 3. Creating User ---")
    user = User(1, "Nikhil", "nikhil@email.com", "9876543210")
    system.add_user(user)
    print(f"Created: {user}")

    # 4. Show available seats
    system.show_available_seats(1)

    # 5. Book some seats
    print("\n--- 5. Booking Seats ---")
    vip_seats = venue.get_seats_by_category(SeatType.VIP)[:2]  # Book 2 VIP seats
    booking = system.book_seats(user, concert, vip_seats)
    print(f"Booking total: ₹{booking.total_amount}")

    # 6. Show available seats after booking
    system.show_available_seats(1)

    # 7. Try to book same seats again (should fail)
    print("\n--- 7. Try Booking Same Seats Again ---")
    try:
        system.book_seats(user, concert, vip_seats)
    except Exception as e:
        print(f"❌ Error: {e}")

    # 8. Confirm booking with payment
    print("\n--- 8. Confirm Booking with Payment ---")
    system.confirm_booking(booking.booking_id, CreditCardPayment())

    # 9. Try another booking with UPI
    print("\n--- 9. Another Booking with UPI ---")
    premium_seats = concert.get_available_seats_by_category(SeatType.PREMIUM)[:3]
    booking2 = system.book_seats(user, concert, premium_seats)
    system.confirm_booking(booking2.booking_id, UPIPayment())

    # 10. Cancel the second booking
    print("\n--- 10. Cancel Second Booking ---")
    system.cancel_booking(booking2.booking_id)

    # 11. Show final seat availability
    system.show_available_seats(1)

    print("\n" + "=" * 60)
    print("DEMO COMPLETED!")
    print("=" * 60)


# ================================================================================
# VERSION 2: SECTION-BASED DESIGN
# ================================================================================
# 
# Instead of SeatType on each Seat, we use a Section class that groups seats.
# This is a more realistic design that mirrors how venues actually work.
#
# Hierarchy:
#   Venue → Sections → Seats
#
# Benefits:
#   - Section knows its type and price (single source of truth)
#   - Easy to add section-level attributes (wheelchair access, etc.)
#   - More realistic venue modeling
#
# ================================================================================

print("\n\n")
print("=" * 60)
print("VERSION 2: SECTION-BASED DESIGN")
print("=" * 60)


class SectionType(Enum):
    """Type of section in the venue."""
    VIP = "VIP"
    PREMIUM = "PREMIUM"
    REGULAR = "REGULAR"


class SeatV2:
    """
    V2 Seat - Belongs to a Section instead of having its own category.
    The section determines the type and price.
    """
    def __init__(self, seat_id: int, row: str, number: int, section: 'SectionV2'):
        self.seat_id = seat_id
        self.row = row
        self.number = number
        self.section = section  # Back-reference to parent section
        self.status = SeatStatus.AVAILABLE
        # Locking attributes
        self.locked_by: User = None
        self.locked_until: datetime = None

    def lock(self, user: User, minutes: int = 10):
        """Lock seat for a user for specified duration."""
        if self.status != SeatStatus.AVAILABLE:
            raise Exception(f"Seat {self.row}{self.number} is not available")
        self.status = SeatStatus.LOCKED
        self.locked_by = user
        self.locked_until = datetime.now() + timedelta(minutes=minutes)

    def unlock(self):
        """Release the lock on this seat."""
        self.status = SeatStatus.AVAILABLE
        self.locked_by = None
        self.locked_until = None

    def book(self):
        """Mark seat as booked."""
        self.status = SeatStatus.BOOKED
        self.locked_by = None
        self.locked_until = None

    def is_lock_expired(self) -> bool:
        """Check if the lock has expired."""
        if self.status != SeatStatus.LOCKED:
            return False
        return datetime.now() > self.locked_until if self.locked_until else True

    def get_price(self) -> int:
        """Get price from parent section."""
        return self.section.price

    def __str__(self):
        return f"Seat({self.row}{self.number}, {self.section.section_type.value}, {self.status.value})"


class SectionV2:
    """
    A section in the venue (e.g., VIP section, Premium section).
    Contains multiple seats and knows its type and price.
    """
    def __init__(self, section_id: int, name: str, section_type: SectionType, price: int):
        self.section_id = section_id
        self.name = name  # e.g., "VIP-Front", "Premium-Left"
        self.section_type = section_type
        self.price = price
        self.seats: list = []

    def add_seat(self, row: str, number: int) -> SeatV2:
        """Create and add a seat to this section."""
        seat_id = len(self.seats) + 1
        seat = SeatV2(seat_id, row, number, self)
        self.seats.append(seat)
        return seat

    def get_available_seats(self) -> list:
        """Get all available seats in this section."""
        available = []
        for seat in self.seats:
            # Auto-unlock expired locks
            if seat.is_lock_expired():
                seat.unlock()
            if seat.status == SeatStatus.AVAILABLE:
                available.append(seat)
        return available

    def __str__(self):
        available = len(self.get_available_seats())
        return f"Section({self.name}, {self.section_type.value}, ₹{self.price}, {available}/{len(self.seats)} available)"


class VenueV2:
    """
    V2 Venue - Contains Sections which contain Seats.
    """
    def __init__(self, venue_id: int, name: str, address: str):
        self.venue_id = venue_id
        self.name = name
        self.address = address
        self.sections: list = []

    def add_section(self, section: SectionV2):
        self.sections.append(section)

    def get_section(self, name: str) -> SectionV2:
        for section in self.sections:
            if section.name == name:
                return section
        raise Exception(f"Section {name} not found")

    def get_all_seats(self) -> list:
        """Get all seats across all sections."""
        seats = []
        for section in self.sections:
            seats.extend(section.seats)
        return seats

    def get_available_seats(self) -> list:
        """Get all available seats across all sections."""
        available = []
        for section in self.sections:
            available.extend(section.get_available_seats())
        return available

    def __str__(self):
        total_seats = sum(len(s.seats) for s in self.sections)
        return f"Venue({self.name}, {len(self.sections)} sections, {total_seats} seats)"


class ConcertV2:
    """
    V2 Concert - Price is determined by Section, not by a separate price map.
    """
    def __init__(self, concert_id: int, name: str, artist: str, venue: VenueV2, date_time: datetime):
        self.concert_id = concert_id
        self.name = name
        self.artist = artist
        self.venue = venue
        self.date_time = date_time
        # Note: Prices are on Sections, not here!

    def get_available_seats(self) -> list:
        return self.venue.get_available_seats()

    def get_available_seats_by_section_type(self, section_type: SectionType) -> list:
        available = []
        for section in self.venue.sections:
            if section.section_type == section_type:
                available.extend(section.get_available_seats())
        return available

    def show_availability(self):
        print(f"\n--- {self.name} by {self.artist} ---")
        print(f"Venue: {self.venue.name}")
        for section in self.venue.sections:
            print(f"  {section}")

    def __str__(self):
        return f"Concert({self.name} by {self.artist})"


class BookingV2:
    """
    V2 Booking - Price is calculated from seat.get_price() which comes from Section.
    """
    def __init__(self, booking_id: int, user: User, concert: ConcertV2, seats: list):
        self.booking_id = booking_id
        self.user = user
        self.concert = concert
        self.seats = seats
        self.status = BookingStatus.PENDING
        self.total_amount = self._calculate_total()
        self.created_at = datetime.now()

    def _calculate_total(self) -> int:
        """Calculate total from each seat's section price."""
        return sum(seat.get_price() for seat in self.seats)

    def confirm(self):
        for seat in self.seats:
            seat.book()
        self.status = BookingStatus.CONFIRMED

    def cancel(self):
        for seat in self.seats:
            seat.unlock()
        self.status = BookingStatus.CANCELLED

    def __str__(self):
        seat_list = ", ".join([f"{s.row}{s.number}" for s in self.seats])
        return f"Booking({self.booking_id}, [{seat_list}], ₹{self.total_amount}, {self.status.value})"


# ============ V2 DEMO ============

print("\n--- Creating V2 Venue with Sections ---")

# Create venue
venue_v2 = VenueV2(1, "National Stadium", "Delhi")

# Create sections with their own prices
vip_section = SectionV2(1, "VIP-Front", SectionType.VIP, price=5000)
premium_left = SectionV2(2, "Premium-Left", SectionType.PREMIUM, price=2000)
premium_right = SectionV2(3, "Premium-Right", SectionType.PREMIUM, price=2000)
regular_section = SectionV2(4, "Regular-Back", SectionType.REGULAR, price=500)

# Add seats to sections
for i in range(1, 6):
    vip_section.add_seat("A", i)

for i in range(1, 6):
    premium_left.add_seat("B", i)
    premium_right.add_seat("C", i)

for i in range(1, 11):
    regular_section.add_seat("D", i)

# Add sections to venue
venue_v2.add_section(vip_section)
venue_v2.add_section(premium_left)
venue_v2.add_section(premium_right)
venue_v2.add_section(regular_section)

print(f"Created: {venue_v2}")
for section in venue_v2.sections:
    print(f"  {section}")

# Create concert
print("\n--- Creating V2 Concert ---")
concert_v2 = ConcertV2(
    concert_id=1,
    name="Rock Festival",
    artist="Arijit Singh",
    venue=venue_v2,
    date_time=datetime(2024, 7, 20, 18, 0)
)
print(f"Created: {concert_v2}")

# Show availability
concert_v2.show_availability()

# Create user and booking
print("\n--- V2 Booking ---")
user_v2 = User(2, "Rahul", "rahul@email.com", "9999999999")

# Get 2 VIP seats
vip_seats = vip_section.get_available_seats()[:2]

# Lock seats
for seat in vip_seats:
    seat.lock(user_v2, minutes=10)
print(f"Locked seats: {[str(s) for s in vip_seats]}")

# Create booking
booking_v2 = BookingV2(1, user_v2, concert_v2, vip_seats)
print(f"Created: {booking_v2}")
print(f"Total from Section prices: ₹{booking_v2.total_amount}")

# Confirm booking
booking_v2.confirm()
print(f"Confirmed: {booking_v2}")

# Show updated availability
concert_v2.show_availability()

print("\n" + "=" * 60)
print("V2 DEMO COMPLETED!")
print("=" * 60)
print("\n")
print("KEY DIFFERENCES V1 vs V2:")
print("-" * 40)
print("V1: Seat has SeatType, Concert has price map")
print("V2: Section has type & price, Seat inherits from Section")
print("-" * 40)
print("V2 Benefits:")
print("  - Single source of truth for pricing (Section)")
print("  - Easier to add section-level attributes")
print("  - More realistic venue modeling")
print("  - Section can have special rules (e.g., min age for VIP)")
print("=" * 60)