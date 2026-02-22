from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import math

# ============ ENUMS ============

class SpotType(Enum):
    SMALL = 1       # For motorcycles
    COMPACT = 2     # For cars
    LARGE = 3       # For trucks

class SpotStatus(Enum):
    AVAILABLE = "AVAILABLE"
    OCCUPIED = "OCCUPIED"

class VehicleType(Enum):
    MOTORCYCLE = "MOTORCYCLE"
    CAR = "CAR"
    TRUCK = "TRUCK"

class TicketStatus(Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


# ============ VEHICLE HIERARCHY ============

class Vehicle(ABC):
    def __init__(self, licence_number: str):
        self.licence_number = licence_number
    
    @abstractmethod
    def get_vehicle_type(self) -> VehicleType:
        pass
    
    @abstractmethod
    def get_required_spot_type(self) -> SpotType:
        pass
    
    def __str__(self):
        return f"{self.get_vehicle_type().value}({self.licence_number})"


class Motorcycle(Vehicle):
    def get_vehicle_type(self) -> VehicleType:
        return VehicleType.MOTORCYCLE
    
    def get_required_spot_type(self) -> SpotType:
        return SpotType.SMALL


class Car(Vehicle):
    def get_vehicle_type(self) -> VehicleType:
        return VehicleType.CAR
    
    def get_required_spot_type(self) -> SpotType:
        return SpotType.COMPACT


class Truck(Vehicle):
    def get_vehicle_type(self) -> VehicleType:
        return VehicleType.TRUCK
    
    def get_required_spot_type(self) -> SpotType:
        return SpotType.LARGE


# ============ VEHICLE FACTORY ============

class VehicleFactory:
    @staticmethod
    def create_vehicle(licence_number: str, vehicle_type: VehicleType) -> Vehicle:
        if vehicle_type == VehicleType.MOTORCYCLE:
            return Motorcycle(licence_number)
        elif vehicle_type == VehicleType.CAR:
            return Car(licence_number)
        elif vehicle_type == VehicleType.TRUCK:
            return Truck(licence_number)
        else:
            raise ValueError(f"Unknown vehicle type: {vehicle_type}")


# ============ PARKING SPOT ============

class Spot:
    def __init__(self, spot_id: int, spot_type: SpotType, floor_number: int):
        self.spot_id = spot_id
        self.spot_type = spot_type
        self.floor_number = floor_number
        self.status = SpotStatus.AVAILABLE
        self.vehicle = None  # Currently parked vehicle
    
    def can_fit(self, vehicle: Vehicle) -> bool:
        """Check if spot can fit the vehicle (spot size >= vehicle required size)."""
        return self.spot_type.value >= vehicle.get_required_spot_type().value
    
    def is_available(self) -> bool:
        return self.status == SpotStatus.AVAILABLE
    
    def park(self, vehicle: Vehicle):
        if not self.is_available():
            raise Exception(f"Spot {self.spot_id} is not available")
        if not self.can_fit(vehicle):
            raise Exception(f"Spot {self.spot_id} cannot fit {vehicle}")
        self.vehicle = vehicle
        self.status = SpotStatus.OCCUPIED
    
    def unpark(self) -> Vehicle:
        if self.status != SpotStatus.OCCUPIED:
            raise Exception(f"Spot {self.spot_id} is not occupied")
        vehicle = self.vehicle
        self.vehicle = None
        self.status = SpotStatus.AVAILABLE
        return vehicle
    
    def __str__(self):
        status = "🚗" if self.status == SpotStatus.OCCUPIED else "✅"
        return f"Spot(F{self.floor_number}-{self.spot_id}, {self.spot_type.name}, {status})"


# ============ SPOT FACTORY ============

class SpotFactory:
    @staticmethod
    def create_spots(floor_number: int, small: int, compact: int, large: int) -> list:
        spots = []
        spot_id = 1
        
        for _ in range(small):
            spots.append(Spot(spot_id, SpotType.SMALL, floor_number))
            spot_id += 1
        
        for _ in range(compact):
            spots.append(Spot(spot_id, SpotType.COMPACT, floor_number))
            spot_id += 1
        
        for _ in range(large):
            spots.append(Spot(spot_id, SpotType.LARGE, floor_number))
            spot_id += 1
        
        return spots


# ============ FLOOR ============

class Floor:
    def __init__(self, floor_number: int, small: int = 5, compact: int = 10, large: int = 3):
        self.floor_number = floor_number
        self.spots = SpotFactory.create_spots(floor_number, small, compact, large)
    
    def get_available_spots(self) -> list:
        return [spot for spot in self.spots if spot.is_available()]
    
    def get_available_spots_for_vehicle(self, vehicle: Vehicle) -> list:
        return [spot for spot in self.spots 
                if spot.is_available() and spot.can_fit(vehicle)]
    
    def get_available_count(self) -> dict:
        counts = {SpotType.SMALL: 0, SpotType.COMPACT: 0, SpotType.LARGE: 0}
        for spot in self.spots:
            if spot.is_available():
                counts[spot.spot_type] += 1
        return counts
    
    def __str__(self):
        counts = self.get_available_count()
        return f"Floor {self.floor_number}: Small={counts[SpotType.SMALL]}, Compact={counts[SpotType.COMPACT]}, Large={counts[SpotType.LARGE]}"


# ============ TICKET ============

class Ticket:
    def __init__(self, ticket_id: int, vehicle: Vehicle, spot: Spot):
        self.ticket_id = ticket_id
        self.vehicle = vehicle
        self.spot = spot
        self.entry_time = datetime.now()
        self.exit_time = None
        self.status = TicketStatus.ACTIVE
    
    def complete(self):
        self.exit_time = datetime.now()
        self.status = TicketStatus.COMPLETED
    
    def get_duration_hours(self) -> float:
        end_time = self.exit_time or datetime.now()
        duration = end_time - self.entry_time
        return duration.total_seconds() / 3600
    
    def __str__(self):
        duration = self.get_duration_hours()
        return f"Ticket({self.ticket_id}, {self.vehicle}, {self.spot}, {duration:.2f}hrs, {self.status.value})"


# ============ ALLOCATION STRATEGY ============

class AllocationStrategy(ABC):
    @abstractmethod
    def find_spot(self, floors: list, vehicle: Vehicle) -> Spot:
        pass


class FirstAvailableStrategy(AllocationStrategy):
    """Find the first available spot that fits the vehicle."""
    def find_spot(self, floors: list, vehicle: Vehicle) -> Spot:
        for floor in floors:
            for spot in floor.spots:
                if spot.is_available() and spot.can_fit(vehicle):
                    return spot
        return None


class BestFitStrategy(AllocationStrategy):
    """Find the smallest spot that fits the vehicle (to save larger spots)."""
    def find_spot(self, floors: list, vehicle: Vehicle) -> Spot:
        required_size = vehicle.get_required_spot_type().value
        
        # Try to find exact match first
        for floor in floors:
            for spot in floor.spots:
                if spot.is_available() and spot.spot_type.value == required_size:
                    return spot
        
        # If no exact match, find next larger
        for floor in floors:
            for spot in floor.spots:
                if spot.is_available() and spot.can_fit(vehicle):
                    return spot
        
        return None


# ============ PRICING STRATEGY ============

class PricingStrategy(ABC):
    @abstractmethod
    def calculate_fee(self, vehicle: Vehicle, hours: float) -> float:
        pass


class HourlyPricing(PricingStrategy):
    """Charge per hour based on vehicle type."""
    RATES = {
        VehicleType.MOTORCYCLE: 20,
        VehicleType.CAR: 40,
        VehicleType.TRUCK: 60
    }
    
    def calculate_fee(self, vehicle: Vehicle, hours: float) -> float:
        rate = self.RATES[vehicle.get_vehicle_type()]
        return rate * math.ceil(hours)  # Round up to next hour


class FlatPricing(PricingStrategy):
    """Flat rate for up to 4 hours, then hourly after."""
    FLAT_RATES = {
        VehicleType.MOTORCYCLE: 50,
        VehicleType.CAR: 100,
        VehicleType.TRUCK: 150
    }
    THRESHOLD_HOURS = 4
    
    def calculate_fee(self, vehicle: Vehicle, hours: float) -> float:
        flat_rate = self.FLAT_RATES[vehicle.get_vehicle_type()]
        if hours <= self.THRESHOLD_HOURS:
            return flat_rate
        else:
            extra_hours = hours - self.THRESHOLD_HOURS
            hourly_rate = flat_rate / self.THRESHOLD_HOURS
            return flat_rate + (hourly_rate * math.ceil(extra_hours))


# ============ PAYMENT STRATEGY ============

class PaymentStrategy(ABC):
    @abstractmethod
    def pay(self, amount: float) -> bool:
        pass


class CreditCardPayment(PaymentStrategy):
    def pay(self, amount: float) -> bool:
        print(f"💳 Paid ₹{amount:.2f} using Credit Card")
        return True


class UPIPayment(PaymentStrategy):
    def pay(self, amount: float) -> bool:
        print(f"📱 Paid ₹{amount:.2f} using UPI")
        return True


class CashPayment(PaymentStrategy):
    def pay(self, amount: float) -> bool:
        print(f"💵 Paid ₹{amount:.2f} in Cash")
        return True


# ============ PARKING LOT (Singleton) ============

class ParkingLot:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ParkingLot, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.floors = []
        self.tickets = {}  # ticket_id -> Ticket
        self._ticket_counter = 0
        
        # Strategies (can be changed)
        self.allocation_strategy = FirstAvailableStrategy()
        self.pricing_strategy = HourlyPricing()
    
    # ---- Configuration ----
    def add_floor(self, floor: Floor):
        self.floors.append(floor)
        print(f"✅ Added {floor}")
    
    def set_allocation_strategy(self, strategy: AllocationStrategy):
        self.allocation_strategy = strategy
        print(f"🔧 Allocation strategy set to: {strategy.__class__.__name__}")
    
    def set_pricing_strategy(self, strategy: PricingStrategy):
        self.pricing_strategy = strategy
        print(f"🔧 Pricing strategy set to: {strategy.__class__.__name__}")
    
    # ---- Core Operations ----
    def park_vehicle(self, vehicle: Vehicle) -> Ticket:
        """Park a vehicle and return a ticket."""
        # Find available spot using strategy
        spot = self.allocation_strategy.find_spot(self.floors, vehicle)
        
        if not spot:
            raise Exception(f"❌ No spot available for {vehicle}")
        
        # Park the vehicle
        spot.park(vehicle)
        
        # Issue ticket
        self._ticket_counter += 1
        ticket = Ticket(self._ticket_counter, vehicle, spot)
        self.tickets[ticket.ticket_id] = ticket
        
        print(f"✅ Parked {vehicle} at {spot}")
        return ticket
    
    def unpark_vehicle(self, ticket_id: int, payment_strategy: PaymentStrategy) -> float:
        """Unpark a vehicle, calculate fee, process payment."""
        if ticket_id not in self.tickets:
            raise Exception(f"❌ Ticket {ticket_id} not found")
        
        ticket = self.tickets[ticket_id]
        
        if ticket.status == TicketStatus.COMPLETED:
            raise Exception(f"❌ Ticket {ticket_id} already completed")
        
        # Complete the ticket
        ticket.complete()
        
        # Calculate fee
        hours = ticket.get_duration_hours()
        fee = self.pricing_strategy.calculate_fee(ticket.vehicle, hours)
        
        # Process payment
        payment_strategy.pay(fee)
        
        # Free the spot
        ticket.spot.unpark()
        
        print(f"✅ {ticket.vehicle} exited. Duration: {hours:.2f} hrs")
        return fee
    
    # ---- Display ----
    def show_availability(self):
        print("\n--- Parking Lot Availability ---")
        total = {SpotType.SMALL: 0, SpotType.COMPACT: 0, SpotType.LARGE: 0}
        for floor in self.floors:
            print(f"  {floor}")
            counts = floor.get_available_count()
            for spot_type, count in counts.items():
                total[spot_type] += count
        print(f"  TOTAL: Small={total[SpotType.SMALL]}, Compact={total[SpotType.COMPACT]}, Large={total[SpotType.LARGE]}")
    
    def is_full(self) -> bool:
        for floor in self.floors:
            if floor.get_available_spots():
                return False
        return True


# ============ DEMO ============

if __name__ == "__main__":
    print("=" * 60)
    print("PARKING LOT SYSTEM - DEMO")
    print("=" * 60)
    
    # Get singleton instance
    lot = ParkingLot()
    
    # 1. Add floors
    print("\n--- 1. Setting Up Parking Lot ---")
    lot.add_floor(Floor(1, small=3, compact=5, large=2))
    lot.add_floor(Floor(2, small=2, compact=5, large=2))
    
    # 2. Show initial availability
    lot.show_availability()
    
    # 3. Create vehicles using Factory
    print("\n--- 2. Vehicles Arriving ---")
    car1 = VehicleFactory.create_vehicle("KA-01-AB-1234", VehicleType.CAR)
    car2 = VehicleFactory.create_vehicle("KA-02-CD-5678", VehicleType.CAR)
    bike = VehicleFactory.create_vehicle("KA-03-EF-9012", VehicleType.MOTORCYCLE)
    truck = VehicleFactory.create_vehicle("KA-04-GH-3456", VehicleType.TRUCK)
    
    # 4. Park vehicles
    print("\n--- 3. Parking Vehicles ---")
    ticket1 = lot.park_vehicle(car1)
    ticket2 = lot.park_vehicle(car2)
    ticket3 = lot.park_vehicle(bike)
    ticket4 = lot.park_vehicle(truck)
    
    # 5. Show availability after parking
    lot.show_availability()
    
    # 6. Simulate time passing (for demo, we'll manually set exit time)
    print("\n--- 4. Time Passes (Simulating 2 hours) ---")
    ticket1.entry_time = datetime.now() - timedelta(hours=2)
    ticket2.entry_time = datetime.now() - timedelta(hours=3.5)
    ticket3.entry_time = datetime.now() - timedelta(hours=1)
    ticket4.entry_time = datetime.now() - timedelta(hours=5)
    
    # 7. Unpark and pay
    print("\n--- 5. Vehicles Exiting ---")
    lot.unpark_vehicle(ticket1.ticket_id, CreditCardPayment())
    lot.unpark_vehicle(ticket2.ticket_id, UPIPayment())
    lot.unpark_vehicle(ticket3.ticket_id, CashPayment())
    
    # 8. Show availability after some exits
    lot.show_availability()
    
    # 9. Change pricing strategy to Flat
    print("\n--- 6. Switch to Flat Pricing ---")
    lot.set_pricing_strategy(FlatPricing())
    lot.unpark_vehicle(ticket4.ticket_id, CreditCardPayment())
    
    # 10. Try to park when full (simulate)
    print("\n--- 7. Testing Full Lot Handling ---")
    # Park many cars
    tickets = []
    for i in range(15):
        try:
            v = VehicleFactory.create_vehicle(f"TEST-{i}", VehicleType.CAR)
            t = lot.park_vehicle(v)
            tickets.append(t)
        except Exception as e:
            print(f"⚠️ {e}")
            break
    
    lot.show_availability()
    print(f"Is lot full? {lot.is_full()}")
    
    # 11. Change allocation strategy
    print("\n--- 8. Switch to Best Fit Allocation ---")
    lot.set_allocation_strategy(BestFitStrategy())
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETED!")
    print("=" * 60)