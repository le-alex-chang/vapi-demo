from typing import Dict, List, Optional
import difflib
from threading import Lock

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(title="Catalog and Cart API")

# Allow cross-origin requests (broad for demo; tighten origins for prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Fixed catalog of building materials.
# Keys are product IDs, values carry basic details.
CATALOG: Dict[str, Dict[str, object]] = {
    "concrete_bag": {"name": "Concrete Mix 60lb", "unit": "bag", "price": 5.75},
    "plywood_sheet": {"name": "Plywood 3/4in 4x8", "unit": "sheet", "price": 42.50},
    "lumber_2x4": {"name": "Lumber 2x4x8 SPF", "unit": "piece", "price": 4.25},
    "drywall_panel": {"name": "Drywall 1/2in 4x8", "unit": "panel", "price": 12.40},
    "rebar_10ft": {"name": "Rebar #4 10ft", "unit": "piece", "price": 8.10},
    "brick_clay": {"name": "Clay Brick", "unit": "each", "price": 0.55},
    "mortar_bag": {"name": "Mortar Mix 60lb", "unit": "bag", "price": 6.30},
    "insulation_roll": {"name": "Fiberglass Insulation R-13", "unit": "roll", "price": 16.90},
    "roof_shingle": {"name": "Asphalt Shingles Bundle", "unit": "bundle", "price": 31.00},
    "galv_nails": {"name": "Galvanized Nails 1lb", "unit": "box", "price": 4.80},
    "wood_screws": {"name": "Wood Screws 1lb", "unit": "box", "price": 5.10},
    "paint_gallon": {"name": "Interior Paint White", "unit": "gallon", "price": 24.75},
    "primer_gallon": {"name": "Primer Sealer", "unit": "gallon", "price": 21.30},
    "acrylic_caulk": {"name": "Acrylic Caulk 10oz", "unit": "tube", "price": 3.40},
    "pvc_pipe_10ft": {"name": "PVC Pipe 3/4in 10ft", "unit": "piece", "price": 6.60},
    "copper_pipe_10ft": {"name": "Copper Pipe 1/2in 10ft", "unit": "piece", "price": 32.00},
    "electrical_cable": {"name": "NM-B Cable 12/2 50ft", "unit": "roll", "price": 48.00},
    "duplex_outlet": {"name": "Duplex Outlet 15A", "unit": "each", "price": 1.20},
    "toggle_switch": {"name": "Toggle Light Switch", "unit": "each", "price": 1.40},
    "led_fixture": {"name": "LED Ceiling Fixture", "unit": "each", "price": 36.00},
}


class Product(BaseModel):
    id: str
    name: str
    unit: str
    price: float


class SearchResult(BaseModel):
    query: str
    found: bool
    product: Optional[Product] = None


class BulkSearchResponse(BaseModel):
    results: List[SearchResult]
    not_found: List[str]


class ModifyItem(BaseModel):
    product_id: str = Field(..., description="Catalog product identifier")
    quantity: int = Field(..., gt=0, description="Quantity to add or remove")


class AddToCartRequest(BaseModel):
    user_id: str = Field(..., description="Unique cart owner identifier")
    items: List[ModifyItem]


class RemoveFromCartRequest(BaseModel):
    user_id: str = Field(..., description="Unique cart owner identifier")
    items: List[ModifyItem]


class CartItem(BaseModel):
    product_id: str
    name: str
    quantity: int


class CartResponse(BaseModel):
    user_id: str
    items: List[CartItem]
    total_items: int


_carts: Dict[str, Dict[str, int]] = {}
_cart_lock = Lock()


def _catalog_product(product_id: str) -> Product:
    if product_id not in CATALOG:
        raise HTTPException(status_code=404, detail="Product not found in catalog")

    data = CATALOG[product_id]
    return Product(id=product_id, name=data["name"], unit=data["unit"], price=float(data["price"]))


def _cart_response(user_id: str, cart: Dict[str, int]) -> CartResponse:
    response_items = [
        CartItem(product_id=pid, name=CATALOG[pid]["name"], quantity=qty) for pid, qty in cart.items()
    ]
    total_items = sum(item.quantity for item in response_items)
    return CartResponse(user_id=user_id, items=response_items, total_items=total_items)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/products/search", response_model=BulkSearchResponse)
def search_products(queries: List[str] = Query(...)) -> BulkSearchResponse:
    if not queries:
        raise HTTPException(status_code=400, detail="Query list must not be empty")

    results: List[SearchResult] = []
    not_found_queries: List[str] = []

    # Prepare a mapping of normalized name -> product_id for fuzzy matching
    # We use all lowercase for simpler matching on the name
    name_to_pid = {pdata["name"].lower(): pid for pid, pdata in CATALOG.items()}
    all_names = list(name_to_pid.keys())

    for q in queries:
        q_norm = q.lower().strip()
        if not q_norm:
            continue

        matched_product = None
        
        # 1. Exact ID match
        if q_norm in CATALOG:
             data = CATALOG[q_norm]
             matched_product = Product(id=q_norm, name=data["name"], unit=data["unit"], price=float(data["price"]))
        
        # 2. Fuzzy name match if no ID match
        if not matched_product:
            # get_close_matches details:
            # n=1: return top 1 best match
            # cutoff=0.4: match threshold (0.0 to 1.0)
            matches = difflib.get_close_matches(q_norm, all_names, n=1, cutoff=0.4)
            if matches:
                best_match_name = matches[0]
                pid = name_to_pid[best_match_name]
                data = CATALOG[pid]
                matched_product = Product(id=pid, name=data["name"], unit=data["unit"], price=float(data["price"]))

        if matched_product:
            results.append(SearchResult(query=q, found=True, product=matched_product))
        else:
            results.append(SearchResult(query=q, found=False, product=None))
            not_found_queries.append(q)

    return BulkSearchResponse(results=results, not_found=not_found_queries)


@app.post("/cart/add", response_model=CartResponse)
def add_to_cart(request: AddToCartRequest) -> CartResponse:
    with _cart_lock:
        cart = _carts.setdefault(request.user_id, {})

        for item in request.items:
            product = _catalog_product(item.product_id)
            current_qty = cart.get(product.id, 0)
            cart[product.id] = current_qty + item.quantity

        return _cart_response(request.user_id, cart)


@app.post("/cart/remove", response_model=CartResponse)
def remove_from_cart(request: RemoveFromCartRequest) -> CartResponse:
    with _cart_lock:
        cart = _carts.setdefault(request.user_id, {})

        for item in request.items:
            product = _catalog_product(item.product_id)
            if product.id not in cart:
                raise HTTPException(status_code=404, detail=f"{product.name} not in cart")
            current_qty = cart[product.id]
            new_qty = current_qty - item.quantity
            if new_qty > 0:
                cart[product.id] = new_qty
            else:
                cart.pop(product.id, None)

        return _cart_response(request.user_id, cart)


# To run locally:
# uvicorn backend.main:app --reload

