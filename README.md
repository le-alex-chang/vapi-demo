# Catalog and Cart API

A simple FastAPI application for searching building materials and managing a shopping cart.

## Prerequisites

- Python 3.9+
- Node.js (for Cloudflare Tunnel / localtunnel if used)

## Setup

1.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

    Or if using a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

2.  **Run the Backend**
    Start the FastAPI server on port 8000:
    ```bash
    python3 -m uvicorn backend.main:app --reload --port 8000
    ```

3.  **Expose to Public**
    To make the API accessible from the internet (e.g. for Vapi integration), run a tunnel.

    **Option A: Cloudflare Tunnel (Recommended - No Password)**
    ```bash
    # Install if needed: brew install cloudflared
    cloudflared tunnel --url http://localhost:8000
    ```
    *Look for the `trycloudflare.com` URL in the output.*

    **Option B: Localtunnel**
    ```bash
    npx localtunnel --port 8000
    ```
    *Note: `localtunnel` URLs are password-protected by default. API clients may need special headers.*

## API Usage

Replace `YOUR_PUBLIC_URL` with your actual tunnel URL (e.g., `https://annex-cannon-packed-entity.trycloudflare.com`) or `http://localhost:8000`.

### 1. Search Products
Search for multiple items at once using fuzzy matching.

-   **Method**: `GET`
-   **Endpoint**: `/products/search`
-   **Params**: `queries` (list of strings)

```bash
curl "YOUR_PUBLIC_URL/products/search?queries=concrete&queries=plywd&queries=nails"
```

### 2. Add to Cart
Add items to a user's cart.

-   **Method**: `POST`
-   **Endpoint**: `/cart/add`
-   **Body**: JSON with `user_id` and list of `items`.

```bash
curl -X POST "YOUR_PUBLIC_URL/cart/add" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alex123",
    "items": [
      {"product_id": "concrete_bag", "quantity": 5},
      {"product_id": "plywood_sheet", "quantity": 10}
    ]
  }'
```

### 3. Remove from Cart
Remove items from a user's cart.

-   **Method**: `POST`
-   **Endpoint**: `/cart/remove`
-   **Body**: JSON with `user_id` and list of `items`.

```bash
curl -X POST "YOUR_PUBLIC_URL/cart/remove" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alex123",
    "items": [
      {"product_id": "concrete_bag", "quantity": 1}
    ]
  }'
```

### 4. Health Check
Verify the server is running.

```bash
curl "YOUR_PUBLIC_URL/health"
```
