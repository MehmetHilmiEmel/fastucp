# Checkout Builder

The `CheckoutBuilder` is the core utility in FastUCP. It follows the Builder Design Pattern to help you construct complex `CheckoutResponse` objects without manually instantiating dozens of nested Pydantic models.

## Basic Usage

```python
from fastucp import CheckoutBuilder

# Initialize with the app instance and a session ID
cart = CheckoutBuilder(app, session_id="sess_123", currency="USD")
```

## Adding Items
Use add_item to automatically calculate line item totals and subtotals.
```python
cart.add_item(
    item_id="sku_1",
    title="Coffee Mug",
    price=1500,      # 1500 cents = $15.00
    quantity=2,
    img_url="...",
    description="Ceramic mug"
)
```
## Managing Buyer Data & Validation
You can set buyer data and add errors if specific fields are missing. This triggers the "requires_buyer_input" status in the UCP protocol.
```python
cart.set_buyer(buyer_data)

if not buyer_data.email:
    cart.add_error(
        code="missing", 
        path="$.buyer.email", 
        message="Email is required."
    )
```

## Shipping & Discounts
The builder handles the complex nesting of Fulfillment Groups and Discount Allocations automatically.
```python
# Add Shipping
cart.add_shipping_option("opt_1", "Ground Shipping", 500)
cart.select_shipping_option("opt_1") # Adds to total

# Add Discount
cart.add_discount("SAVE10", 1000, "Loyalty Discount") # Subtracts from total
```

## Build
Finally, call .build() to get the Pydantic model ready for the response.
```python
response = cart.build()
```