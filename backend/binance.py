import time
import httpx
from config import BINANCE_BASE, SYMBOLS_CACHE_TTL

# Sembol listesi cache (bellekte tutulur, uygulama yeniden başlayana kadar geçerli)
_symbols_cache: list[str] = []
_symbols_cache_time: float = 0.0


async def get_futures_symbols() -> list[str]:
    """
    Binance Futures'taki tüm USDT-M sembollerini döner.
    Sonuç SYMBOLS_CACHE_TTL süre boyunca bellekte tutulur.
    """
    global _symbols_cache, _symbols_cache_time

    now = time.time()
    if _symbols_cache and (now - _symbols_cache_time) < SYMBOLS_CACHE_TTL:
        return _symbols_cache

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{BINANCE_BASE}/fapi/v1/exchangeInfo")
        resp.raise_for_status()
        data = resp.json()

    symbols = [
        s["symbol"]
        for s in data["symbols"]
        if s["quoteAsset"] == "USDT" and s["status"] == "TRADING"
    ]
    symbols.sort()

    _symbols_cache = symbols
    _symbols_cache_time = now
    return symbols


async def get_open_interest(symbol: str) -> dict:
    """
    Verilen sembol için anlık open interest döner.
    Yanıt: { openInterest: float (coin cinsinden), notionalValue: float (USDT cinsinden) }
    """
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{BINANCE_BASE}/fapi/v1/openInterest",
            params={"symbol": symbol}
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "open_interest": float(data["openInterest"]),  # coin adedi
    }


async def get_ticker(symbol: str) -> dict:
    """
    24 saatlik ticker verisi: anlık fiyat + 24s değişim yüzdesi.
    """
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{BINANCE_BASE}/fapi/v1/ticker/24hr",
            params={"symbol": symbol}
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "price": float(data["lastPrice"]),
        "change_pct": float(data["priceChangePercent"]),
        "volume_usdt": float(data["quoteVolume"]),  # 24s USDT hacmi
    }