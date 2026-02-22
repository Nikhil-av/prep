from enum import Enum
from abc import ABC, abstractmethod

# ============ ENUMS ============

class Coin(Enum):
    ONE = 1
    TWO = 2
    FIVE = 5
    TEN = 10

class Ingredient(Enum):
    COFFEE = "COFFEE"
    MILK = "MILK"
    WATER = "WATER"
    SUGAR = "SUGAR"


# ============ COFFEE BASE (Decorator Pattern) ============

class Coffee(ABC):
    @abstractmethod
    def get_cost(self) -> int:
        pass

    @abstractmethod
    def get_description(self) -> str:
        pass

    @abstractmethod
    def get_recipe(self) -> dict:
        """Returns {Ingredient: amount}"""
        pass


# ============ CONCRETE COFFEES ============

class Espresso(Coffee):
    def get_cost(self) -> int:
        return 30

    def get_description(self) -> str:
        return "Espresso"

    def get_recipe(self) -> dict:
        return {
            Ingredient.COFFEE: 2,
            Ingredient.WATER: 1,
            Ingredient.SUGAR: 1
        }


class Latte(Coffee):
    def get_cost(self) -> int:
        return 40

    def get_description(self) -> str:
        return "Latte"

    def get_recipe(self) -> dict:
        return {
            Ingredient.COFFEE: 1,
            Ingredient.MILK: 2,
            Ingredient.WATER: 1,
            Ingredient.SUGAR: 1
        }


class Cappuccino(Coffee):
    def get_cost(self) -> int:
        return 50

    def get_description(self) -> str:
        return "Cappuccino"

    def get_recipe(self) -> dict:
        return {
            Ingredient.COFFEE: 1,
            Ingredient.MILK: 1,
            Ingredient.WATER: 1,
            Ingredient.SUGAR: 2
        }


# ============ COFFEE DECORATORS ============

class CoffeeDecorator(Coffee):
    """Abstract decorator that wraps a Coffee object."""
    
    def __init__(self, coffee: Coffee):
        self._coffee = coffee

    def get_cost(self) -> int:
        return self._coffee.get_cost()

    def get_description(self) -> str:
        return self._coffee.get_description()

    def get_recipe(self) -> dict:
        return self._coffee.get_recipe().copy()


class SugarDecorator(CoffeeDecorator):
    """Adds extra sugar to the coffee."""
    
    def get_cost(self) -> int:
        return self._coffee.get_cost() + 5

    def get_description(self) -> str:
        return self._coffee.get_description() + " + Extra Sugar"

    def get_recipe(self) -> dict:
        recipe = self._coffee.get_recipe().copy()
        recipe[Ingredient.SUGAR] = recipe.get(Ingredient.SUGAR, 0) + 1
        return recipe


class MilkDecorator(CoffeeDecorator):
    """Adds extra milk to the coffee."""
    
    def get_cost(self) -> int:
        return self._coffee.get_cost() + 10

    def get_description(self) -> str:
        return self._coffee.get_description() + " + Extra Milk"

    def get_recipe(self) -> dict:
        recipe = self._coffee.get_recipe().copy()
        recipe[Ingredient.MILK] = recipe.get(Ingredient.MILK, 0) + 1
        return recipe


# ============ INGREDIENT INVENTORY ============

