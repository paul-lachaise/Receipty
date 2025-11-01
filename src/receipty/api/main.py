from fastapi import FastAPI, BackgroundTasks
from typing import List

from .db import (
    get_receipts,
)

from receipty.models.receipt_models import ReceiptDB, MessageResponse
from .LLM_processor import process_pending_receipts

app = FastAPI(
    title="Receipty API",
    description="API for processing receipts and managing data analysis.",
    version="1.0.0",
)


@app.get("/", tags=["Status"], response_model=MessageResponse)
def read_root():
    """
    Check if the API is running.

    This is a simple health check endpoint.
    """
    return {"message": "Receipty API is running."}


@app.get("/receipts", tags=["Receipts"], response_model=List[ReceiptDB])
async def get_all_receipts():
    """
    Retrieve all receipts currently stored in the database.

    This route fetches all rows from the 'receipts' table, including
    pending, processed, and failed entries.

    This is primarily for testing and debugging purposes.
    """
    return await get_receipts()


@app.post(
    "/process-receipts",
    status_code=202,
    tags=["Processing"],
    response_model=MessageResponse,
)
async def trigger_processing(background_tasks: BackgroundTasks):
    """
    Triggers the background process to analyze all pending receipts.

    This endpoint returns immediately with a '202 Accepted' status
    to indicate that the task has been queued. The actual processing
    (fetching from DB, calling LLM, updating DB) happens in the background.
    """
    print("API: Received request to process pending receipts.")

    background_tasks.add_task(process_pending_receipts)

    return {"message": "Receipt processing started in the background."}
