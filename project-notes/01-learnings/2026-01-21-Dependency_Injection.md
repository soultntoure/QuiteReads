## Dependency Injection

Dependency injection is a design pattern where an object receives its dependencies from an external source rather than creating them itself. Instead of a class being responsible for instantiating the things it needs, those things are "injected" from outside.

### The Restaurant Analogy

Imagine you're a chef at a restaurant.

**Without dependency injection:** You have to grow your own vegetables, raise your own livestock, mill your own flour, and make your own equipment before you can cook anything. You're tightly coupled to every part of the supply chain.

**With dependency injection:** Suppliers deliver ingredients to your kitchen. You just specify what you need (fresh tomatoes, chicken, olive oil), and they arrive ready to use. You can focus on cooking, and if you want to switch from one tomato supplier to another, you just change who delivers—your recipes stay the same.
![alt text](image-4.png)

### Code Example

**Without DI (tightly coupled):**
```python
class EmailService:
    def send(self, message):
        print(f"Sending email: {message}")

class OrderProcessor:
    def __init__(self):
        self.notifier = EmailService()  # Creates its own dependency
    
    def process(self, order):
        # process the order...
        self.notifier.send(f"Order {order} confirmed")
```

The problem: `OrderProcessor` is hardwired to `EmailService`. Want to use SMS instead? You have to modify the class.

**With DI (loosely coupled):**
```python
class OrderProcessor:
    def __init__(self, notifier):  # Dependency is injected
        self.notifier = notifier
    
    def process(self, order):
        # process the order...
        self.notifier.send(f"Order {order} confirmed")

# Now you can inject whatever you want
order_processor = OrderProcessor(EmailService())
# or
order_processor = OrderProcessor(SMSService())
# or for testing
order_processor = OrderProcessor(MockNotifier())
```

### Why It Matters

1. **Testability** — You can inject mock objects for unit testing
2. **Flexibility** — Swap implementations without changing the class
3. **Single responsibility** — Classes focus on their job, not on building their tools
4. **Decoupling** — Components depend on abstractions, not concrete implementations