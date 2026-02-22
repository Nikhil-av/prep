import datetime
from enum import Enum, auto
from typing import List, Optional
import copy
from abc import ABC, abstractmethod
import threading
import time

# --- Enums ---
class FlightStatus(Enum):
    SCHEDULED = auto()
    DELAYED = auto()
    DEPARTED = auto()
    ARRIVED = auto()
    CANCELLED = auto()

class BookingStatus(Enum):
    PENDING = auto()
    COMPLETED = auto()
    CANCELLED = auto()
    FAILED = auto()

class SeatStatus(Enum):
    AVAILABLE = auto()
    TEMPORARILY_RESERVED = auto() 
    UNAVAILABLE = auto()

class SeatType(Enum):
    BUSINESS = auto()
    ECONOMY = auto()

# --- Core Entities ---
class Seat:
    def __init__(self, seat_number: int, seat_type: SeatType):
        self.seat_number = seat_number
        self.seat_type = seat_type
        self.status = SeatStatus.AVAILABLE
        self.lock = threading.Lock() 

    def is_available(self) -> bool:
        return self.status == SeatStatus.AVAILABLE

class Passenger:
    def __init__(self, passenger_number: int, name: str, age: int, gender: str):
        self.passenger_number = passenger_number
        self.name = name
        self.age = age
        self.gender = gender

    def __str__(self):
        return f"Passenger: {self.name} (ID: {self.passenger_number})"

class AirPlane:
    def __init__(self, airplane_number: int, model: str, seats: List[Seat]):
        self.airplane_number = airplane_number
        self.model = model
        self.seats = seats

# --- Flight ---
class Flight:
    def __init__(self, flight_number: int, start: str, dest: str, airplane: AirPlane, start_time: datetime.datetime, end_time: datetime.datetime):
        self.flight_number = flight_number
        self.start = start
        self.dest = dest
        self.airplane = airplane
        self.start_time = start_time
        self.end_time = end_time
        self.status = FlightStatus.SCHEDULED
        
        self.seats = []
        for seat in airplane.seats:
            new_seat = Seat(seat.seat_number, seat.seat_type)
            self.seats.append(new_seat)

    def get_available_seats(self) -> List[Seat]:
        return [seat for seat in self.seats if seat.status == SeatStatus.AVAILABLE]

# --- Booking ---
class Booking:
    def __init__(self, booking_number: int, flight: Flight, passenger: Passenger, seats: List[Seat], price: float):
        self.booking_number = booking_number
        self.flight = flight
        self.passenger = passenger
        self.seats = seats 
        self.price = price
        self.status = BookingStatus.PENDING

# --- Search Strategy Pattern ---
class SearchCriteria:
    def __init__(self, source: str = None, destination: str = None, travel_date: datetime.date = None):
        self.source = source
        self.destination = destination
        self.travel_date = travel_date

class FlightSearchStrategy(ABC):
    @abstractmethod
    def search(self, flights: List[Flight], criteria: SearchCriteria) -> List[Flight]:
        pass

class ExactMatchStrategy(FlightSearchStrategy):
    def search(self, flights: List[Flight], criteria: SearchCriteria) -> List[Flight]:
        results = []
        for flight in flights:
            if flight.status == FlightStatus.CANCELLED:
                continue
            if criteria.source and flight.start.lower() != criteria.source.lower():
                continue
            if criteria.destination and flight.dest.lower() != criteria.destination.lower():
                continue
            if criteria.travel_date and flight.start_time.date() != criteria.travel_date:
                continue
            results.append(flight)
        return results

class DateFlexibleSearchStrategy(FlightSearchStrategy):
    def search(self, flights: List[Flight], criteria: SearchCriteria) -> List[Flight]:
        results = []
        for flight in flights:
            if flight.status == FlightStatus.CANCELLED:
                continue
            if criteria.source and flight.start.lower() != criteria.source.lower():
                continue
            if criteria.destination and flight.dest.lower() != criteria.destination.lower():
                continue
            if criteria.travel_date:
                delta = abs((flight.start_time.date() - criteria.travel_date).days)
                if delta > 1: 
                    continue
            results.append(flight)
        return results

# --- Payment Strategy Pattern ---
class PaymentStrategy(ABC):
    @abstractmethod
    def process_payment(self, amount: float) -> bool:
        pass

class CreditCardPayment(PaymentStrategy):
    def process_payment(self, amount: float) -> bool:
        print(f"Processing credit card payment of ${amount}")
        return True 

class PayPalPayment(PaymentStrategy):
    def process_payment(self, amount: float) -> bool:
        print(f"Processing PayPal payment of ${amount}")
        return True

# --- Observer Pattern Base Classes ---
class Observer(ABC):
    """
    Abstract Observer that declares the update interface.
    """
    @abstractmethod
    def update(self, booking: Booking):
        pass

class Subject:
    """
    The Base Subject class providing infrastructure for managing observers.
    """
    def __init__(self):
        self._observers: List[Observer] = []

    def attach(self, observer: Observer):
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Observer):
        try:
            self._observers.remove(observer)
        except ValueError:
            pass

    def notify_observers(self, booking: Booking):
        """
        Triggers an update in each subscriber.
        """
        for observer in self._observers:
            observer.update(booking)

# --- Inventory Management ---
class FlightInventory:
    def __init__(self):
        self.flights: List[Flight] = []

    def add_flight(self, flight: Flight):
        self.flights.append(flight)

    def search_flights(self, strategy: FlightSearchStrategy, criteria: SearchCriteria) -> List[Flight]:
        return strategy.search(self.flights, criteria)

