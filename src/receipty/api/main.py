from fastapi import FastAPI, BackgroundTasks

from .db import (
    get_receipts,
)

from .LLM_processor import process_pending_receipts

app = FastAPI()


@app.get("/receipts")
async def get_all_receipts():
    return await get_receipts()


@app.get("/", tags=["Status"])
def read_root():
    """Check if the API is running."""
    return {"message": "Receipty API is running."}


@app.post("/process-receipts", status_code=202, tags=["Processing"])
async def trigger_processing(background_tasks: BackgroundTasks):
    """
    Triggers the background process to analyze all pending receipts.
    This endpoint returns immediately (202 Accepted) and does the work
    in the background.
    """
    print("API: Received request to process pending receipts.")

    # This is the key line:
    # It adds your async function to FastAPI's background tasks.
    # FastAPI will 'await' it for you in the background.
    background_tasks.add_task(process_pending_receipts)

    return {"message": "Receipt processing started in the background."}