class IngredientInventory:
    def __init__(self):
        # Initialize with some stock
        self._inventory = {
            Ingredient.COFFEE: 10,
            Ingredient.MILK: 10,
            Ingredient.WATER: 10,
            Ingredient.SUGAR: 10
        }

    def get_quantity(self, ingredient: Ingredient) -> int:
        return self._inventory.get(ingredient, 0)

    def add_ingredient(self, ingredient: Ingredient, quantity: int):
        """Admin refill operation."""
        if quantity < 0:
            raise ValueError("Cannot add negative quantity")
        self._inventory[ingredient] = self._inventory.get(ingredient, 0) + quantity

    def use_ingredient(self, ingredient: Ingredient, quantity: int):
        """Deduct ingredients when making coffee."""
        if self._inventory.get(ingredient, 0) < quantity:
            raise ValueError(f"Insufficient {ingredient.value}")
        self._inventory[ingredient] -= quantity

    def has_enough_for(self, recipe: dict) -> bool:
        """Check if all ingredients in recipe are available."""
        for ingredient, amount in recipe.items():
            if self._inventory.get(ingredient, 0) < amount:
                return False
        return True

    def use_recipe(self, recipe: dict):
        """Deduct all ingredients in a recipe."""
        for ingredient, amount in recipe.items():
            self.use_ingredient(ingredient, amount)

    def __str__(self):
        return "\n".join([f"  {ing.value}: {qty}" for ing, qty in self._inventory.items()])


# ============ MACHINE STATES (State Pattern) ============

class MachineState(ABC):
    @abstractmethod
    def select_coffee(self, machine: 'CoffeeVendingMachine', coffee: Coffee):
        pass

    @abstractmethod
    def insert_coin(self, machine: 'CoffeeVendingMachine', coin: Coin):
        pass

    @abstractmethod
    def dispense(self, machine: 'CoffeeVendingMachine'):
        pass

    @abstractmethod
    def cancel(self, machine: 'CoffeeVendingMachine'):
        pass


class IdleState(MachineState):
    def select_coffee(self, machine: 'CoffeeVendingMachine', coffee: Coffee):
        # Check if ingredients are available
        if not machine.inventory.has_enough_for(coffee.get_recipe()):
            print(f"❌ Sorry, {coffee.get_description()} is currently unavailable.")
            return

        machine.selected_coffee = coffee
        machine.set_state(AwaitingPaymentState())
        print(f"Selected: {coffee.get_description()} - ₹{coffee.get_cost()}")
        print("Please insert coins...")

    def insert_coin(self, machine: 'CoffeeVendingMachine', coin: Coin):
        print("❌ Please select a coffee first.")

    def dispense(self, machine: 'CoffeeVendingMachine'):
        print("❌ Please select a coffee first.")

    def cancel(self, machine: 'CoffeeVendingMachine'):
        print("❌ Nothing to cancel.")


class AwaitingPaymentState(MachineState):
    def select_coffee(self, machine: 'CoffeeVendingMachine', coffee: Coffee):
        print("❌ Coffee already selected. Please pay or cancel.")

    def insert_coin(self, machine: 'CoffeeVendingMachine', coin: Coin):
        machine.inserted_amount += coin.value
        remaining = machine.selected_coffee.get_cost() - machine.inserted_amount

        if remaining <= 0:
            print(f"✅ Payment complete! Inserted: ₹{machine.inserted_amount}")
            machine.set_state(DispensingState())
            machine.dispense()  # Auto-dispense when payment complete
        else:
            print(f"Inserted: ₹{coin.value}. Total: ₹{machine.inserted_amount}. Remaining: ₹{remaining}")

    def dispense(self, machine: 'CoffeeVendingMachine'):
        print(f"❌ Please complete payment. Remaining: ₹{machine.selected_coffee.get_cost() - machine.inserted_amount}")

    def cancel(self, machine: 'CoffeeVendingMachine'):
        if machine.inserted_amount > 0:
            print(f"Refunding ₹{machine.inserted_amount}...")
        print("Order cancelled.")
        machine.reset()
        machine.set_state(IdleState())


class DispensingState(MachineState):
    def select_coffee(self, machine: 'CoffeeVendingMachine', coffee: Coffee):
        print("❌ Please wait, dispensing coffee...")

    def insert_coin(self, machine: 'CoffeeVendingMachine', coin: Coin):
        print("❌ Please wait, dispensing coffee...")

    def dispense(self, machine: 'CoffeeVendingMachine'):
        coffee = machine.selected_coffee
        print(f"\n☕ Making {coffee.get_description()}...")
        
        # Deduct ingredients
        machine.inventory.use_recipe(coffee.get_recipe())
        
        print("✅ Coffee dispensed! Enjoy!")
        print(f"   Paid: ₹{machine.inserted_amount}")
        
        # Reset for next customer
        machine.reset()
        machine.set_state(IdleState())

    def cancel(self, machine: 'CoffeeVendingMachine'):
        print("❌ Cannot cancel, already dispensing.")


