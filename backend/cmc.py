import time
import httpx
from .config import CMC_BASE, CMC_API_KEY, SUPPLY_CACHE_TTL

# ── Sembol → CMC ID + supply map ──────────────────────────
# { "BTC": { "id": 1, "supply": 19700000.0, "ts": 1234567890 } }
_coin_map: dict[str, dict] = {}
_map_loaded = False

# ── Supply cache ──────────────────────────────────────────
_supply_cache: dict[str, tuple[float, float]] = {}


async def load_coin_map():
    """
    CMC /cryptocurrency/map endpoint'inden tüm aktif coinleri çeker.
    Rank sıralamalı gelir — sembol çakışmasında rank'i küçük (büyük coin) kazanır.
    """
    global _coin_map, _map_loaded

    if _map_loaded:
        return

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{CMC_BASE}/cryptocurrency/map",
                headers={"X-CMC_PRO_API_KEY": CMC_API_KEY},
                params={"status": "active", "limit": 5000}
            )
            resp.raise_for_status()
            data = resp.json()

        coins = data.get("data", [])
        temp: dict[str, dict] = {}

        for coin in coins:
            sym = coin["symbol"].upper()
            # İlk gelen = rank'i en küçük = market cap en büyük
            if sym not in temp:
                temp[sym] = {"id": coin["id"], "name": coin["name"]}

        _coin_map  = temp
        _map_loaded = True
        print(f"[CMC] {len(_coin_map)} coin yüklendi.")

    except Exception as e:
        print(f"[CMC] Coin listesi yüklenemedi: {e}")


def resolve_symbol(futures_symbol: str) -> dict | None:
    """
    BTCUSDT → { id: 1, name: "Bitcoin" }
    USDT/BUSD/USDC suffix'ini soyar, map'te arar.
    """
    sym = futures_symbol.upper()
    for suffix in ("USDT", "BUSD", "USDC", "USD"):
        if sym.endswith(suffix):
            sym = sym[:-len(suffix)]
            break
    return _coin_map.get(sym)


async def ensure_loaded():
    if not _map_loaded:
        await load_coin_map()


async def get_circulating_supply(cmc_id: int) -> float | None:
    """
    CMC /cryptocurrency/quotes/latest endpoint'inden supply çeker.
    SUPPLY_CACHE_TTL süre cache'lenir.
    """
    cache_key = str(cmc_id)
    now = time.time()

    if cache_key in _supply_cache:
        cached_val, cached_ts = _supply_cache[cache_key]
        if (now - cached_ts) < SUPPLY_CACHE_TTL:
            return cached_val

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{CMC_BASE}/cryptocurrency/quotes/latest",
                headers={"X-CMC_PRO_API_KEY": CMC_API_KEY},
                params={"id": cmc_id, "convert": "USD"}
            )
            resp.raise_for_status()
            data = resp.json()

        coin_data = data.get("data", {}).get(str(cmc_id), {})
        supply    = coin_data.get("circulating_supply")

        if supply is None:
            return None

        supply = float(supply)
        _supply_cache[cache_key] = (supply, now)
        return supply

    except Exception as e:
        print(f"[CMC] Supply alınamadı (id={cmc_id}): {e}")
        if cache_key in _supply_cache:
            return _supply_cache[cache_key][0]
        return None