# --- Booking Manager ---
class BookingManager(Subject):
    def __init__(self):
        super().__init__() # Initialize Subject
        self.bookings: List[Booking] = []
        self._booking_counter = 0
        self._booking_lock = threading.Lock() 

    def create_booking(self, flight: Flight, passenger: Passenger, seat_numbers: List[int], payment_strategy: PaymentStrategy) -> Optional[Booking]:
        # 1. Identify all requested seat objects
        seats_to_book = []
        for s_num in seat_numbers:
            found_seat = next((s for s in flight.seats if s.seat_number == s_num), None)
            if not found_seat:
                print(f"Error: Seat {s_num} does not exist.")
                return None
            seats_to_book.append(found_seat)
        
        # 2. Sort seats (Deadlock Prevention)
        seats_to_book.sort(key=lambda s: s.seat_number)

        # 3. Validation and Reservation
        locked_seats = []
        all_available = True
        
        try:
            # Phase 1: Locking
            for seat in seats_to_book:
                seat.lock.acquire()
                locked_seats.append(seat)
                if seat.status != SeatStatus.AVAILABLE:
                    all_available = False
                    print(f"Error: Seat {seat.seat_number} is not available. Booking aborted.")
                    break 
            
            if not all_available:
                return None 

            # Phase 2: Reserve
            for seat in seats_to_book:
                seat.status = SeatStatus.TEMPORARILY_RESERVED
            
            # Unlock for Payment
            for seat in locked_seats:
                seat.lock.release()
            locked_seats = [] 

            # Phase 3: Payment
            total_price = 0.0
            for seat in seats_to_book:
                total_price += 100.0 if seat.seat_type == SeatType.ECONOMY else 500.0
            
            payment_success = payment_strategy.process_payment(total_price)

            # Phase 4: Finalize
            for seat in seats_to_book:
                seat.lock.acquire()
                locked_seats.append(seat)
            
            if payment_success:
                with self._booking_lock:
                    self._booking_counter += 1
                    booking_id = self._booking_counter
                
                booking = Booking(booking_id, flight, passenger, seats_to_book, total_price)
                booking.status = BookingStatus.COMPLETED
                for seat in seats_to_book:
                    seat.status = SeatStatus.UNAVAILABLE
                
                self.bookings.append(booking)
                print(f"Success: Booking {booking_id} confirmed for {passenger.name}.")
                
                # --- NOTIFY OBSERVERS HERE ---
                self.notify_observers(booking)
                
                return booking
            else:
                print("Error: Payment failed.")
                for seat in seats_to_book:
                    seat.status = SeatStatus.AVAILABLE
                return None

        except Exception as e:
            print(f"Unexpected error: {e}")
            for seat in seats_to_book:
                if seat.status == SeatStatus.TEMPORARILY_RESERVED:
                     seat.status = SeatStatus.AVAILABLE
            return None
            
        finally:
            for seat in locked_seats:
                seat.lock.release()

# --- Concrete Observers ---
class EmailNotificationService(Observer):
    def update(self, booking: Booking):
        # In real life, this would connect to an SMTP server
        print(f"[Email Service] Sending confirmation email to {booking.passenger.name} for Booking #{booking.booking_number}.")

class SMSNotificationService(Observer):
    def update(self, booking: Booking):
        # In real life, this would use Twilio or similar
        print(f"[SMS Service] Sending SMS to {booking.passenger.name}: Your seats {[s.seat_number for s in booking.seats]} are booked!")

class AnalyticsService(Observer):
    def update(self, booking: Booking):
        print(f"[Analytics] Recording transaction of ${booking.price} for Flight {booking.flight.flight_number}.")


# --- Facade: Airline Management System ---
class AirlineManagementSystem:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AirlineManagementSystem, cls).__new__(cls)
            cls._instance.inventory = FlightInventory()
            cls._instance.booking_manager = BookingManager()
            
            # Auto-register default services
            cls._instance.booking_manager.attach(EmailNotificationService())
            cls._instance.booking_manager.attach(SMSNotificationService())
            cls._instance.booking_manager.attach(AnalyticsService())
            
        return cls._instance

    def add_flight(self, flight: Flight):
        self.inventory.add_flight(flight)

    def search_flights(self, source: str, destination: str, date: datetime.date, strategy: FlightSearchStrategy = None) -> List[Flight]:
        if strategy is None:
            strategy = ExactMatchStrategy()
        criteria = SearchCriteria(source, destination, date)
        return self.inventory.search_flights(strategy, criteria)

    def book_tickets(self, flight: Flight, passenger: Passenger, seat_numbers: List[int], payment_strategy: PaymentStrategy):
        return self.booking_manager.create_booking(flight, passenger, seat_numbers, payment_strategy)

# --- Driver Code ---
if __name__ == "__main__":
    ams = AirlineManagementSystem()

    # Setup Airplane
    seats = [Seat(i, SeatType.ECONOMY if i > 2 else SeatType.BUSINESS) for i in range(1, 11)]
    plane = AirPlane(101, "Boeing 737", seats)

    # Schedule Flights
    now = datetime.datetime.now()
    flight_time_tomorrow = now + datetime.timedelta(days=1)
    flight1 = Flight(101, "NYC", "LAX", plane, flight_time_tomorrow, flight_time_tomorrow + datetime.timedelta(hours=5))
    ams.add_flight(flight1)

    print("\n--- Notification Test Multi-Seat Booking ---")
    p1 = Passenger(1, "John Doe", 30, "M")
    payment = CreditCardPayment()
    
    # This should trigger emails, SMS, and analytics
    booking = ams.book_tickets(flight1, p1, [3, 4], payment)
