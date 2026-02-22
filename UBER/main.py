from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import math
import random


# ═══════════════════════════════════════════════════════════════
#                        ENUMS
# ═══════════════════════════════════════════════════════════════

class RideStatus(Enum):
    REQUESTED = 1
    DRIVER_ASSIGNED = 2
    IN_PROGRESS = 3
    COMPLETED = 4
    CANCELLED = 5

class DriverStatus(Enum):
    AVAILABLE = 1
    ON_RIDE = 2
    OFFLINE = 3

class VehicleType(Enum):
    AUTO = 1
    MINI = 2
    SEDAN = 3
    SUV = 4


# ═══════════════════════════════════════════════════════════════
#                     LOCATION
# ═══════════════════════════════════════════════════════════════

class Location:
    """Simple (x, y) coordinate. In production → lat/long with Haversine."""
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def distance_to(self, other: 'Location') -> float:
        """Euclidean distance. In production → Google Maps Distance Matrix API."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def __str__(self):
        return f"({self.x}, {self.y})"


# ═══════════════════════════════════════════════════════════════
#                     STRATEGIES
# ═══════════════════════════════════════════════════════════════

# --- Payment Strategy ---
class PaymentStrategy(ABC):
    @abstractmethod
    def pay(self, amount: float):
        pass

class CashPayment(PaymentStrategy):
    def pay(self, amount: float):
        print(f"      💵 Paid ₹{amount:.0f} in Cash")

class CardPayment(PaymentStrategy):
    def pay(self, amount: float):
        print(f"      💳 Paid ₹{amount:.0f} via Card")

class UPIPayment(PaymentStrategy):
    def pay(self, amount: float):
        print(f"      📱 Paid ₹{amount:.0f} via UPI")


# --- Pricing Config (dict-based, cleaner than Strategy for this use case) ---
PRICING = {
    VehicleType.AUTO:  {"base": 25, "per_km": 8,  "per_min": 1.0},
    VehicleType.MINI:  {"base": 40, "per_km": 10, "per_min": 1.5},
    VehicleType.SEDAN: {"base": 50, "per_km": 12, "per_min": 2.0},
    VehicleType.SUV:   {"base": 70, "per_km": 15, "per_min": 2.5},
}


# ═══════════════════════════════════════════════════════════════
#                     CORE ENTITIES
# ═══════════════════════════════════════════════════════════════

class Rider:
    def __init__(self, rider_id: int, name: str, location: Location):
        self.rider_id = rider_id
        self.name = name
        self.location = location
        self.ride_history: list['Ride'] = []
        self.rating = 5.0
        self.total_ratings = 0

    def add_rating(self, rating: float):
        self.rating = ((self.rating * self.total_ratings) + rating) / (self.total_ratings + 1)
        self.total_ratings += 1

    def __str__(self):
        return f"👤 {self.name} (Rating: {self.rating:.1f}⭐)"


class Driver:
    def __init__(self, driver_id: int, name: str, vehicle_type: VehicleType, location: Location):
        self.driver_id = driver_id
        self.name = name
        self.vehicle_type = vehicle_type
        self.location = location
        self.status = DriverStatus.AVAILABLE
        self.ride_history: list['Ride'] = []
        self.rating = 5.0
        self.total_ratings = 0

    def go_online(self):
        self.status = DriverStatus.AVAILABLE

    def go_offline(self):
        self.status = DriverStatus.OFFLINE

    def add_rating(self, rating: float):
        self.rating = ((self.rating * self.total_ratings) + rating) / (self.total_ratings + 1)
        self.total_ratings += 1

    def __str__(self):
        return f"🚗 {self.name} ({self.vehicle_type.name}, {self.status.name}, Rating: {self.rating:.1f}⭐)"


class Ride:
    _counter = 0

    def __init__(self, rider: Rider, pickup: Location, drop: Location, vehicle_type: VehicleType):
        Ride._counter += 1
        self.ride_id = Ride._counter
        self.rider = rider
        self.driver: Driver | None = None
        self.pickup = pickup
        self.drop = drop
        self.vehicle_type = vehicle_type
        self.status = RideStatus.REQUESTED
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.fare = 0.0
        self.distance_km = pickup.distance_to(drop)

    def __str__(self):
        driver_name = self.driver.name if self.driver else "None"
        return (f"🛣️ Ride#{self.ride_id}: {self.rider.name} → {driver_name} | "
                f"{self.pickup}→{self.drop} | {self.status.name} | ₹{self.fare:.0f}")


# ═══════════════════════════════════════════════════════════════
#              CAB BOOKING SYSTEM (SINGLETON)
# ═══════════════════════════════════════════════════════════════

class CabBookingSystem:
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
        self.riders: dict[int, Rider] = {}
        self.drivers: dict[int, Driver] = {}
        self.rides: dict[int, Ride] = {}
        self.surge_multiplier = 1.0

    # ─── Registration ───
    def register_rider(self, rider_id: int, name: str, location: Location) -> Rider:
        rider = Rider(rider_id, name, location)
        self.riders[rider_id] = rider
        return rider

    def register_driver(self, driver_id: int, name: str, vehicle_type: VehicleType, location: Location) -> Driver:
        driver = Driver(driver_id, name, vehicle_type, location)
        self.drivers[driver_id] = driver
        return driver

    def set_surge(self, multiplier: float):
        self.surge_multiplier = multiplier
        print(f"   ⚡ Surge set to {multiplier}x")

    # ─── Find Nearby Drivers ───
    def find_nearby_drivers(self, location: Location, vehicle_type: VehicleType, radius: float = 10.0) -> list[Driver]:
        """Filter AVAILABLE + matching vehicle → within radius → sort by distance."""
        available = [d for d in self.drivers.values()
                     if d.status == DriverStatus.AVAILABLE
                     and d.vehicle_type == vehicle_type]
        nearby = [d for d in available
                  if d.location.distance_to(location) <= radius]
        nearby.sort(key=lambda d: d.location.distance_to(location))
        return nearby

    # ─── Request Ride ───
    def request_ride(self, rider_id: int, pickup: Location, drop: Location, vehicle_type: VehicleType) -> Ride | None:
        rider = self.riders.get(rider_id)
        if not rider:
            print("   ❌ Rider not found!")
            return None

        ride = Ride(rider, pickup, drop, vehicle_type)
        self.rides[ride.ride_id] = ride

        # Find nearby drivers
        nearby_drivers = self.find_nearby_drivers(pickup, vehicle_type)
        if not nearby_drivers:
            print(f"   ❌ No {vehicle_type.name} drivers available nearby!")
            ride.status = RideStatus.CANCELLED
            return None

        # Show available drivers
        print(f"   🔍 Found {len(nearby_drivers)} nearby {vehicle_type.name} driver(s):")
        for d in nearby_drivers:
            dist = d.location.distance_to(pickup)
            print(f"      • {d.name} — {dist:.1f} km away")

        rider.ride_history.append(ride)
        print(f"   📝 Ride#{ride.ride_id} created: {pickup} → {drop} ({ride.distance_km:.1f} km)")
        return ride

    # ─── Accept Ride ───
    def accept_ride(self, driver_id: int, ride_id: int) -> bool:
        driver = self.drivers.get(driver_id)
        ride = self.rides.get(ride_id)

        if not driver or not ride:
            print("   ❌ Driver or Ride not found!")
            return False

        if ride.status != RideStatus.REQUESTED:
            print(f"   ❌ Ride is {ride.status.name}, cannot accept!")
            return False

        if driver.status != DriverStatus.AVAILABLE:
            print(f"   ❌ {driver.name} is {driver.status.name}, cannot accept!")
            return False

        ride.driver = driver
        ride.status = RideStatus.DRIVER_ASSIGNED
        driver.status = DriverStatus.ON_RIDE
        driver.ride_history.append(ride)
        print(f"   ✅ {driver.name} accepted Ride#{ride_id}! Heading to pickup...")
        return True

    # ─── Start Ride ───
    def start_ride(self, ride_id: int) -> bool:
        ride = self.rides.get(ride_id)
        if not ride:
            print("   ❌ Ride not found!")
            return False

        if ride.status != RideStatus.DRIVER_ASSIGNED:
            print(f"   ❌ Ride is {ride.status.name}, cannot start!")
            return False

        ride.status = RideStatus.IN_PROGRESS
        ride.start_time = datetime.now()
        print(f"   🚀 Ride#{ride_id} started! {ride.rider.name} picked up by {ride.driver.name}")
        return True

    # ─── Complete Ride ───
    def complete_ride(self, ride_id: int, payment: PaymentStrategy, duration_min: float = None) -> float:
        ride = self.rides.get(ride_id)
        if not ride:
            print("   ❌ Ride not found!")
            return 0

        if ride.status != RideStatus.IN_PROGRESS:
            print(f"   ❌ Ride is {ride.status.name}, cannot complete!")
            return 0

        ride.end_time = datetime.now()
        ride.status = RideStatus.COMPLETED

        # Calculate fare
        pricing = PRICING[ride.vehicle_type]
        if duration_min is None:
            duration_min = random.randint(15, 45)  # Simulate duration

        fare = (pricing["base"]
                + ride.distance_km * pricing["per_km"]
                + duration_min * pricing["per_min"]) * self.surge_multiplier
        ride.fare = round(fare, 0)

        # Process payment
        print(f"   🏁 Ride#{ride_id} completed!")
        print(f"      Distance: {ride.distance_km:.1f} km | Duration: {duration_min:.0f} min | Surge: {self.surge_multiplier}x")
        print(f"      Fare breakdown: ₹{pricing['base']} base + {ride.distance_km:.1f}×₹{pricing['per_km']}/km"
              f" + {duration_min:.0f}×₹{pricing['per_min']}/min = ₹{ride.fare:.0f}")
        payment.pay(ride.fare)

        # Free up driver
        ride.driver.status = DriverStatus.AVAILABLE
        ride.driver.location = ride.drop  # Driver is now at drop location
        return ride.fare

    # ─── Cancel Ride ───
    def cancel_ride(self, ride_id: int) -> bool:
        ride = self.rides.get(ride_id)
        if not ride:
            print("   ❌ Ride not found!")
            return False

        if ride.status in (RideStatus.COMPLETED, RideStatus.CANCELLED):
            print(f"   ❌ Ride is already {ride.status.name}!")
            return False

        # Free driver if assigned
        if ride.driver and ride.driver.status == DriverStatus.ON_RIDE:
            ride.driver.status = DriverStatus.AVAILABLE
            print(f"   🔓 {ride.driver.name} is now available again")

        ride.status = RideStatus.CANCELLED
        print(f"   🚫 Ride#{ride_id} cancelled!")
        return True

    # ─── Rating ───
    def rate_driver(self, ride_id: int, rating: float):
        ride = self.rides.get(ride_id)
        if not ride or ride.status != RideStatus.COMPLETED:
            print("   ❌ Can only rate completed rides!")
            return
        ride.driver.add_rating(rating)
        print(f"   ⭐ {ride.rider.name} rated {ride.driver.name}: {rating}/5")

    def rate_rider(self, ride_id: int, rating: float):
        ride = self.rides.get(ride_id)
        if not ride or ride.status != RideStatus.COMPLETED:
            print("   ❌ Can only rate completed rides!")
            return
        ride.rider.add_rating(rating)
        print(f"   ⭐ {ride.driver.name} rated {ride.rider.name}: {rating}/5")


# ═══════════════════════════════════════════════════════════════
#                        DEMO
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("        CAB BOOKING SYSTEM (UBER) - LLD DEMO")
    print("=" * 60)

    system = CabBookingSystem()

    # ─── Register Riders ───
    print("\n👥 Registering Riders:")
    r1 = system.register_rider(1, "Nikhil", Location(10, 20))
    r2 = system.register_rider(2, "Priya", Location(15, 25))
    print(f"   {r1}")
    print(f"   {r2}")

    # ─── Register Drivers ───
    print("\n🚗 Registering Drivers:")
    d1 = system.register_driver(1, "Raju", VehicleType.SEDAN, Location(11, 21))    # 1.4 km from Nikhil
    d2 = system.register_driver(2, "Kumar", VehicleType.SEDAN, Location(8, 18))    # 2.8 km from Nikhil
    d3 = system.register_driver(3, "Suresh", VehicleType.AUTO, Location(12, 22))   # AUTO, not SEDAN
    d4 = system.register_driver(4, "Venkat", VehicleType.SUV, Location(9, 19))     # SUV
    for d in [d1, d2, d3, d4]:
        print(f"   {d}")

    # ═══════════════════════════════════════════════════════════
    #  TEST 1: Normal Ride Flow (SEDAN)
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 60)
    print("  TEST 1: Normal Ride Flow (SEDAN)")
    print("─" * 60)

    print("\n① Nikhil requests a SEDAN ride:")
    ride1 = system.request_ride(1, Location(10, 20), Location(30, 40), VehicleType.SEDAN)

    print("\n② Raju (closest) accepts:")
    system.accept_ride(1, ride1.ride_id)

    print("\n③ Ride starts:")
    system.start_ride(ride1.ride_id)

    print("\n④ Ride completes (25 min):")
    system.complete_ride(ride1.ride_id, UPIPayment(), duration_min=25)

    print("\n⑤ Ratings:")
    system.rate_driver(ride1.ride_id, 4.5)
    system.rate_rider(ride1.ride_id, 5.0)

    # ═══════════════════════════════════════════════════════════
    #  TEST 2: Surge Pricing (1.5x)
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 60)
    print("  TEST 2: Surge Pricing (1.5x)")
    print("─" * 60)

    system.set_surge(1.5)

    print("\n① Priya requests a SEDAN ride:")
    ride2 = system.request_ride(2, Location(15, 25), Location(35, 45), VehicleType.SEDAN)

    print("\n② Raju accepts (he's now at (30,40) from last ride):")
    system.accept_ride(1, ride2.ride_id)

    print("\n③ Ride starts & completes (30 min, with 1.5x surge):")
    system.start_ride(ride2.ride_id)
    system.complete_ride(ride2.ride_id, CardPayment(), duration_min=30)

    system.set_surge(1.0)  # Reset surge

    # ═══════════════════════════════════════════════════════════
    #  TEST 3: Cancellation
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 60)
    print("  TEST 3: Ride Cancellation")
    print("─" * 60)

    print("\n① Nikhil requests an AUTO ride:")
    ride3 = system.request_ride(1, Location(10, 20), Location(20, 30), VehicleType.AUTO)

    print("\n② Suresh accepts:")
    system.accept_ride(3, ride3.ride_id)

    print("\n③ Nikhil cancels the ride:")
    system.cancel_ride(ride3.ride_id)

    # ═══════════════════════════════════════════════════════════
    #  TEST 4: No Drivers Available
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 60)
    print("  TEST 4: No Drivers Available")
    print("─" * 60)

    print("\n① Nikhil requests an SUV ride:")
    # Venkat is the only SUV driver
    d4.go_offline()
    print(f"   (Venkat went offline: {d4})")
    ride4 = system.request_ride(1, Location(10, 20), Location(50, 50), VehicleType.SUV)

    d4.go_online()  # Back online

    # ═══════════════════════════════════════════════════════════
    #  TEST 5: State Validation
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 60)
    print("  TEST 5: State Validation")
    print("─" * 60)

    print("\n① Try to complete a cancelled ride:")
    system.complete_ride(ride3.ride_id, CashPayment())

    print("\n② Try to cancel a completed ride:")
    system.cancel_ride(ride1.ride_id)

    # ═══════════════════════════════════════════════════════════
    #  FINAL STATE
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 60)
    print("  FINAL STATE")
    print("─" * 60)

    print("\n📊 Drivers:")
    for d in system.drivers.values():
        print(f"   {d}")

    print("\n📊 Riders:")
    for r in system.riders.values():
        print(f"   {r}")

    print("\n📊 All Rides:")
    for ride in system.rides.values():
        print(f"   {ride}")

    print(f"\n🔒 Singleton: {system is CabBookingSystem()} ✓")

    print("\n" + "=" * 60)
    print("        ALL TESTS COMPLETE! 🎉")
    print("=" * 60)