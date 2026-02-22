from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime
import uuid

# ============ ENUMS ============
class TransactionStatus(Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class TransactionType(Enum):
    WITHDRAW = "WITHDRAW"
    BALANCE_INQUIRY = "BALANCE_INQUIRY"
    DEPOSIT = "DEPOSIT"

# ============ NOTE DISPENSER (Chain of Responsibility) ============
# Each dispenser owns its own count - SIMPLIFIED DESIGN
class NoteDispenser(ABC):
    def __init__(self, count: int):
        self.count = count
        self.next_dispenser = None

    def set_next(self, next_dispenser):
        self.next_dispenser = next_dispenser
        return next_dispenser

    @abstractmethod
    def get_denomination(self) -> int:
        pass

    def dispense(self, amount: int) -> int:
        """Dispense as many notes as possible, return remaining amount."""
        denomination = self.get_denomination()
        notes_needed = amount // denomination
        notes_to_give = min(notes_needed, self.count)

        if notes_to_give > 0:
            self.count -= notes_to_give
            amount -= (notes_to_give * denomination)
            print(f"Dispensing {notes_to_give} x ${denomination} notes")

        if amount > 0 and self.next_dispenser:
            return self.next_dispenser.dispense(amount)
        
        return amount

    def can_dispense(self, amount: int) -> bool:
        notes_needed = amount // self.get_denomination()
        notes_can_give = min(notes_needed, self.count)
        remaining = amount - (notes_can_give * self.get_denomination())
        if remaining == 0:
            return True
        if self.next_dispenser:
            return self.next_dispenser.can_dispense(remaining)
        return False

    def get_total_cash(self) -> int:
        """Get total cash from this dispenser and all subsequent ones."""
        my_cash = self.count * self.get_denomination()
        if self.next_dispenser:
            return my_cash + self.next_dispenser.get_total_cash()
        return my_cash

    def add_notes(self, count: int):
        """Refill this dispenser with more notes."""
        if count < 0:
            raise ValueError("Cannot add negative notes")
        self.count += count


class Note100Dispenser(NoteDispenser):
    def get_denomination(self) -> int:
        return 100


class Note50Dispenser(NoteDispenser):
    def get_denomination(self) -> int:
        return 50


class Note20Dispenser(NoteDispenser):
    def get_denomination(self) -> int:
        return 20


class Note10Dispenser(NoteDispenser):
    def get_denomination(self) -> int:
        return 10


# ============ CARD ============
class Card:
    def __init__(self, card_number: str, pin: int, account: 'Account'):
        self.card_number = card_number
        self.pin = pin
        self.account = account  # Link to the associated account

    def verify_pin(self, entered_pin: int) -> bool:
        return self.pin == entered_pin

    def get_account(self) -> 'Account':
        return self.account


# ============ ACCOUNT ============
class Account:
    def __init__(self, account_number: str, balance: float):
        self.account_number = account_number
        self.balance = balance

    def get_balance(self) -> float:
        return self.balance

    def debit(self, amount: float) -> bool:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if self.balance >= amount:
            self.balance -= amount
            return True
        return False

    def credit(self, amount: float):
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self.balance += amount


# ============ TRANSACTION (Audit Trail) ============
class Transaction:
    def __init__(self, account: Account, transaction_type: TransactionType, amount: float):
        self.transaction_id = str(uuid.uuid4())
        self.account = account
        self.transaction_type = transaction_type
        self.amount = amount
        self.status = TransactionStatus.PENDING
        self.timestamp = datetime.now()

    def mark_success(self):
        self.status = TransactionStatus.SUCCESS

    def mark_failed(self):
        self.status = TransactionStatus.FAILED

    def __str__(self):
        return f"Transaction[{self.transaction_id[:8]}] {self.transaction_type.value} ${self.amount} - {self.status.value}"


# ============ BANK SERVICE (Abstract - Dependency Inversion) ============
class BankService(ABC):
    @abstractmethod
    def authenticate(self, card: Card, pin: int) -> bool:
        """Verify the card's PIN."""
        pass

    @abstractmethod
    def get_balance(self, account: Account) -> float:
        """Get account balance."""
        pass

    @abstractmethod
    def debit(self, account: Account, amount: float) -> bool:
        """Deduct amount from account. Returns True if successful."""
        pass


class LocalBankService(BankService):
    """Simple implementation for demo - in reality, this would call a remote API."""
    
    def authenticate(self, card: Card, pin: int) -> bool:
        return card.verify_pin(pin)

    def get_balance(self, account: Account) -> float:
        return account.get_balance()

    def debit(self, account: Account, amount: float) -> bool:
        return account.debit(amount)


# ============ ATM STATES (State Pattern) ============
class ATMState(ABC):
    @abstractmethod
    def insert_card(self, atm: 'ATM', card: Card):
        pass

    @abstractmethod
    def eject_card(self, atm: 'ATM'):
        pass

    @abstractmethod
    def enter_pin(self, atm: 'ATM', pin: int):
        pass

    @abstractmethod
    def withdraw(self, atm: 'ATM', amount: int):
        pass

    @abstractmethod
    def check_balance(self, atm: 'ATM'):
        pass


class IdleState(ATMState):
    def insert_card(self, atm: 'ATM', card: Card):
        print("Card Inserted")
        atm.currentCard = card
        atm.currentAccount = card.get_account()
        atm.set_state(HasCardState())

    def eject_card(self, atm: 'ATM'):
        print("No card to eject")

    def enter_pin(self, atm: 'ATM', pin: int):
        print("Please insert card first")

    def withdraw(self, atm: 'ATM', amount: int):
        print("Please insert card first")

    def check_balance(self, atm: 'ATM'):
        print("Please insert card first")


class HasCardState(ATMState):
    def __init__(self):
        self.pin_attempts = 0
        self.max_attempts = 3

    def insert_card(self, atm: 'ATM', card: Card):
        print("Card already inserted")

    def eject_card(self, atm: 'ATM'):
        print("Card ejected")
        atm.currentCard = None
        atm.currentAccount = None
        atm.set_state(IdleState())

    def enter_pin(self, atm: 'ATM', pin: int):
        if atm.bank_service.authenticate(atm.currentCard, pin):
            print("PIN verified. You are now authenticated.")
            atm.set_state(AuthenticatedState())
        else:
            self.pin_attempts += 1
            remaining = self.max_attempts - self.pin_attempts
            if remaining > 0:
                print(f"Invalid PIN. {remaining} attempts remaining.")
            else:
                print("Too many failed attempts. Card ejected.")
                self.eject_card(atm)

    def withdraw(self, atm: 'ATM', amount: int):
        print("Please enter your PIN first")

    def check_balance(self, atm: 'ATM'):
        print("Please enter your PIN first")


class AuthenticatedState(ATMState):
    def insert_card(self, atm: 'ATM', card: Card):
        print("Card already inserted")

    def eject_card(self, atm: 'ATM'):
        print("Card ejected. Thank you for using the ATM.")
        atm.currentCard = None
        atm.currentAccount = None
        atm.currentTransaction = None
        atm.set_state(IdleState())

    def enter_pin(self, atm: 'ATM', pin: int):
        print("Already authenticated")

    def withdraw(self, atm: 'ATM', amount: int):
        # Create transaction for audit trail
        transaction = Transaction(atm.currentAccount, TransactionType.WITHDRAW, amount)
        atm.currentTransaction = transaction
        print(f"Processing withdrawal of ${amount}...")

        # Step 1: Check if ATM has enough cash
        if not atm.can_dispense(amount):
            print("ATM does not have enough cash for this amount")
            transaction.mark_failed()
            return

        # Step 2: Check if account has enough balance
        if atm.currentAccount.get_balance() < amount:
            print("Insufficient funds in your account")
            transaction.mark_failed()
            return

        # Step 3: Debit the account (via BankService)
        if not atm.bank_service.debit(atm.currentAccount, amount):
            print("Transaction failed at bank")
            transaction.mark_failed()
            return

        # Step 4: Dispense cash
        remaining = atm.dispense(amount)
        if remaining == 0:
            transaction.mark_success()
            print(f"Withdrawal successful! New balance: ${atm.currentAccount.get_balance()}")
        else:
            # Cash dispense failed - ideally refund the account
            print("Cash dispense error. Please contact support.")
            transaction.mark_failed()

    def check_balance(self, atm: 'ATM'):
        balance = atm.bank_service.get_balance(atm.currentAccount)
        print(f"Your current balance is: ${balance}")
        # Create transaction for audit trail
        transaction = Transaction(atm.currentAccount, TransactionType.BALANCE_INQUIRY, 0)
        transaction.mark_success()


# ============ ATM (Singleton) ============
class ATM:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ATM, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # Prevent re-initialization on subsequent calls
        if self._initialized:
            return
        self._initialized = True

        # Setup dispenser chain: $100 -> $50 -> $20 -> $10
        d100 = Note100Dispenser(10)
        d50 = Note50Dispenser(10)
        d20 = Note20Dispenser(10)
        d10 = Note10Dispenser(10)
        d100.set_next(d50)
        d50.set_next(d20)
        d20.set_next(d10)
        self.note_dispenser_chain = d100

        # State and session
        self.currentState: ATMState = IdleState()
        self.currentCard: Card = None
        self.currentAccount: Account = None
        self.currentTransaction: Transaction = None

        # Bank service (Dependency Injection)
        self.bank_service: BankService = LocalBankService()

    def set_state(self, state: ATMState):
        self.currentState = state

    def can_dispense(self, amount: int) -> bool:
        return self.note_dispenser_chain.can_dispense(amount)

    def dispense(self, amount: int) -> int:
        """Returns 0 if fully dispensed, else remaining amount."""
        return self.note_dispenser_chain.dispense(amount)

    def get_total_cash(self) -> int:
        return self.note_dispenser_chain.get_total_cash()

    # ---- Public API (Delegates to current state) ----
    def insert_card(self, card: Card):
        self.currentState.insert_card(self, card)

    def eject_card(self):
        self.currentState.eject_card(self)

    def enter_pin(self, pin: int):
        self.currentState.enter_pin(self, pin)

    def withdraw(self, amount: int):
        self.currentState.withdraw(self, amount)

    def check_balance(self):
        self.currentState.check_balance(self)


# ============ DEMO ============
if __name__ == "__main__":
    # Create an account and card
    account = Account("ACC-123456", 1000.0)
    card = Card("1234-5678-9012-3456", 1234, account)

    # Get the ATM (Singleton)
    atm = ATM()
    print(f"ATM Total Cash: ${atm.get_total_cash()}")
    print("=" * 50)

    # Simulate a withdrawal flow
    print("\n--- Inserting Card ---")
    atm.insert_card(card)

    print("\n--- Entering Wrong PIN ---")
    atm.enter_pin(9999)

    print("\n--- Entering Correct PIN ---")
    atm.enter_pin(1234)

    print("\n--- Checking Balance ---")
    atm.check_balance()

    print("\n--- Withdrawing $280 ---")
    atm.withdraw(280)

    print("\n--- Checking Balance Again ---")
    atm.check_balance()

    print("\n--- Ejecting Card ---")
    atm.eject_card()

    print("\n--- Trying to withdraw without card ---")
    atm.withdraw(100)

    print("=" * 50)
    print(f"ATM Total Cash Remaining: ${atm.get_total_cash()}")
