import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.requests import Request
from starlette.responses import Response
from jwcrypto import jwk, jws

class UCPSigningMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, private_key_json: str):
        super().__init__(app)

        self.key = jwk.JWK.from_json(private_key_json)

    async def dispatch(self, request: Request, call_next):

        response = await call_next(request)


        if response.headers.get("content-type") == "application/json":

            response_body = [section async for section in response.body_iterator]
            response.body_iterator = iter(response_body) # Rewind stream
            body_bytes = b"".join(response_body)
            
            try:
                signer = jws.JWS(body_bytes)
                signer.add_signature(
                    self.key, 
                    alg="ES256", # UCP standard is usually ES256
                    protected={"alg": "ES256", "kid": self.key.key_id}
                )
                
                signature = signer.serialize(compact=True)
                response.headers["UCP-Signature"] = signature
                
            except Exception as e:
                print(f"⚠️ Signing Error: {e}")

        return response