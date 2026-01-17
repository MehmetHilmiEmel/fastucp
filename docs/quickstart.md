# Quick Start

## Installation

```bash
pip install fastucp-python

```

## First Application
```python
from fastucp import FastUCP, CheckoutBuilder
from fastucp.types import CheckoutCreateRequest

app = FastUCP(title="My Store", base_url="http://localhost:8000")

@app.checkout("/checkout-sessions")
def create_session(payload: CheckoutCreateRequest):
    cart = CheckoutBuilder(app, "session_1")
    cart.add_item("sku_1", "T-Shirt", 2000, 1, "img.jpg")
    return cart.build()
```