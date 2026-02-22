from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime
import math


# ═══════════════════════════════════════════════════════════════
#                        ENUMS
# ═══════════════════════════════════════════════════════════════

class OrderStatus(Enum):
    PLACED = 1
    CONFIRMED = 2
    PREPARING = 3
    OUT_FOR_DELIVERY = 4
    DELIVERED = 5
    CANCELLED = 6

class AgentStatus(Enum):
    AVAILABLE = 1
    ON_DELIVERY = 2
    OFFLINE = 3


# ═══════════════════════════════════════════════════════════════
#                     LOCATION
# ═══════════════════════════════════════════════════════════════

class Location:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def distance_to(self, other: 'Location') -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def __str__(self):
        return f"({self.x}, {self.y})"


# ═══════════════════════════════════════════════════════════════
#                     STRATEGIES
# ═══════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════
#                     CORE ENTITIES
# ═══════════════════════════════════════════════════════════════

class MenuItem:
    def __init__(self, item_id: int, name: str, price: float, is_available: bool = True):
        self.item_id = item_id
        self.name = name
        self.price = price
        self.is_available = is_available

    def __str__(self):
        status = "✅" if self.is_available else "❌"
        return f"{status} {self.name} — ₹{self.price:.0f}"


class Restaurant:
    def __init__(self, restaurant_id: int, name: str, cuisine: str, location: Location):
        self.restaurant_id = restaurant_id
        self.name = name
        self.cuisine = cuisine
        self.location = location
        self.menu: list[MenuItem] = []
        self.rating = 5.0
        self.total_ratings = 0
        self.order_history: list['Order'] = []

    def add_menu_item(self, item: MenuItem):
        self.menu.append(item)

    def get_menu_item(self, item_id: int) -> MenuItem | None:
        for item in self.menu:
            if item.item_id == item_id and item.is_available:
                return item
        return None

    def add_rating(self, rating: float):
        self.rating = ((self.rating * self.total_ratings) + rating) / (self.total_ratings + 1)
        self.total_ratings += 1

    def __str__(self):
        return f"🍽️ {self.name} ({self.cuisine}) | Rating: {self.rating:.1f}⭐ | {self.location}"


class Customer:
    def __init__(self, customer_id: int, name: str, location: Location):
        self.customer_id = customer_id
        self.name = name
        self.location = location
        self.order_history: list['Order'] = []

    def __str__(self):
        return f"👤 {self.name} | Orders: {len(self.order_history)}"


class DeliveryAgent:
    def __init__(self, agent_id: int, name: str, location: Location):
        self.agent_id = agent_id
        self.name = name
        self.location = location
        self.status = AgentStatus.AVAILABLE
        self.rating = 5.0
        self.total_ratings = 0
        self.delivery_history: list['Order'] = []

    def add_rating(self, rating: float):
        self.rating = ((self.rating * self.total_ratings) + rating) / (self.total_ratings + 1)
        self.total_ratings += 1

    def __str__(self):
        return f"🏍️ {self.name} ({self.status.name}) | Rating: {self.rating:.1f}⭐"


class OrderItem:
    """Links MenuItem to quantity. Like BookCopy for Books."""
    def __init__(self, menu_item: MenuItem, quantity: int):
        self.menu_item = menu_item
        self.quantity = quantity
        self.subtotal = menu_item.price * quantity

    def __str__(self):
        return f"  • {self.menu_item.name} × {self.quantity} = ₹{self.subtotal:.0f}"


class Order:
    _counter = 0
    DELIVERY_FEE_PER_KM = 5

    def __init__(self, customer: Customer, restaurant: Restaurant, items: list[OrderItem]):
        Order._counter += 1
        self.order_id = Order._counter
        self.customer = customer
        self.restaurant = restaurant
        self.agent: DeliveryAgent | None = None
        self.items = items
        self.status = OrderStatus.PLACED
        self.item_total = sum(i.subtotal for i in items)
        distance = restaurant.location.distance_to(customer.location)
        self.delivery_fee = round(distance * self.DELIVERY_FEE_PER_KM, 0)
        self.total_amount = self.item_total + self.delivery_fee
        self.placed_at = datetime.now()
        self.delivered_at: datetime | None = None

    def __str__(self):
        agent_name = self.agent.name if self.agent else "Unassigned"
        return (f"📦 Order#{self.order_id}: {self.customer.name} ← {self.restaurant.name} "
                f"| Agent: {agent_name} | {self.status.name} | ₹{self.total_amount:.0f}")


