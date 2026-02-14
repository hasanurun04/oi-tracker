"""
Supply servisi — önce CMC dener, olmadıysa CoinGecko dener.
Her coin ayrı ayrı sorgulanır, startup'ta toplu istek atmaz.
"""
import time
import httpx
from config import CMC_BASE, CMC_API_KEY, COINGECKO_BASE, SUPPLY_CACHE_TTL

# { "BTCUSDT": (supply, timestamp) }
_supply_cache: dict[str, tuple[float, float]] = {}

# Bilinen sembol → CoinGecko ID eşleştirmesi (fallback için)
_CG_IDS: dict[str, str] = {
    "BTC": "bitcoin", "ETH": "ethereum", "BNB": "binancecoin",
    "SOL": "solana", "XRP": "ripple", "ADA": "cardano",
    "DOGE": "dogecoin", "AVAX": "avalanche-2", "LINK": "chainlink",
    "DOT": "polkadot", "MATIC": "matic-network", "UNI": "uniswap",
    "LTC": "litecoin", "ATOM": "cosmos", "ETC": "ethereum-classic",
    "XLM": "stellar", "TRX": "tron", "NEAR": "near",
    "APT": "aptos", "OP": "optimism", "ARB": "arbitrum",
    "SUI": "sui", "PEPE": "pepe", "SHIB": "shiba-inu",
    "MKR": "maker", "AAVE": "aave", "CRV": "curve-dao-token",
    "RNDR": "render-token", "RENDER": "render-token",
    "FET": "fetch-ai", "GRT": "the-graph",
    "LDO": "lido-dao", "WLD": "worldcoin-org",
    "JUP": "jupiter-exchange-solana",
    "TON": "the-open-network", "KAS": "kaspa",
    "TAO": "bittensor", "ENA": "ethena",
    "INJ": "injective-protocol", "SEI": "sei-network",
    "TIA": "celestia", "NOT": "notcoin",
    "WIF": "dogwifcoin", "BONK": "bonk",
    "PYTH": "pyth-network", "AR": "arweave",
    "RUNE": "thorchain", "STX": "blockstack",
    "FLOW": "flow", "HBAR": "hedera-hashgraph",
    "ICP": "internet-computer", "ALGO": "algorand",
    "VET": "vechain", "FIL": "filecoin",
    "SAND": "the-sandbox", "MANA": "decentraland",
    "GALA": "gala", "AXS": "axie-infinity",
    "FTM": "fantom", "IMX": "immutable-x",
    "EIGEN": "eigenlayer", "SPACE": "spacecoin",
    "STG": "stargate-finance", "BLUR": "blur",
    "PIXEL": "pixels", "PORTAL": "portal-gaming",
    "STRK": "starknet", "ALT": "altlayer",
    "JTO": "jito-governance-token", "MANTA": "manta-network",
    "ZK": "zksync", "W": "wormhole",
    "IO": "io-net", "ZRO": "layerzero",
}


def _strip_suffix(futures_symbol: str) -> str:
    sym = futures_symbol.upper()
    for suffix in ("USDT", "BUSD", "USDC", "USD"):
        if sym.endswith(suffix):
            return sym[:-len(suffix)]
    return sym


async def get_supply(futures_symbol: str) -> float | None:
    """
    Verilen Binance futures sembolü için circulating supply döner.
    Önce cache bakar, sonra CMC dener, sonra CoinGecko dener.
    """
    now = time.time()
    if futures_symbol in _supply_cache:
        val, ts = _supply_cache[futures_symbol]
        if (now - ts) < SUPPLY_CACHE_TTL:
            return val

    base = _strip_suffix(futures_symbol)

    # ── 1. CMC dene ───────────────────────────────────────
    supply = await _from_cmc(base)

    # ── 2. CoinGecko dene ─────────────────────────────────
    if supply is None:
        supply = await _from_coingecko(base)

    if supply is not None:
        _supply_cache[futures_symbol] = (supply, now)

    return supply


def supports(futures_symbol: str) -> bool:
    """Bu sembol için supply verisi alabiliyor muyuz?"""
    base = _strip_suffix(futures_symbol)
    return base in _CG_IDS  # en azından CoinGecko fallback var


async def _from_cmc(base_symbol: str) -> float | None:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                f"{CMC_BASE}/cryptocurrency/quotes/latest",
                headers={"X-CMC_PRO_API_KEY": CMC_API_KEY},
                params={
                    "symbol": base_symbol,
                    "convert": "USD",
                    "aux": "circulating_supply,cmc_rank",
                },
            )
            if resp.status_code != 200:
                print(f"[CMC] {base_symbol} HTTP {resp.status_code}: {resp.text[:200]}")
                return None
            data = resp.json()

        # data["data"]["SPACE"] -> list veya dict olabilir
        raw = data.get("data", {}).get(base_symbol.upper(), [])
        if isinstance(raw, dict):
            entries = [raw]
        elif isinstance(raw, list):
            entries = raw
        else:
            return None

        if not entries:
            return None

        # cmc_rank en küçük = market cap en büyük = Binance'teki coin
        best = min(entries, key=lambda c: c.get("cmc_rank") or 99999)
        print(f"[CMC] {base_symbol} -> {best.get('name')} (rank #{best.get('cmc_rank')})")
        supply = best.get("circulating_supply")
        return float(supply) if supply else None

    except Exception as e:
        print(f"[CMC] {base_symbol} supply hatası: {e}")
        return None


async def _from_coingecko(base_symbol: str) -> float | None:
    cg_id = _CG_IDS.get(base_symbol.upper())
    if not cg_id:
        return None

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            resp = await client.get(
                f"{COINGECKO_BASE}/coins/{cg_id}",
                params={
                    "localization": "false",
                    "tickers": "false",
                    "market_data": "true",
                    "community_data": "false",
                    "developer_data": "false",
                },
            )
            if resp.status_code != 200:
                return None
            data = resp.json()

        supply = data.get("market_data", {}).get("circulating_supply")
        return float(supply) if supply else None

    except Exception as e:
        print(f"[CoinGecko] {base_symbol} supply hatası: {e}")
        return None