from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict
import uuid

# ============ SPLIT CLASS ============

class Split:
    """Represents one user's share in an expense."""
    def __init__(self, user: 'User', amount: float):
        self.user = user
        self.amount = amount
    
    def __str__(self):
        return f"Split({self.user.name}: ₹{self.amount:.2f})"


# ============ USER ============

class User:
    def __init__(self, name: str, email: str, phone: str = None):
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.email = email
        self.phone = phone
    
    def __str__(self):
        return f"User({self.name})"
    
    def __eq__(self, other):
        if isinstance(other, User):
            return self.id == other.id
        return False
    
    def __hash__(self):
        return hash(self.id)


# ============ EXPENSE ============

class Expense:
    def __init__(self, amount: float, payer: User, description: str, splits: List[Split]):
        self.id = str(uuid.uuid4())[:8]
        self.amount = amount
        self.payer = payer
        self.description = description
        self.splits = splits
        self.timestamp = datetime.now()
    
    def __str__(self):
        return f"Expense({self.description}: ₹{self.amount}, paid by {self.payer.name})"


# ============ SETTLEMENT ============

class Settlement:
    """Records a payment between two users to settle up."""
    def __init__(self, payer: User, payee: User, amount: float):
        self.id = str(uuid.uuid4())[:8]
        self.payer = payer
        self.payee = payee
        self.amount = amount
        self.timestamp = datetime.now()
    
    def __str__(self):
        return f"Settlement({self.payer.name} paid {self.payee.name} ₹{self.amount:.2f})"


# ============ SPLIT STRATEGIES ============

class SplitStrategy(ABC):
    @abstractmethod
    def calculate_splits(self, 
                         total_amount: float, 
                         payer: User,
                         participants: List[User], 
                         split_details: Dict = None) -> List[Split]:
        pass


class EqualSplitStrategy(SplitStrategy):
    """Split equally among all participants."""
    def calculate_splits(self, total_amount, payer, participants, split_details=None):
        per_person = total_amount / len(participants)
        return [Split(user, per_person) for user in participants]


class ExactSplitStrategy(SplitStrategy):
    """Each participant pays an exact specified amount."""
    def calculate_splits(self, total_amount, payer, participants, split_details):
        if not split_details:
            raise ValueError("Exact split requires split_details")
        
        splits = []
        total = 0
        for user in participants:
            amount = split_details.get(user.id, 0)
            total += amount
            splits.append(Split(user, amount))
        
        if abs(total - total_amount) > 0.01:
            raise ValueError(f"Split amounts ({total}) don't add up to total ({total_amount})!")
        return splits


class PercentSplitStrategy(SplitStrategy):
    """Each participant pays a percentage of the total."""
    def calculate_splits(self, total_amount, payer, participants, split_details):
        if not split_details:
            raise ValueError("Percent split requires split_details")
        
        splits = []
        total_percent = 0
        for user in participants:
            percent = split_details.get(user.id, 0)
            total_percent += percent
            amount = (percent / 100) * total_amount
            splits.append(Split(user, amount))
        
        if abs(total_percent - 100) > 0.01:
            raise ValueError(f"Percentages ({total_percent}) don't add up to 100!")
        return splits


# ============ OBSERVER INTERFACE ============

class Observer(ABC):
    """Observer interface for notifications."""
    @abstractmethod
    def update(self, user: User, message: str):
        pass


class EmailObserver(Observer):
    def update(self, user: User, message: str):
        print(f"📧 Email to {user.email}: {message}")


class SMSObserver(Observer):
    def update(self, user: User, message: str):
        if user.phone:
            print(f"📱 SMS to {user.phone}: {message}")


class PushObserver(Observer):
    def update(self, user: User, message: str):
        print(f"🔔 Push to {user.name}: {message}")


# ============ SUBJECT (Abstract Base for Observer Pattern) ============

class Subject(ABC):
    """
    Abstract Subject in Observer pattern.
    Any class that can notify observers extends this.
    """
    def __init__(self):
        self._observers: List[Observer] = []
    
    def add_observer(self, observer: Observer):
        """Subscribe an observer."""
        if observer not in self._observers:
            self._observers.append(observer)
    
    def remove_observer(self, observer: Observer):
        """Unsubscribe an observer."""
        if observer in self._observers:
            self._observers.remove(observer)
    
    def notify_observers(self, user: User, message: str):
        """Notify all observers."""
        for observer in self._observers:
            observer.update(user, message)


