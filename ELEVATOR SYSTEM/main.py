from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict
import time

# ============ ENUMS ============

class Direction(Enum):
    UP = 1
    DOWN = -1
    IDLE = 0

class ElevatorState(Enum):
    IDLE = "IDLE"
    MOVING = "MOVING"
    DOOR_OPEN = "DOOR_OPEN"


# ============ OBSERVER PATTERN ============

class Observer(ABC):
    """Observer interface for floor displays."""
    @abstractmethod
    def update(self, elevator_id: int, current_floor: int, direction: Direction):
        pass


class Subject(ABC):
    """Subject that notifies observers."""
    def __init__(self):
        self._observers: List[Observer] = []
    
    def add_observer(self, observer: Observer):
        if observer not in self._observers:
            self._observers.append(observer)
    
    def remove_observer(self, observer: Observer):
        if observer in self._observers:
            self._observers.remove(observer)
    
    def notify_observers(self, elevator_id: int, current_floor: int, direction: Direction):
        for observer in self._observers:
            observer.update(elevator_id, current_floor, direction)


# ============ FLOOR (Observer) ============

class Floor(Observer):
    """Floor with display panel that shows all elevator positions."""
    def __init__(self, floor_id: int):
        self.floor_id = floor_id
        self.up_button_pressed = False
        self.down_button_pressed = False
        # Display: elevator_id -> (current_floor, direction)
        self.elevator_display: Dict[int, tuple] = {}
    
    def press_up(self):
        self.up_button_pressed = True
        print(f"🔼 Floor {self.floor_id}: UP button pressed")
    
    def press_down(self):
        self.down_button_pressed = True
        print(f"🔽 Floor {self.floor_id}: DOWN button pressed")
    
    def reset_button(self, direction: Direction):
        if direction == Direction.UP:
            self.up_button_pressed = False
        elif direction == Direction.DOWN:
            self.down_button_pressed = False
    
    def update(self, elevator_id: int, current_floor: int, direction: Direction):
        """Observer method: Called when any elevator moves."""
        self.elevator_display[elevator_id] = (current_floor, direction)
        # Only print for the floor where elevator currently is
        if current_floor == self.floor_id:
            dir_symbol = "↑" if direction == Direction.UP else "↓" if direction == Direction.DOWN else "•"
            print(f"📟 Floor {self.floor_id} Display: Elevator {elevator_id} is HERE {dir_symbol}")
    
    def elevator_arrived(self, elevator_id: int, direction: Direction):
        """Called when elevator doors open at this floor."""
        print(f"🔔 Floor {self.floor_id}: *DING* Elevator {elevator_id} arrived!")
        self.reset_button(direction)
    
    def show_display(self):
        """Show all elevator positions on this floor's display."""
        print(f"\n📟 Floor {self.floor_id} Display Panel:")
        for elev_id, (floor, direction) in self.elevator_display.items():
            dir_symbol = "↑" if direction == Direction.UP else "↓" if direction == Direction.DOWN else "•"
            print(f"    Elevator {elev_id}: Floor {floor} {dir_symbol}")


# ============ ELEVATOR (Subject) ============

