import time
import httpx
from config import COINGECKO_BASE, SUPPLY_CACHE_TTL

# ── Sembol → CoinGecko ID map (market cap sıralamalı) ─────
# { "BTC": "bitcoin", "ETH": "ethereum", ... }
_symbol_map: dict[str, str] = {}
_symbol_map_loaded = False

# ── Supply cache ──────────────────────────────────────────
# { cg_id: (supply, timestamp) }
_supply_cache: dict[str, tuple[float, float]] = {}


async def _load_coin_list():
    """
    CoinGecko /coins/markets endpoint'inden market cap sıralamasıyla
    ilk 2000 coini çeker. Sembol çakışmasında market cap'i büyük olan kazanır.
    """
    global _symbol_map, _symbol_map_loaded

    if _symbol_map_loaded:
        return

    temp_map: dict[str, str] = {}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Market cap sıralamasıyla sayfa sayfa çek (max 250/sayfa)
            for page in range(1, 9):  # 8 sayfa × 250 = 2000 coin
                resp = await client.get(
                    f"{COINGECKO_BASE}/coins/markets",
                    params={
                        "vs_currency": "usd",
                        "order": "market_cap_desc",
                        "per_page": 250,
                        "page": page,
                        "sparkline": "false",
                    }
                )
                resp.raise_for_status()
                coins = resp.json()
                if not coins:
                    break

                for coin in coins:
                    sym = coin["symbol"].lower()
                    # İlk gelen = market cap'i büyük olan, üzerine yazma
                    if sym not in temp_map:
                        temp_map[sym] = coin["id"]

                # Rate limit için kısa bekleme
                await _sleep(0.3)

        _symbol_map = temp_map
        _symbol_map_loaded = True
        print(f"[CoinGecko] {len(_symbol_map)} coin yüklendi (market cap sıralamalı).")

    except Exception as e:
        print(f"[CoinGecko] Coin listesi yüklenemedi: {e}")
        # Yüklenemese bile temel coinleri elle tanımla
        _symbol_map.update(_FALLBACK)
        _symbol_map_loaded = True
        print(f"[CoinGecko] Fallback liste kullanılıyor ({len(_symbol_map)} coin).")


async def _sleep(seconds: float):
    import asyncio
    await asyncio.sleep(seconds)


# Fallback: en yaygın coinler — API çalışmazsa bunlar kullanılır
_FALLBACK: dict[str, str] = {
    "btc": "bitcoin", "eth": "ethereum", "bnb": "binancecoin",
    "sol": "solana", "xrp": "ripple", "ada": "cardano",
    "doge": "dogecoin", "avax": "avalanche-2", "link": "chainlink",
    "dot": "polkadot", "matic": "matic-network", "uni": "uniswap",
    "ltc": "litecoin", "atom": "cosmos", "etc": "ethereum-classic",
    "xlm": "stellar", "trx": "tron", "near": "near",
    "apt": "aptos", "op": "optimism", "arb": "arbitrum",
    "sui": "sui", "pepe": "pepe", "shib": "shiba-inu",
    "mkr": "maker", "aave": "aave", "crv": "curve-dao-token",
    "rndr": "render-token", "fet": "fetch-ai", "grt": "the-graph",
    "ldo": "lido-dao", "wld": "worldcoin-org", "jup": "jupiter-exchange-solana",
    "ton": "the-open-network", "kas": "kaspa", "tao": "bittensor",
    "ena": "ethena", "inj": "injective-protocol", "sei": "sei-network",
    "tia": "celestia", "not": "notcoin", "wif": "dogwifcoin",
    "bonk": "bonk", "pyth": "pyth-network", "ar": "arweave",
    "rune": "thorchain", "stx": "blockstack", "flow": "flow",
    "hbar": "hedera-hashgraph", "icp": "internet-computer",
    "algo": "algorand", "vet": "vechain", "fil": "filecoin",
    "sand": "the-sandbox", "mana": "decentraland", "gala": "gala",
    "axs": "axie-infinity", "ftm": "fantom", "imx": "immutable-x",
}


def resolve_cg_id(futures_symbol: str) -> str | None:
    """
    BTCUSDT → bitcoin, SPACEUSDT → space (market cap'e göre doğru eşleşme)
    USDT/BUSD/USDC suffix'ini soyar, map'te arar.
    """
    sym = futures_symbol.upper()
    for suffix in ("USDT", "BUSD", "USDC", "USD"):
        if sym.endswith(suffix):
            sym = sym[:-len(suffix)]
            break

    return _symbol_map.get(sym.lower())


async def ensure_loaded():
    if not _symbol_map_loaded:
        await _load_coin_list()


async def get_circulating_supply(cg_id: str) -> float | None:
    """
    CoinGecko'dan circulating supply döner. SUPPLY_CACHE_TTL süre cache'lenir.
    """
    now = time.time()

    if cg_id in _supply_cache:
        cached_supply, cached_time = _supply_cache[cg_id]
        if (now - cached_time) < SUPPLY_CACHE_TTL:
            return cached_supply

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{COINGECKO_BASE}/coins/{cg_id}",
                params={
                    "localization": "false",
                    "tickers": "false",
                    "market_data": "true",
                    "community_data": "false",
                    "developer_data": "false",
                }
            )
            resp.raise_for_status()
            data = resp.json()

        supply = data.get("market_data", {}).get("circulating_supply")
        if supply is None:
            return None

        supply = float(supply)
        _supply_cache[cg_id] = (supply, now)
        return supply

    except Exception as e:
        print(f"[CoinGecko] Supply alınamadı ({cg_id}): {e}")
        if cg_id in _supply_cache:
            return _supply_cache[cg_id][0]
        return None