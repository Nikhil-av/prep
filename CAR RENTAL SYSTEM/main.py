from enum import Enum
import uuid
class CarStatus(Enum):
    AVAILABLE = 1
    UNAVAILABLE = 2
    UNDER_MAINTENANCE = 3
class BookingStatus(Enum):
    PENDING = 1
    CONFIRMED = 2
    CANCELLED = 3
    COMPLETED = 4
class UserStatus(Enum):
    UNVERIFIED = 1
    VERIFIED = 2
class User:
    def __init__(self, name: str):
        self.user_id = uuid.uuid4()
        self.name = name
        self.status = UserStatus.UNVERIFIED
        self.licence_number = None
    def verify_user(self, licence_number: str):
        self.status = UserStatus.VERIFIED
        self.licence_number = licence_number
    def __str__(self):
        return f"User ID: {self.user_id}, Name: {self.name}, Status: {self.status.name}, Licence Number: {self.licence_number}"
class Car:
    def __init__(self, name: str, model: str, year: int, branch_id: int):
        self.car_id = uuid.uuid4()
        self.name = name
        self.model = model
        self.year = year
        self.status = CarStatus.AVAILABLE
        self.branch_id = branch_id
    def __str__(self):
        return f"Car ID: {self.car_id}, Name: {self.name}, Model: {self.model}, Year: {self.year}, Status: {self.status.name}"
    def change_status(self, status: CarStatus):
        self.status = status
class Booking:
    def __init__(self, user: User, car: Car, start_date: str, end_date: str, status: BookingStatus):
        self.booking_id = uuid.uuid4()
        self.user = user
        self.car = car
        self.start_date = start_date
        self.end_date = end_date
        self.status = BookingStatus.PENDING
        self.payment_strategy = None
    def change_status(self, status: BookingStatus):
        self.status = status
    def set_payment_strategy(self, payment_strategy: PaymentStrategy):
        self.payment_strategy = payment_strategy
    def pay(self,payment_strategy: PaymentStrategy, amount: float):
        payment_strategy.pay(amount)
        self.status = BookingStatus.CONFIRMED
class BookingService:
    def __init__(self):
        self.bookings = []
    def book_car(self, user: User, car: Car, start_date: str, end_date: str):
        if user.status != UserStatus.VERIFIED:
            raise Exception("User is not verified")
        if car.status != CarStatus.AVAILABLE:
            raise Exception("Car is not available")
        booking = Booking(user, car, start_date, end_date, BookingStatus.PENDING)
        car.change_status(CarStatus.UNAVAILABLE)  # Mark car as rented
        self.bookings.append(booking)
        return booking
    def cancel_booking(self, booking: Booking):
        booking.change_status(BookingStatus.CANCELLED)
        booking.car.change_status(CarStatus.AVAILABLE)  # Release the car
        return booking
    def complete_booking(self, booking: Booking):
        booking.change_status(BookingStatus.COMPLETED)
        booking.car.change_status(CarStatus.AVAILABLE)  # Car is available again
        return booking
    def confirm_booking(self, booking: Booking):
        booking.change_status(BookingStatus.CONFIRMED)
        return booking

class Branch:
    def __init__(self, name: str, location: str):
        self.branch_id = uuid.uuid4()
        self.name = name
        self.location = location
        self.cars = []
    def __str__(self):
        return f"Branch ID: {self.branch_id}, Name: {self.name}, Location: {self.location}, Cars: {self.cars}"
    def add_car(self, car: Car):
        self.cars.append(car)
    def remove_car(self, car: Car):
        self.cars.remove(car)
    def get_available_cars(self):
        """Get all currently available cars at this branch."""
        return [car for car in self.cars if car.status == CarStatus.AVAILABLE]
class CarRentalSystem:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CarRentalSystem, cls).__new__(cls)
        return cls._instance
    def __init__(self):
        # Prevent re-initialization on subsequent calls
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.branches = {}
        self.users = {}
        self.bookings = {}
        self.booking_service = BookingService()

    def search_available_cars(self, branch_id):
        """Get all available cars at a specific branch."""
        if branch_id not in self.branches:
            raise Exception(f"Branch {branch_id} not found")
        return self.branches[branch_id].get_available_cars()
    def add_branch(self, branch: Branch):
        self.branches[branch.branch_id] = branch
    def remove_branch(self, branch: Branch):
        self.branches.pop(branch.branch_id)
    def add_car(self,branch_id: int, car: Car):
        self.branches[branch_id].add_car(car)
    def remove_car(self, branch_id: int, car: Car):
        self.branches[branch_id].remove_car(car)
    def add_user(self, user: User):
        self.users[user.user_id] = user
    def remove_user(self, user: User):
        self.users.pop(user.user_id)
    def add_booking(self, booking: Booking):
        self.bookings[booking.booking_id] = booking
    def remove_booking(self, booking: Booking):
        self.bookings.pop(booking.booking_id)


