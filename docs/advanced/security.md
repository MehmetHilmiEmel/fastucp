# Security (JWS Signing)

The Universal Commerce Protocol requires responses to be signed using **JSON Web Signature (JWS)** to ensure authenticity. FastUCP handles this via middleware.

## Configuring Signing

You need to provide a private key (in JWK JSON format) when initializing the application.

```python
private_key_json = """
{
    "kty": "EC",
    "crv": "P-256",
    "x": "...",
    "y": "...",
    "d": "..." 
}
"""

app = FastUCP(
    ...,
    signing_key=private_key_json
)
```

## What happens internally?
FastUCP captures the outgoing JSON response.

* It calculates a JWS Detached Signature using ES256.

* It attaches the signature to the UCP-Signature HTTP header.

* This ensures that any client (Google, a Marketplace, or an Agent) can verify that the payload originated from your server and hasn't been tampered with.