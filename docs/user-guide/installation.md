# Installation

## Prerequisites

FastUCP requires **Python 3.10** or higher.

## Install via Pip

```bash
pip install fastucp-python
```

## Install via uv (Recommended)
If you are using uv for package management:
```bash
uv add fastucp-python
```

## Dependencies
FastUCP automatically installs the following core dependencies:

* fastapi: For the web server framework.
* uvicorn: For running the server.
* pydantic: For data validation and UCP models.
* jwcrypto: For JWS signature handling.