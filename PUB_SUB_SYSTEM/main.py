from datetime import datetime
import threading
from queue import Queue   # Thread-safe queue — this is KEY!
import time

# ═══════════════════════════════════════════════════════════════
#                        ENTITIES
# ═══════════════════════════════════════════════════════════════

class Message:
    def __init__(self, id: int, content: str):
        self.id = id
        self.content = content
        self.timestamp = datetime.now()
    def __str__(self):
        return f"Message({self.id}: {self.content})"


class Subscriber:
    """
    Each subscriber has:
    1. A Queue (thread-safe) — holds incoming messages
    2. A Thread (daemon) — processes messages independently
    3. active flag — controls when to stop
    
    WHY THREADING MATTERS:
    ─────────────────────
    Without threading:
        publisher.publish() → calls subscriber.consume() → BLOCKS until done
        If subscriber takes 5 seconds, publisher is stuck for 5 seconds!
    
    With threading:
        publisher.publish() → puts message in subscriber's queue → RETURNS INSTANTLY
        subscriber's thread (running separately) picks up message → processes it
        Publisher is NOT blocked at all!
    
    HOW IT WORKS:
    ─────────────
    1. When Subscriber is created, a daemon thread starts running _consume()
    2. _consume() calls self.queue.get() — this BLOCKS (waits) until a message arrives
       (No CPU waste! It just sleeps until queue has something)
    3. When publisher puts a message in the queue, .get() unblocks and returns the message
    4. Subscriber processes it, then loops back to .get() to wait for next message
    5. To stop: put None (poison pill) in queue → thread sees None → exits loop → dies
    
    THREAD-SAFE QUEUE vs LIST:
    ──────────────────────────
    ❌ list:  self.queue.append(msg) — NOT thread-safe, can corrupt with concurrent access
    ✅ Queue: self.queue.put(msg)    — thread-safe, designed for producer-consumer pattern
    
    ❌ list:  while True: if len(queue) > 0: queue.pop(0)  — busy-waiting, burns CPU
    ✅ Queue: msg = self.queue.get()  — blocks efficiently, zero CPU when waiting
    """
    
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
        self.queue = Queue()        # Thread-safe message queue
        self.active = True          # Flag to stop the thread
        
        # Create and start a daemon thread
        # daemon=True means: thread dies automatically when main program exits
        self.thread = threading.Thread(target=self._consume, daemon=True)
        self.thread.start()
    
    def _consume(self):
        """
        Runs in its own thread. Continuously pulls messages from the queue.
        
        queue.get() BLOCKS until a message is available — no busy waiting!
        This is much better than: while True: if len(queue) > 0: ...
        """
        while self.active:
            message = self.queue.get()   # Blocks here until message arrives
            
            if message is None:          # Poison pill = shutdown signal
                print(f"  🛑 {self.name} shutting down")
                break
            
            # Simulate processing (this is where the callback logic goes)
            print(f"  📩 {self.name} received: {message.content}")
    
    def add_message(self, message: Message):
        """Called by Topic — puts message in this subscriber's queue."""
        self.queue.put(message)     # Thread-safe! No lock needed.
    
    def stop(self):
        """Graceful shutdown using poison pill pattern."""
        self.active = False
        self.queue.put(None)        # Unblocks the .get() call so thread can exit
    
    def __str__(self):
        return f"Subscriber({self.id}: {self.name})"


class Topic:
    def __init__(self, name: str, id: int):  # Fixed: was __init (missing underscores!)
        self.name = name
        self.id = id
        self.subscribers = []
        self._lock = threading.Lock()   # Protects subscriber list
    
    def add_subscriber(self, subscriber: Subscriber):
        with self._lock:
            self.subscribers.append(subscriber)
            print(f"  ✅ {subscriber.name} subscribed to '{self.name}'")
    
    def remove_subscriber(self, subscriber: Subscriber):
        with self._lock:
            self.subscribers.remove(subscriber)
            print(f"  ❌ {subscriber.name} unsubscribed from '{self.name}'")
    
    def publish_message(self, message: Message):
        """Fan-out: puts message into EACH subscriber's queue."""
        with self._lock:
            for subscriber in self.subscribers:
                subscriber.add_message(message)   # Non-blocking! Just puts in queue.
    
    def __str__(self):
        return f"Topic({self.id}: {self.name})"


class Publisher:
    def __init__(self, id: int, name: str):
        self.id = id
        self.name = name
    
    def publish(self, topic: Topic, message: Message):
        print(f"  📤 {self.name} published to '{topic.name}': {message.content}")
        topic.publish_message(message)
    
    def __str__(self):
        return f"Publisher({self.id}: {self.name})"


