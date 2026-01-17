# FastUCP ⚡️

**The "FastAPI" for the Universal Commerce Protocol (UCP).**

FastUCP is a high-performance, developer-friendly Python framework designed to build UCP-compliant Merchant Servers and Commerce Agents. It bridges the gap between complex commerce standards and modern Python development.



## 🚀 Why FastUCP?

The Universal Commerce Protocol involves complex JSON schemas, rigorous validation rules, and deep object nesting. **FastUCP** abstracts this complexity away.

* **🧱 Official Models:** Built directly on top of Google's auto-generated Pydantic models for 100% protocol compliance.
* **🛠 Builder Pattern:** No more manual JSON construction. Use our `CheckoutBuilder` to write business logic, not boilerplate.
* **🤖 AI Ready (MCP):** Native support for the **Model Context Protocol**, allowing LLMs (Claude, Gemini) to interact with your store out of the box.
* **🔍 Auto-Discovery:** Automatically generates the `/.well-known/ucp` manifest based on your registered endpoints.

## Minimal Example

Create a store in just a few lines of code:

```python
from fastucp import FastUCP, CheckoutBuilder
from fastucp.types import CheckoutCreateRequest

app = FastUCP(title="My Store", base_url="[http://127.0.0.1:8000](http://127.0.0.1:8000)")

@app.checkout("/checkout-sessions")
def create_session(payload: CheckoutCreateRequest):
    # Create a new session using the Builder
    cart = CheckoutBuilder(app, session_id="session_1")
    
    # Add a product
    cart.add_item(
        item_id="sku_1",
        title="Premium T-Shirt",
        price=2500,  # $25.00
        quantity=1,
        img_url="[https://example.com/tshirt.jpg](https://example.com/tshirt.jpg)"
    )
    
    return cart.build()
```
[Get Started](user-guide/installation.md)
[View on GitHub](https://github.com/MehmetHilmiEmel/fastucp)