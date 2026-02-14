import os

BINANCE_BASE   = "https://fapi.binance.com"
CMC_BASE       = "https://pro-api.coinmarketcap.com/v1"
CMC_API_KEY = os.getenv("CMC_API_KEY", "3203614f7a0440a99023abec884d2e02")
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Supply cache süresi (saniye) — 10 dakika
SUPPLY_CACHE_TTL = 600

# Binance sembol listesi cache süresi — 1 saat
SYMBOLS_CACHE_TTL = 3600