class PubSubSystem:
    """Singleton — central broker managing all topics."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PubSubSystem, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.topics = {}
        self.publishers = []
        self.subscribers = []
    
    def create_topic(self, name: str, id: int) -> Topic:
        topic = Topic(name, id)
        self.topics[id] = topic
        print(f"  📁 Topic '{name}' created")
        return topic
    
    def create_publisher(self, id: int, name: str) -> Publisher:
        publisher = Publisher(id, name)
        self.publishers.append(publisher)
        return publisher
    
    def create_subscriber(self, id: int, name: str) -> Subscriber:
        subscriber = Subscriber(id, name)
        self.subscribers.append(subscriber)
        return subscriber
    
    def subscribe(self, topic: Topic, subscriber: Subscriber):
        topic.add_subscriber(subscriber)
    
    def unsubscribe(self, topic: Topic, subscriber: Subscriber):
        topic.remove_subscriber(subscriber)
    
    def publish(self, publisher: Publisher, topic: Topic, message: Message):
        publisher.publish(topic, message)
    
    def shutdown(self):
        """Gracefully stop all subscriber threads."""
        print("\n🔌 Shutting down all subscribers...")
        for sub in self.subscribers:
            sub.stop()


# ═══════════════════════════════════════════════════════════════
#                        DEMO
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("       PUB-SUB SYSTEM - LLD DEMO")
    print("=" * 60)

    system = PubSubSystem()

    # --- Setup Topics ---
    print("\n📁 Creating Topics:")
    orders_topic = system.create_topic("orders", 1)
    payments_topic = system.create_topic("payments", 2)

    # --- Setup Publishers ---
    order_service = system.create_publisher(1, "OrderService")
    payment_service = system.create_publisher(2, "PaymentService")

    # --- Setup Subscribers ---
    print("\n👥 Creating Subscribers:")
    email_service = system.create_subscriber(1, "EmailService")
    inventory_service = system.create_subscriber(2, "InventoryService")
    analytics_service = system.create_subscriber(3, "AnalyticsService")

    # --- Subscribe to Topics ---
    print("\n🔗 Subscribing:")
    system.subscribe(orders_topic, email_service)        # EmailService → orders
    system.subscribe(orders_topic, inventory_service)    # InventoryService → orders
    system.subscribe(orders_topic, analytics_service)    # AnalyticsService → orders
    system.subscribe(payments_topic, analytics_service)  # AnalyticsService → payments too!

    # --- Test 1: Publish to "orders" ---
    print("\n" + "─" * 40)
    print("TEST 1: Publish to 'orders' (3 subscribers)")
    print("─" * 40)
    system.publish(order_service, orders_topic, Message(1, "Order #101 placed"))
    time.sleep(0.5)  # Wait for async subscribers to process

    # --- Test 2: Publish to "payments" ---
    print("\n" + "─" * 40)
    print("TEST 2: Publish to 'payments' (1 subscriber)")
    print("─" * 40)
    system.publish(payment_service, payments_topic, Message(2, "Payment for Order #101 received"))
    time.sleep(0.5)

    # --- Test 3: Multiple messages ---
    print("\n" + "─" * 40)
    print("TEST 3: Rapid-fire 3 messages (ordering preserved)")
    print("─" * 40)
    system.publish(order_service, orders_topic, Message(3, "Order #102 placed"))
    system.publish(order_service, orders_topic, Message(4, "Order #103 placed"))
    system.publish(order_service, orders_topic, Message(5, "Order #104 placed"))
    time.sleep(0.5)

    # --- Test 4: Unsubscribe ---
    print("\n" + "─" * 40)
    print("TEST 4: Unsubscribe EmailService, then publish")
    print("─" * 40)
    system.unsubscribe(orders_topic, email_service)
    system.publish(order_service, orders_topic, Message(6, "Order #105 placed"))
    time.sleep(0.5)
    print("  (EmailService should NOT receive this ☝️)")

    # --- Test 5: Singleton check ---
    print("\n" + "─" * 40)
    print("TEST 5: Singleton check")
    print("─" * 40)
    system2 = PubSubSystem()
    print(f"  system is system2: {system is system2} ✓")

    # --- Shutdown ---
    system.shutdown()
    time.sleep(0.5)

    print("\n" + "=" * 60)
    print("       ALL TESTS COMPLETE! 🎉")
    print("=" * 60)