# ============ COFFEE VENDING MACHINE (Singleton) ============

class CoffeeVendingMachine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CoffeeVendingMachine, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.inventory = IngredientInventory()
        self.current_state: MachineState = IdleState()
        self.selected_coffee: Coffee = None
        self.inserted_amount: int = 0

        # Available coffee menu
        self.menu = {
            "espresso": Espresso(),
            "latte": Latte(),
            "cappuccino": Cappuccino()
        }

    def set_state(self, state: MachineState):
        self.current_state = state

    def reset(self):
        self.selected_coffee = None
        self.inserted_amount = 0

    # ---- Public API (Delegates to current state) ----

    def select_coffee(self, coffee: Coffee):
        self.current_state.select_coffee(self, coffee)

    def insert_coin(self, coin: Coin):
        self.current_state.insert_coin(self, coin)

    def dispense(self):
        self.current_state.dispense(self)

    def cancel(self):
        self.current_state.cancel(self)

    def show_menu(self):
        print("\n--- MENU ---")
        for name, coffee in self.menu.items():
            available = "✅" if self.inventory.has_enough_for(coffee.get_recipe()) else "❌"
            print(f"  {available} {coffee.get_description()}: ₹{coffee.get_cost()}")
        print("  Extras: +Sugar (₹5), +Milk (₹10)")

    def show_inventory(self):
        print("\n--- INVENTORY ---")
        print(self.inventory)


# ============ DEMO ============

if __name__ == "__main__":
    print("=" * 60)
    print("COFFEE VENDING MACHINE - DEMO")
    print("=" * 60)

    # Get the singleton instance
    machine = CoffeeVendingMachine()

    # Show menu
    machine.show_menu()

    # 1. Try to insert coin without selecting coffee
    print("\n--- 1. Insert coin without selection ---")
    machine.insert_coin(Coin.TEN)

    # 2. Select a simple Espresso
    print("\n--- 2. Select Espresso (₹30) ---")
    machine.select_coffee(Espresso())

    # 3. Insert coins
    print("\n--- 3. Insert coins ---")
    machine.insert_coin(Coin.TEN)
    machine.insert_coin(Coin.TEN)
    machine.insert_coin(Coin.TEN)  # This completes payment and auto-dispenses

    # 4. Show inventory after dispensing
    machine.show_inventory()

    # 5. Order Latte with extra sugar and milk (Decorator Pattern!)
    print("\n--- 5. Order Latte + Extra Sugar + Extra Milk ---")
    custom_latte = Latte()
    custom_latte = SugarDecorator(custom_latte)
    custom_latte = MilkDecorator(custom_latte)
    print(f"Custom order: {custom_latte.get_description()} - ₹{custom_latte.get_cost()}")

    machine.select_coffee(custom_latte)

    # 6. Try to select another coffee while one is selected
    print("\n--- 6. Try selecting another coffee ---")
    machine.select_coffee(Espresso())

    # 7. Cancel the order
    print("\n--- 7. Cancel order ---")
    machine.cancel()

    # 8. New order - complete it
    print("\n--- 8. New order: Cappuccino ---")
    machine.select_coffee(Cappuccino())
    machine.insert_coin(Coin.TEN)
    machine.insert_coin(Coin.TEN)
    machine.insert_coin(Coin.TEN)
    machine.insert_coin(Coin.TEN)
    machine.insert_coin(Coin.TEN)

    # 9. Final inventory
    print("\n--- 9. Final Inventory ---")
    machine.show_inventory()

    print("\n" + "=" * 60)
    print("DEMO COMPLETED!")
    print("=" * 60)