class Elevator(Subject):
    """Elevator that notifies all floors when it moves."""
    def __init__(self, elevator_id: int, total_floors: int):
        super().__init__()  # Initialize observers list
        self.elevator_id = elevator_id
        self.total_floors = total_floors
        self.current_floor = 1
        self.direction = Direction.IDLE
        self.state = ElevatorState.IDLE
        self.destination_floors: List[int] = []
        self.floors_map: Dict[int, Floor] = {}  # Reference to floors for arrival notification
    
    def set_floors(self, floors: Dict[int, Floor]):
        """Set reference to all floors for arrival notifications."""
        self.floors_map = floors
    
    def add_stop(self, floor: int):
        """Add a floor to the destination list."""
        if floor not in self.destination_floors and 1 <= floor <= self.total_floors:
            self.destination_floors.append(floor)
            # Sort based on direction for efficiency
            if self.direction == Direction.UP or self.direction == Direction.IDLE:
                self.destination_floors.sort()
            else:
                self.destination_floors.sort(reverse=True)
            
            if self.state == ElevatorState.IDLE:
                self._determine_direction()
            
            print(f"🛗 Elevator {self.elevator_id}: Added stop at Floor {floor}. Pending: {self.destination_floors}")
    
    def _determine_direction(self):
        """Determine direction based on next destination."""
        if not self.destination_floors:
            self.direction = Direction.IDLE
            self.state = ElevatorState.IDLE
        elif self.destination_floors[0] > self.current_floor:
            self.direction = Direction.UP
            self.state = ElevatorState.MOVING
        elif self.destination_floors[0] < self.current_floor:
            self.direction = Direction.DOWN
            self.state = ElevatorState.MOVING
        else:
            # Already at destination
            self.open_door()
    
    def move(self):
        """Move elevator one step. Call this in simulation loop."""
        if self.state != ElevatorState.MOVING or not self.destination_floors:
            return
        
        # Move one floor in current direction
        if self.direction == Direction.UP:
            self.current_floor += 1
        elif self.direction == Direction.DOWN:
            self.current_floor -= 1
        
        # Notify ALL floors about position change (for displays)
        self.notify_observers(self.elevator_id, self.current_floor, self.direction)
        
        print(f"🛗 Elevator {self.elevator_id}: Now at Floor {self.current_floor}")
        
        # Check if we need to stop here
        if self.current_floor in self.destination_floors:
            self.open_door()
    
    def open_door(self):
        """Open door, notify floor, remove from destinations."""
        self.state = ElevatorState.DOOR_OPEN
        print(f"🚪 Elevator {self.elevator_id}: Door OPENING at Floor {self.current_floor}")
        
        # Notify the specific floor that elevator arrived
        if self.current_floor in self.floors_map:
            self.floors_map[self.current_floor].elevator_arrived(self.elevator_id, self.direction)
        
        # Simulate door open time
        # time.sleep(1)  # Uncomment for real timing
        
        # Remove this floor from destinations
        if self.current_floor in self.destination_floors:
            self.destination_floors.remove(self.current_floor)
        
        self.close_door()
    
    def close_door(self):
        """Close door and determine next action."""
        print(f"🚪 Elevator {self.elevator_id}: Door CLOSING at Floor {self.current_floor}")
        
        if self.destination_floors:
            self._determine_direction()
        else:
            self.direction = Direction.IDLE
            self.state = ElevatorState.IDLE
            print(f"🛗 Elevator {self.elevator_id}: Now IDLE at Floor {self.current_floor}")
    
    def __str__(self):
        dir_symbol = "↑" if self.direction == Direction.UP else "↓" if self.direction == Direction.DOWN else "•"
        return f"Elevator {self.elevator_id}: Floor {self.current_floor} {dir_symbol} ({self.state.value})"


# ============ DISPATCH STRATEGY ============

class DispatchStrategy(ABC):
    @abstractmethod
    def select_elevator(self, elevators: Dict[int, Elevator], 
                        floor: int, direction: Direction) -> Elevator:
        pass


class NearestElevatorStrategy(DispatchStrategy):
    """Select the nearest elevator, prefer same direction or idle."""
    def select_elevator(self, elevators: Dict[int, Elevator], 
                        floor: int, direction: Direction) -> Elevator:
        elevator_list = list(elevators.values())
        
        # Priority 1: Same direction and will pass this floor
        same_direction = []
        for e in elevator_list:
            if e.direction == direction:
                if direction == Direction.UP and e.current_floor <= floor:
                    same_direction.append(e)
                elif direction == Direction.DOWN and e.current_floor >= floor:
                    same_direction.append(e)
        
        if same_direction:
            return min(same_direction, key=lambda x: abs(x.current_floor - floor))
        
        # Priority 2: Idle elevators
        idle = [e for e in elevator_list if e.state == ElevatorState.IDLE]
        if idle:
            return min(idle, key=lambda x: abs(x.current_floor - floor))
        
        # Priority 3: Any nearest
        return min(elevator_list, key=lambda x: abs(x.current_floor - floor))


class LeastLoadedStrategy(DispatchStrategy):
    """Select elevator with fewest pending stops."""
    def select_elevator(self, elevators: Dict[int, Elevator], 
                        floor: int, direction: Direction) -> Elevator:
        elevator_list = list(elevators.values())
        return min(elevator_list, key=lambda x: len(x.destination_floors))


