## Factory Functions
![Factory Functions Introduction](../images/factory_functions_intro.png)

Factory functions are just functions that create and return objects with specific configurations. Think of them like a real factory—you send in some raw materials (parameters), and it gives you back a finished product (object) ready to use.

### The Coffee Shop Analogy

Imagine you're running a coffee shop.

**Without a factory:** Every barista makes drinks differently. One barista remembers to add the syrup, another forgets. One uses whole milk by default, another uses skim. It's chaos, and your drinks are inconsistent.

**With a factory:** You create a standardized recipe card for each drink type. "Latte: espresso + steamed milk + foam, no sweetener." "Mocha: espresso + chocolate syrup + steamed milk + whipped cream." Now every barista follows the same recipe, and you get consistency.

That's what factory functions do for code—they ensure objects are created consistently with the right configuration every time.

---

### Why I Needed Factories

In my federated learning project, I work with PyTorch `DataLoader` objects all the time. A DataLoader is like a conveyor belt that feeds batches of data into my neural network for training.

**Here's the problem I ran into:**

```python
# Training DataLoader
train_loader = DataLoader(
    dataset,
    batch_size=1024,
    shuffle=True,        # CRITICAL: Need this for training!
    num_workers=4,
    pin_memory=True,
    drop_last=False
)

# Validation DataLoader
val_loader = DataLoader(
    dataset,
    batch_size=1024,
    shuffle=False,       # CRITICAL: Don't want this for validation!
    num_workers=4,
    pin_memory=True,
    drop_last=False
)
```

I had to remember to set `shuffle=True` for training and `shuffle=False` for validation. Easy to mess up, especially when you're copy-pasting code at 2 AM.

Plus, I was repeating this same configuration in like 5 different places:
- Centralized training
- Federated client training
- Validation loaders
- Test loaders
- Debug scripts

If I wanted to change `batch_size` or add a new parameter, I'd have to hunt down every single `DataLoader()` call. Total pain.

---

### My Solution: Factory Functions

I created two factory functions in `app/application/data/data_loader_factory.py`:

**1. Training Loader Factory**
```python
def create_train_loader(
    dataset: RatingsDataset,
    batch_size: int = 1024,
    num_workers: int = 0,
    pin_memory: bool = True,
) -> DataLoader:
    """Create DataLoader for training data.

    Training DataLoader has shuffle=True for stochastic gradient descent.
    """
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,      # ← Always shuffles for training
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=False,
    )
```

**2. Evaluation Loader Factory**
```python
def create_eval_loader(
    dataset: RatingsDataset,
    batch_size: int = 1024,
    num_workers: int = 0,
    pin_memory: bool = True,
) -> DataLoader:
    """Create DataLoader for evaluation data (validation or test).

    Evaluation DataLoader has shuffle=False for deterministic evaluation.
    """
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=False,     # ← Never shuffles for evaluation
        num_workers=num_workers,
        pin_memory=pin_memory,
        drop_last=False,
    )
```

---

### The Key Difference: Shuffle

The whole point of having two separate factories is to enforce one critical rule:

| Loader Type | Shuffle | Why? |
|-------------|---------|------|
| **Training** | `True` | SGD (Stochastic Gradient Descent) requires random batches. If you don't shuffle, the model might learn the order of the data instead of actual patterns. |
| **Evaluation** | `False` | Metrics like RMSE need to be reproducible. If you shuffle validation data, you might get slightly different metrics each run due to batch boundaries. |

By encoding this knowledge in separate functions, I **physically cannot** mess it up. Want a training loader? Call `create_train_loader()`. Want an eval loader? Call `create_eval_loader()`. The function names make it obvious, and the behavior is always correct.

---

### Before vs After

**Before (without factories):**
```python
# In my centralized trainer
train_loader = DataLoader(
    train_dataset,
    batch_size=1024,
    shuffle=True,    # Did I remember this?
    num_workers=0,
    pin_memory=True,
    drop_last=False
)

val_loader = DataLoader(
    val_dataset,
    batch_size=1024,
    shuffle=False,   # What if I copy-pasted and forgot to change this?
    num_workers=0,
    pin_memory=True,
    drop_last=False
)

# In my federated client
client_train_loader = DataLoader(
    client_dataset,
    batch_size=256,   # Oops, forgot to keep batch size consistent
    shuffle=True,
    num_workers=0,
    pin_memory=True,
    drop_last=False   # Wait, or was it True?
)
```