# ============ DEMO ============
if __name__ == "__main__":
    print("=" * 60)
    print("CAR RENTAL SYSTEM - DEMO")
    print("=" * 60)

    # Get the singleton instance
    system = CarRentalSystem()

    # 1. Create a branch
    print("\n--- 1. Creating Airport Branch ---")
    airport_branch = Branch("Airport Branch", "123 Airport Road")
    system.add_branch(airport_branch)
    print(f"Created: {airport_branch.name} (ID: {airport_branch.branch_id})")

    # 2. Add cars to the branch
    print("\n--- 2. Adding Cars to Branch ---")
    car1 = Car("Toyota", "Camry", 2023, airport_branch.branch_id)
    car2 = Car("Honda", "CR-V", 2022, airport_branch.branch_id)
    car3 = Car("Maruti", "Swift", 2024, airport_branch.branch_id)
    
    airport_branch.add_car(car1)
    airport_branch.add_car(car2)
    airport_branch.add_car(car3)
    print(f"Added: {car1.name} {car1.model}")
    print(f"Added: {car2.name} {car2.model}")
    print(f"Added: {car3.name} {car3.model}")

    # 3. Create a user
    print("\n--- 3. Creating User ---")
    user = User("Nikhil")
    system.add_user(user)
    print(f"Created user: {user.name} (Status: {user.status.name})")

    # 4. Try to book without verification (should fail)
    print("\n--- 4. Trying to Book Without Verification ---")
    try:
        system.booking_service.book_car(user, car1, "2024-01-30", "2024-02-02")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 5. Verify the user
    print("\n--- 5. Verifying User ---")
    user.verify_user("DL-1234567890")
    print(f"User verified! Status: {user.status.name}, License: {user.licence_number}")

    # 6. Search available cars
    print("\n--- 6. Searching Available Cars ---")
    available = system.search_available_cars(airport_branch.branch_id)
    print(f"Available cars at {airport_branch.name}: {len(available)}")
    for car in available:
        print(f"  - {car.name} {car.model} ({car.year}) - {car.status.name}")

    # 7. Book a car (should succeed now)
    print("\n--- 7. Booking a Car ---")
    booking = system.booking_service.book_car(user, car1, "2024-01-30", "2024-02-02")
    system.add_booking(booking)
    print(f"✅ Booking created! ID: {booking.booking_id}")
    print(f"   Car: {booking.car.name} {booking.car.model}")
    print(f"   Status: {booking.status.name}")
    print(f"   Car Status: {car1.status.name}")

    # 8. Check available cars (should be 2 now)
    print("\n--- 8. Checking Available Cars After Booking ---")
    available = system.search_available_cars(airport_branch.branch_id)
    print(f"Available cars now: {len(available)}")
    for car in available:
        print(f"  - {car.name} {car.model} - {car.status.name}")

    # 9. Try to book the same car again (should fail)
    print("\n--- 9. Trying to Book Same Car Again ---")
    try:
        system.booking_service.book_car(user, car1, "2024-02-05", "2024-02-10")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 10. Complete the booking
    print("\n--- 10. Completing the Booking (Car Returned) ---")
    system.booking_service.complete_booking(booking)
    print(f"Booking completed! Status: {booking.status.name}")
    print(f"Car Status: {car1.status.name}")

    # 11. Check available cars (should be 3 again)
    print("\n--- 11. Checking Available Cars After Return ---")
    available = system.search_available_cars(airport_branch.branch_id)
    print(f"Available cars now: {len(available)}")

    print("\n" + "=" * 60)
    print("DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 60)


class PaymentStrategy(ABC):
    @abstractmethod
    def pay(self, amount: float):
        pass
class CardPaymentStrategy(PaymentStrategy):
    def pay(self, amount: float):
        print(f"Paid {amount} using credit card.")

class CashPaymentStrategy(PaymentStrategy):
    def pay(self, amount: float):
        print(f"Paid {amount} using cash.")