# ============ ELEVATOR CONTROLLER (Singleton) ============

class ElevatorController:
    """Singleton controller that manages all elevators and floors."""
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(ElevatorController, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, floor_count: int = 10, elevator_count: int = 2):
        if self._initialized:
            return
        self._initialized = True
        
        # Create floors
        self.floors: Dict[int, Floor] = {i: Floor(i) for i in range(1, floor_count + 1)}
        
        # Create elevators
        self.elevators: Dict[int, Elevator] = {}
        for i in range(1, elevator_count + 1):
            elevator = Elevator(i, floor_count)
            elevator.set_floors(self.floors)
            
            # Subscribe ALL floors to each elevator (for display updates)
            for floor in self.floors.values():
                elevator.add_observer(floor)
            
            self.elevators[i] = elevator
        
        self.strategy: DispatchStrategy = NearestElevatorStrategy()
        
        print(f"✅ Elevator System initialized: {floor_count} floors, {elevator_count} elevators")
    
    def set_strategy(self, strategy: DispatchStrategy):
        """Change dispatch strategy."""
        self.strategy = strategy
        print(f"🔧 Strategy changed to: {strategy.__class__.__name__}")
    
    def request_elevator(self, floor: int, direction: Direction):
        """External request: UP/DOWN button pressed at a floor."""
        print(f"\n📢 Request: Floor {floor}, Direction: {'UP' if direction == Direction.UP else 'DOWN'}")
        
        # Press the button on the floor
        if direction == Direction.UP:
            self.floors[floor].press_up()
        else:
            self.floors[floor].press_down()
        
        # Select elevator using strategy
        elevator = self.strategy.select_elevator(self.elevators, floor, direction)
        print(f"📌 Assigned to Elevator {elevator.elevator_id}")
        
        # Add stop
        elevator.add_stop(floor)
    
    def select_floor(self, elevator_id: int, floor: int):
        """Internal request: button pressed inside elevator."""
        print(f"\n📢 Internal: Elevator {elevator_id}, Destination: Floor {floor}")
        self.elevators[elevator_id].add_stop(floor)
    
    def step(self):
        """Simulate one time unit - all elevators move."""
        for elevator in self.elevators.values():
            elevator.move()
    
    def run_simulation(self, steps: int = 10):
        """Run simulation for given steps."""
        print(f"\n{'='*50}")
        print("SIMULATION RUNNING")
        print(f"{'='*50}")
        
        for i in range(steps):
            print(f"\n--- Step {i+1} ---")
            self.step()
            
            # Check if all elevators are idle
            all_idle = all(e.state == ElevatorState.IDLE for e in self.elevators.values())
            if all_idle:
                print("All elevators idle. Stopping simulation.")
                break
    
    def show_status(self):
        """Show current status of all elevators."""
        print(f"\n{'='*50}")
        print("ELEVATOR STATUS")
        print(f"{'='*50}")
        for elevator in self.elevators.values():
            print(f"  {elevator}")
        print(f"{'='*50}")


# ============ DEMO ============

if __name__ == "__main__":
    print("=" * 60)
    print("ELEVATOR SYSTEM - DEMO")
    print("=" * 60)
    
    # Reset singleton for demo
    ElevatorController._instance = None
    
    # Create controller with 5 floors and 2 elevators
    controller = ElevatorController(floor_count=5, elevator_count=2)
    
    # Show initial status
    controller.show_status()
    
    # Scenario 1: Person at Floor 3 presses UP
    controller.request_elevator(floor=3, direction=Direction.UP)
    
    # Scenario 2: Person at Floor 5 presses DOWN
    controller.request_elevator(floor=5, direction=Direction.DOWN)
    
    # Run simulation
    controller.run_simulation(steps=10)
    
    # Show status after simulation
    controller.show_status()
    
    # Scenario 3: Person enters Elevator 1 and presses Floor 5
    print("\n--- Internal Request ---")
    controller.select_floor(elevator_id=1, floor=5)
    
    # Run more simulation
    controller.run_simulation(steps=10)
    
    # Final status
    controller.show_status()
    
    # Show floor display
    print("\n--- Floor Displays ---")
    for floor in controller.floors.values():
        floor.show_display()
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETED!")
    print("=" * 60)