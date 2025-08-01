from fastapi import FastAPI

from db import (
    get_receipts,
)

app = FastAPI()

@app.get("/receipts")
async def get_all_receipts():
    return await get_receipts()