# ============ GROUP (Extends Subject) ============

class Group(Subject):
    """
    Group is a SUBJECT in Observer pattern.
    When expenses or settlements are added, it notifies all observers.
    """
    def __init__(self, name: str):
        super().__init__()  # Initialize observers from Subject
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.users: List[User] = []
        self.expenses: List[Expense] = []
        self.settlements: List[Settlement] = []
        self.balances: Dict[tuple, float] = {}
    
    # --- User Management ---
    def add_user(self, user: User):
        if user not in self.users:
            self.users.append(user)
            print(f"✅ Added {user.name} to group '{self.name}'")
    
    def remove_user(self, user: User):
        if user in self.users:
            self.users.remove(user)
    
    # --- Expense Management ---
    def add_expense(self, expense: Expense):
        """Add expense, update balances, and notify affected users."""
        self.expenses.append(expense)
        self._update_balances_for_expense(expense, add=True)
        print(f"✅ Added expense: {expense}")
        
        # Notify observers (Observer pattern)
        self._notify_expense_added(expense)
    
    def remove_expense(self, expense: Expense):
        if expense in self.expenses:
            self._update_balances_for_expense(expense, add=False)
            self.expenses.remove(expense)
            print(f"✅ Removed expense: {expense}")
    
    def _update_balances_for_expense(self, expense: Expense, add: bool):
        multiplier = 1 if add else -1
        for split in expense.splits:
            if split.user != expense.payer:
                key = (expense.payer.id, split.user.id)
                current = self.balances.get(key, 0)
                self.balances[key] = current + (split.amount * multiplier)
    
    def _notify_expense_added(self, expense: Expense):
        for split in expense.splits:
            if split.user != expense.payer and split.amount > 0:
                message = f"{expense.payer.name} added '{expense.description}'. You owe ₹{split.amount:.2f}"
                self.notify_observers(split.user, message)
    
    # --- Settlement Management ---
    def add_settlement(self, settlement: Settlement):
        self.settlements.append(settlement)
        key = (settlement.payee.id, settlement.payer.id)
        current = self.balances.get(key, 0)
        self.balances[key] = current - settlement.amount
        print(f"✅ Settlement recorded: {settlement}")
        
        # Notify observers (Observer pattern)
        self._notify_settlement(settlement)
    
    def _notify_settlement(self, settlement: Settlement):
        message = f"{settlement.payer.name} paid you ₹{settlement.amount:.2f}"
        self.notify_observers(settlement.payee, message)
    
    # --- Balance Queries ---
    def get_balance(self, user1: User, user2: User) -> float:
        key1 = (user1.id, user2.id)
        key2 = (user2.id, user1.id)
        return self.balances.get(key1, 0) - self.balances.get(key2, 0)
    
    def get_user_balances(self, user: User) -> Dict[User, float]:
        result = {}
        for other in self.users:
            if other != user:
                balance = self.get_balance(user, other)
                if abs(balance) > 0.01:
                    result[other] = balance
        return result
    
    def show_balances(self):
        print(f"\n--- Balances in '{self.name}' ---")
        shown = set()
        for user in self.users:
            for other, amount in self.get_user_balances(user).items():
                pair = tuple(sorted([user.id, other.id]))
                if pair not in shown and amount > 0:
                    print(f"  {other.name} owes {user.name}: ₹{amount:.2f}")
                    shown.add(pair)
        if not shown:
            print("  All settled up! 🎉")
    
    def __str__(self):
        return f"Group({self.name}, {len(self.users)} members)"


# ============ SPLITWISE SERVICE (Singleton Facade) ============
# NOTE: Facade has NO knowledge of observers — clean separation!