# ═══════════════════════════════════════════════════════════════
#                     SEARCH STRATEGIES
# ═══════════════════════════════════════════════════════════════

class SearchStrategy(ABC):
    @abstractmethod
    def search(self, query: str, restaurants: list[Restaurant]) -> list[Restaurant]:
        pass

class SearchByName(SearchStrategy):
    def search(self, query: str, restaurants: list[Restaurant]) -> list[Restaurant]:
        return [r for r in restaurants if query.lower() in r.name.lower()]

class SearchByCuisine(SearchStrategy):
    def search(self, query: str, restaurants: list[Restaurant]) -> list[Restaurant]:
        return [r for r in restaurants if query.lower() in r.cuisine.lower()]


# ═══════════════════════════════════════════════════════════════
#           FOOD DELIVERY SYSTEM (SINGLETON)
# ═══════════════════════════════════════════════════════════════

class FoodDeliverySystem:
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
        self.customers: dict[int, Customer] = {}
        self.restaurants: dict[int, Restaurant] = {}
        self.agents: dict[int, DeliveryAgent] = {}
        self.orders: dict[int, Order] = {}

    # ─── Registration ───
    def register_customer(self, cid: int, name: str, location: Location) -> Customer:
        customer = Customer(cid, name, location)
        self.customers[cid] = customer
        return customer

    def register_restaurant(self, rid: int, name: str, cuisine: str, location: Location) -> Restaurant:
        restaurant = Restaurant(rid, name, cuisine, location)
        self.restaurants[rid] = restaurant
        return restaurant

    def register_agent(self, aid: int, name: str, location: Location) -> DeliveryAgent:
        agent = DeliveryAgent(aid, name, location)
        self.agents[aid] = agent
        return agent

    # ─── Search ───
    def search_restaurants(self, query: str, strategy: SearchStrategy) -> list[Restaurant]:
        return strategy.search(query, list(self.restaurants.values()))

    # ─── Place Order ───
    def place_order(self, customer_id: int, restaurant_id: int,
                    item_quantities: dict[int, int]) -> Order | None:
        """item_quantities = {menu_item_id: quantity}"""
        customer = self.customers.get(customer_id)
        restaurant = self.restaurants.get(restaurant_id)

        if not customer or not restaurant:
            print("   ❌ Customer or Restaurant not found!")
            return None

        # Build order items
        order_items = []
        for item_id, qty in item_quantities.items():
            menu_item = restaurant.get_menu_item(item_id)
            if not menu_item:
                print(f"   ❌ Menu item #{item_id} not found or unavailable!")
                return None
            order_items.append(OrderItem(menu_item, qty))

        order = Order(customer, restaurant, order_items)
        self.orders[order.order_id] = order
        customer.order_history.append(order)
        restaurant.order_history.append(order)

        print(f"   📝 Order#{order.order_id} placed by {customer.name} from {restaurant.name}")
        for item in order_items:
            print(f"   {item}")
        print(f"      Subtotal: ₹{order.item_total:.0f} + Delivery: ₹{order.delivery_fee:.0f} = ₹{order.total_amount:.0f}")
        return order

    def _validate_transition(self, order: Order, expected: OrderStatus, action: str) -> bool:
        if not order:
            print(f"   ❌ Order not found!")
            return False
        if order.status != expected:
            print(f"   ❌ Order is {order.status.name}, cannot {action}!")
            return False
        return True

    # ─── Confirm Order (Restaurant) ───
    def confirm_order(self, order_id: int) -> bool:
        order = self.orders.get(order_id)
        if not self._validate_transition(order, OrderStatus.PLACED, "confirm"):
            return False
        order.status = OrderStatus.CONFIRMED
        print(f"   ✅ {order.restaurant.name} confirmed Order#{order_id}")
        return True

    # ─── Prepare Order (Restaurant) ───
    def prepare_order(self, order_id: int) -> bool:
        order = self.orders.get(order_id)
        if not self._validate_transition(order, OrderStatus.CONFIRMED, "prepare"):
            return False
        order.status = OrderStatus.PREPARING
        print(f"   👨‍🍳 {order.restaurant.name} is preparing Order#{order_id}")
        return True

    # ─── Assign Delivery Agent ───
    def assign_agent(self, order_id: int) -> bool:
        order = self.orders.get(order_id)
        if not self._validate_transition(order, OrderStatus.PREPARING, "assign agent"):
            return False

        # Find nearest available agent to restaurant
        available = [a for a in self.agents.values() if a.status == AgentStatus.AVAILABLE]
        if not available:
            print(f"   ❌ No delivery agents available!")
            return False

        available.sort(key=lambda a: a.location.distance_to(order.restaurant.location))
        agent = available[0]

        order.agent = agent
        order.status = OrderStatus.OUT_FOR_DELIVERY
        agent.status = AgentStatus.ON_DELIVERY
        agent.delivery_history.append(order)
        dist = agent.location.distance_to(order.restaurant.location)
        print(f"   🏍️ {agent.name} assigned to Order#{order_id} ({dist:.1f} km from restaurant)")
        return True

    # ─── Deliver Order ───
    def deliver_order(self, order_id: int, payment: PaymentStrategy) -> bool:
        order = self.orders.get(order_id)
        if not self._validate_transition(order, OrderStatus.OUT_FOR_DELIVERY, "deliver"):
            return False

        order.status = OrderStatus.DELIVERED
        order.delivered_at = datetime.now()
        order.agent.status = AgentStatus.AVAILABLE
        order.agent.location = order.customer.location  # Agent is now at customer's location

        print(f"   🎉 Order#{order_id} delivered to {order.customer.name}!")
        payment.pay(order.total_amount)
        return True

    # ─── Cancel Order ───
    def cancel_order(self, order_id: int) -> bool:
        order = self.orders.get(order_id)
        if not order:
            print("   ❌ Order not found!")
            return False
        if order.status in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
            print(f"   ❌ Order is already {order.status.name}!")
            return False
        if order.status == OrderStatus.OUT_FOR_DELIVERY:
            print(f"   ❌ Cannot cancel — order is already out for delivery!")
            return False

        if order.agent and order.agent.status == AgentStatus.ON_DELIVERY:
            order.agent.status = AgentStatus.AVAILABLE
        order.status = OrderStatus.CANCELLED
        print(f"   🚫 Order#{order_id} cancelled!")
        return True

    # ─── Rating ───
    def rate_restaurant(self, order_id: int, rating: float):
        order = self.orders.get(order_id)
        if not order or order.status != OrderStatus.DELIVERED:
            print("   ❌ Can only rate delivered orders!")
            return
        order.restaurant.add_rating(rating)
        print(f"   ⭐ {order.customer.name} rated {order.restaurant.name}: {rating}/5")

    def rate_agent(self, order_id: int, rating: float):
        order = self.orders.get(order_id)
        if not order or order.status != OrderStatus.DELIVERED:
            print("   ❌ Can only rate delivered orders!")
            return
        order.agent.add_rating(rating)
        print(f"   ⭐ {order.customer.name} rated {order.agent.name}: {rating}/5")