**Problems:**
1. Easy to forget `shuffle=True` for training
2. Easy to accidentally leave `shuffle=True` for validation (copy-paste error)
3. Inconsistent configurations across different parts of the code
4. If I want to change a default, I have to find every DataLoader call

**After (with factories):**
```python
# In my centralized trainer
train_loader = create_train_loader(train_dataset, batch_size=1024)
val_loader = create_eval_loader(val_dataset, batch_size=1024)

# In my federated client
client_train_loader = create_train_loader(client_dataset, batch_size=256)
```

**Benefits:**
1. Impossible to mess up shuffle—training always shuffles, eval never shuffles
2. Clear intent: function name tells you what you're getting
3. Consistent configuration across the entire project
4. Change defaults in ONE place

---

### How This Fits Into My Data Pipeline

My data module has a layered structure:

```
preprocessing.py
    ↓ (filters, maps IDs, creates parquet files)
ratings_dataset.py
    ↓ (loads parquet → PyTorch tensors)
data_loader_factory.py  ← YOU ARE HERE
    ↓ (creates configured DataLoaders)
dataset_loader.py
    ↓ (high-level API that uses the factories)
training modules
```

The `dataset_loader.py` file is the public interface. When someone wants a DataLoader, they call:

```python
from app.application.data import DatasetLoader

loader = DatasetLoader(data_dir=Path('data'))
loader.load()

# Internally, these use the factories
train_loader = loader.get_train_loader(batch_size=1024)
val_loader = loader.get_val_loader(batch_size=1024)
```

Under the hood, `get_train_loader()` calls `create_train_loader()`, and `get_val_loader()` calls `create_eval_loader()`. The factories handle the nitty-gritty details so the higher-level code stays clean.

---

### Real Example: Federated Learning

In federated learning, I have 10 clients, each with their own local data. Each client needs its own DataLoaders:

```python
from app.application.data import UserPartitioner, RatingsDataset, create_train_loader, create_eval_loader

partitioner = UserPartitioner(config)
partitioner.partition(data_dir=Path('data'))

# Create loaders for each client
for client_id in range(10):
    train_path, val_path = partitioner.get_client_paths(client_id)

    # Factory ensures EVERY client uses the same configuration
    client_train_loader = create_train_loader(
        RatingsDataset(train_path),
        batch_size=256
    )

    client_val_loader = create_eval_loader(
        RatingsDataset(val_path),
        batch_size=512
    )
```

**Why this matters:** All 10 clients have identical DataLoader configurations. I don't have to worry about Client 3 accidentally using `shuffle=False` for training while Client 7 uses `shuffle=True`. Consistency across all clients is critical for fair comparisons in federated learning experiments.

---

### The SOLID Principle at Play

This follows the **Single Responsibility Principle**:

| Component | Job | Does NOT Do |
|-----------|-----|-------------|
| `RatingsDataset` | Load parquet files and convert to tensors | ❌ Create DataLoaders |
| `create_train_loader()` | Create training DataLoader with shuffle=True | ❌ Load data |
| `create_eval_loader()` | Create eval DataLoader with shuffle=False | ❌ Load data |
| `DatasetLoader` | Coordinate data access | ❌ Know DataLoader implementation details |

Each piece has one clear job. If I want to change how DataLoaders are created (e.g., add `DistributedSampler` for multi-GPU training), I only change the factories. The rest of the codebase doesn't care.

---

### When to Use Factory Functions

**Use factories when:**
1. You're creating the same type of object in multiple places
2. The object needs specific configuration that's easy to mess up
3. You want to enforce consistency (like shuffle=True vs shuffle=False)
4. You want to hide complexity (DataLoader has 10+ parameters)

**Don't use factories when:**
1. You only create the object once
2. The configuration is trivial and hard to mess up
3. Every instance needs totally different configuration (then a factory doesn't help)

---

### Key Takeaways

1. **Factory functions encapsulate object creation** — One function, one type of object, consistent configuration
2. **They make bugs impossible** — I literally cannot create a training loader without shuffle now
3. **They're DRY (Don't Repeat Yourself)** — Write the config once, use it everywhere
4. **They make change easy** — Want to add a new parameter? Change one function, not 20 calls

My `data_loader_factory.py` is tiny (70 lines), but it saves me from so many potential bugs. Training loaders always shuffle, eval loaders never shuffle, and I never have to think about it. That's the power of a good factory.


![Factory Functions Diagram](../images/factory_functions_diagram.png)