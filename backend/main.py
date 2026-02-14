import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import binance
import supply


@asynccontextmanager
async def lifespan(app):
    print("[Startup] OI Tracker hazır.")
    yield


app = FastAPI(title="OI Tracker", version="4.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/")
async def root():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/symbols")
async def get_symbols():
    symbols = await binance.get_futures_symbols()
    return [
        {
            "symbol": s,
            "supported": supply.supports(s),
        }
        for s in symbols
    ]


@app.get("/api/coin/{symbol}")
async def get_coin_data(symbol: str):
    symbol = symbol.upper()

    all_symbols = await binance.get_futures_symbols()
    if symbol not in all_symbols:
        raise HTTPException(status_code=404, detail=f"{symbol} Binance Futures'ta bulunamadı.")

    oi_task, ticker_task, supply_task = (
        binance.get_open_interest(symbol),
        binance.get_ticker(symbol),
        supply.get_supply(symbol),
    )

    oi_data, ticker_data, circ_supply = await asyncio.gather(oi_task, ticker_task, supply_task)

    open_interest   = oi_data["open_interest"]
    price           = ticker_data["price"]
    oi_usdt         = open_interest * price
    oi_supply_ratio = round((open_interest / circ_supply) * 100, 4) if circ_supply else None

    return {
        "symbol":             symbol,
        "price":              price,
        "change_pct":         ticker_data["change_pct"],
        "volume_usdt":        ticker_data["volume_usdt"],
        "open_interest":      open_interest,
        "open_interest_usdt": oi_usdt,
        "circulating_supply": circ_supply,
        "oi_supply_ratio":    oi_supply_ratio,
    }