# ═══════════════════════════════════════════════════════════════
#                        DEMO
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 65)
    print("       FOOD DELIVERY SYSTEM (SWIGGY) - LLD DEMO")
    print("=" * 65)

    system = FoodDeliverySystem()

    # ─── Register Restaurants ───
    print("\n🍽️ Registering Restaurants:")
    r1 = system.register_restaurant(1, "Biryani House", "Indian", Location(10, 10))
    r1.add_menu_item(MenuItem(1, "Chicken Biryani", 299))
    r1.add_menu_item(MenuItem(2, "Mutton Biryani", 399))
    r1.add_menu_item(MenuItem(3, "Raita", 49))
    r1.add_menu_item(MenuItem(4, "Gulab Jamun", 79))

    r2 = system.register_restaurant(2, "Pizza Planet", "Italian", Location(20, 20))
    r2.add_menu_item(MenuItem(1, "Margherita Pizza", 249))
    r2.add_menu_item(MenuItem(2, "Pepperoni Pizza", 349))
    r2.add_menu_item(MenuItem(3, "Garlic Bread", 129))

    for r in [r1, r2]:
        print(f"   {r}")
        for item in r.menu:
            print(f"      {item}")

    # ─── Register Customers ───
    print("\n👥 Registering Customers:")
    c1 = system.register_customer(1, "Nikhil", Location(15, 15))
    c2 = system.register_customer(2, "Priya", Location(25, 25))
    for c in [c1, c2]:
        print(f"   {c}")

    # ─── Register Delivery Agents ───
    print("\n🏍️ Registering Delivery Agents:")
    a1 = system.register_agent(1, "Raju", Location(11, 11))
    a2 = system.register_agent(2, "Kumar", Location(18, 18))
    for a in [a1, a2]:
        print(f"   {a}")

    # ═══════════════════════════════════════════════════════════
    #  TEST 1: Search Restaurants
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 65)
    print("  TEST 1: Search Restaurants")
    print("─" * 65)

    print("\n🔍 Search by name 'biryani':")
    results = system.search_restaurants("biryani", SearchByName())
    for r in results:
        print(f"   {r}")

    print("\n🔍 Search by cuisine 'italian':")
    results = system.search_restaurants("italian", SearchByCuisine())
    for r in results:
        print(f"   {r}")

    # ═══════════════════════════════════════════════════════════
    #  TEST 2: Complete Order Flow
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 65)
    print("  TEST 2: Complete Order Flow (Biryani House)")
    print("─" * 65)

    print("\n① Nikhil places order:")
    order1 = system.place_order(1, 1, {1: 2, 3: 1, 4: 2})  # 2 Chicken Biryani + 1 Raita + 2 Gulab Jamun

    print("\n② Restaurant confirms:")
    system.confirm_order(order1.order_id)

    print("\n③ Restaurant starts preparing:")
    system.prepare_order(order1.order_id)

    print("\n④ Delivery agent assigned:")
    system.assign_agent(order1.order_id)

    print("\n⑤ Order delivered:")
    system.deliver_order(order1.order_id, UPIPayment())

    print("\n⑥ Ratings:")
    system.rate_restaurant(order1.order_id, 4.5)
    system.rate_agent(order1.order_id, 5.0)

    # ═══════════════════════════════════════════════════════════
    #  TEST 3: Order Cancellation
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 65)
    print("  TEST 3: Order Cancellation")
    print("─" * 65)

    print("\n① Priya places order from Pizza Planet:")
    order2 = system.place_order(2, 2, {1: 1, 3: 1})  # Margherita + Garlic Bread

    print("\n② Restaurant confirms:")
    system.confirm_order(order2.order_id)

    print("\n③ Priya cancels before preparation:")
    system.cancel_order(order2.order_id)

    # ═══════════════════════════════════════════════════════════
    #  TEST 4: State Validation
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 65)
    print("  TEST 4: State Validation")
    print("─" * 65)

    print("\n① Try to deliver a cancelled order:")
    system.deliver_order(order2.order_id, CashPayment())

    print("\n② Try to cancel a delivered order:")
    system.cancel_order(order1.order_id)

    # ═══════════════════════════════════════════════════════════
    #  TEST 5: Multiple Orders + Agent Reuse
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 65)
    print("  TEST 5: Agent Reuse After Delivery")
    print("─" * 65)

    print("\n① Priya orders again from Pizza Planet:")
    order3 = system.place_order(2, 2, {2: 1})  # Pepperoni Pizza

    system.confirm_order(order3.order_id)
    system.prepare_order(order3.order_id)

    print("\n② Assigning agent (Raju now at Nikhil's location from last delivery):")
    system.assign_agent(order3.order_id)

    system.deliver_order(order3.order_id, CardPayment())

    # ═══════════════════════════════════════════════════════════
    #  FINAL STATE
    # ═══════════════════════════════════════════════════════════
    print("\n" + "─" * 65)
    print("  FINAL STATE")
    print("─" * 65)

    print("\n📊 Restaurants:")
    for r in system.restaurants.values():
        print(f"   {r}")

    print("\n📊 Customers:")
    for c in system.customers.values():
        print(f"   {c}")

    print("\n📊 Agents:")
    for a in system.agents.values():
        print(f"   {a}")

    print("\n📊 All Orders:")
    for o in system.orders.values():
        print(f"   {o}")

    print(f"\n🔒 Singleton: {system is FoodDeliverySystem()} ✓")

    print("\n" + "=" * 65)
    print("       ALL TESTS COMPLETE! 🎉")
    print("=" * 65)