class SplitwiseService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SplitwiseService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.users: Dict[str, User] = {}
        self.groups: Dict[str, Group] = {}
        
        # Strategy map
        self.strategies = {
            "EQUAL": EqualSplitStrategy(),
            "EXACT": ExactSplitStrategy(),
            "PERCENT": PercentSplitStrategy()
        }
    
    # --- User Management ---
    def add_user(self, name: str, email: str, phone: str = None) -> User:
        user = User(name, email, phone)
        self.users[user.id] = user
        print(f"✅ Registered user: {user}")
        return user
    
    def get_user(self, user_id: str) -> User:
        return self.users.get(user_id)
    
    # --- Group Management ---
    def create_group(self, name: str, members: List[User]) -> Group:
        """Create a group. Observers should be added by caller."""
        group = Group(name)
        for member in members:
            group.add_user(member)
        self.groups[group.id] = group
        print(f"✅ Created group: {group}")
        return group
    
    def get_group(self, group_id: str) -> Group:
        return self.groups.get(group_id)
    
    # --- Expense Management ---
    def add_expense(self,
                    group: Group,
                    payer: User,
                    amount: float,
                    description: str,
                    split_type: str = "EQUAL",
                    participants: List[User] = None,
                    split_details: Dict[str, float] = None) -> Expense:
        
        if participants is None:
            participants = group.users
        
        strategy = self.strategies.get(split_type)
        if not strategy:
            raise ValueError(f"Unknown split type: {split_type}")
        
        splits = strategy.calculate_splits(amount, payer, participants, split_details)
        expense = Expense(amount, payer, description, splits)
        
        # Notifications happen automatically via Observer pattern in Group!
        group.add_expense(expense)
        return expense
    
    # --- Settlement ---
    def settle_up(self, group: Group, payer: User, payee: User, amount: float) -> Settlement:
        settlement = Settlement(payer, payee, amount)
        # Notifications happen automatically via Observer pattern in Group!
        group.add_settlement(settlement)
        return settlement
    
    # --- Balance Queries ---
    def show_group_balances(self, group: Group):
        group.show_balances()
    
    def show_user_balances(self, user: User, group: Group):
        print(f"\n--- {user.name}'s balances in '{group.name}' ---")
        balances = group.get_user_balances(user)
        if not balances:
            print("  All settled up! 🎉")
        for other, amount in balances.items():
            if amount > 0:
                print(f"  {other.name} owes you: ₹{amount:.2f}")
            else:
                print(f"  You owe {other.name}: ₹{abs(amount):.2f}")


# ============ DEMO ============

if __name__ == "__main__":
    print("=" * 60)
    print("SPLITWISE - DEMO")
    print("Observer Pattern: Group extends Subject")
    print("Facade: SplitwiseService has NO observer knowledge")
    print("=" * 60)
    
    # Get service instance (Facade)
    service = SplitwiseService()
    
    # 1. Create users
    print("\n--- 1. Register Users ---")
    alice = service.add_user("Alice", "alice@email.com", "9876543210")
    bob = service.add_user("Bob", "bob@email.com", "9876543211")
    charlie = service.add_user("Charlie", "charlie@email.com", "9876543212")
    
    # 2. Create a group (NO observers yet - facade doesn't handle that)
    print("\n--- 2. Create Group ---")
    trip = service.create_group("Goa Trip", [alice, bob, charlie])
    
    # 3. Add observers to group (OUTSIDE of facade - clean separation!)
    print("\n--- 3. Subscribe Observers to Group (Outside Facade) ---")
    trip.add_observer(EmailObserver())
    trip.add_observer(PushObserver())
    trip.add_observer(SMSObserver())
    print("✅ Subscribed: Email, Push, SMS observers")
    
    # 4. Add expenses (notifications happen automatically!)
    print("\n--- 4. Add Equal Split Expense ---")
    service.add_expense(
        group=trip,
        payer=alice,
        amount=300,
        description="Dinner",
        split_type="EQUAL"
    )
    
    print("\n--- 5. Add Exact Split Expense ---")
    service.add_expense(
        group=trip,
        payer=bob,
        amount=200,
        description="Hotel",
        split_type="EXACT",
        split_details={alice.id: 80, bob.id: 60, charlie.id: 60}
    )
    
    print("\n--- 6. Add Percent Split Expense ---")
    service.add_expense(
        group=trip,
        payer=charlie,
        amount=150,
        description="Transport",
        split_type="PERCENT",
        split_details={alice.id: 50, bob.id: 30, charlie.id: 20}
    )
    
    # 5. Show balances
    print("\n--- 7. Group Balances ---")
    service.show_group_balances(trip)
    
    # 6. Settlement (notifications happen automatically!)
    print("\n--- 8. Settlement ---")
    service.settle_up(trip, bob, alice, 20)
    
    # 7. Final balances
    print("\n--- 9. Final Balances ---")
    service.show_group_balances(trip)
    
    print("\n" + "=" * 60)
    print("DESIGN HIGHLIGHTS:")
    print("  ✅ Subject (abstract) → Group extends it")
    print("  ✅ Observer (interface) → Email, SMS, Push implement it")
    print("  ✅ Facade (SplitwiseService) has NO observer logic")
    print("  ✅ Observers subscribed outside facade (clean separation)")
    print("=" * 60)
