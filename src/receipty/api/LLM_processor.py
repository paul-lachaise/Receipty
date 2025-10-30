from supabase import Client, create_client
from pydantic import ValidationError
from openai import AsyncOpenAI

from receipty.models.receipt_models import (
    StructuredReceiptData,
    Status,
    Categories,
)
from receipty.config import settings

# Initialize the Supabase client
supabase: Client = create_client(settings.supabase_url, settings.supabase_api_key)

# Initialize the OpenAI client
client = AsyncOpenAI(api_key=settings.openai_api_key)


# Private Helper Functions


def _create_llm_prompt(receipt_text: str) -> str:
    """
    Creates a simple analysis prompt for the LLM.
    The structure is defined by the 'tool' capability.
    """
    category_list = ", ".join([c.value for c in Categories])

    return f"""
    Analyze the following raw OCR text from a French receipt.
    Extract the merchant, date (YYYY-MM-DD), total amount, and all items.
    Assign a category to each item from this list: [{category_list}].

    Receipt Text:
    ---
    {receipt_text}
    ---
    """


async def _call_llm_api(prompt: str) -> str | None:
    """
    Calls the OpenAI API using Tool Calling to get structured data.
    """
    tool_name = "save_structured_receipt"
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": "Saves the extracted receipt data.",
                        # Pass the Pydantic schema directly to OpenAI
                        "parameters": StructuredReceiptData.model_json_schema(),
                    },
                }
            ],
            # Force the model to use our tool define with Pydantic
            tool_choice={"type": "function", "function": {"name": tool_name}},
        )

        # Extract the JSON string from the tool call arguments
        tool_call = response.choices[0].message.tool_calls[0]
        if tool_call.function.name == tool_name:
            raw_json_output = tool_call.function.arguments
            print("Successfully received structured data from OpenAI.")
            return raw_json_output
        else:
            print(f"Error: LLM called unexpected tool: {tool_call.function.name}")
            return None

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None


def _parse_and_validate_response(raw_response: str) -> StructuredReceiptData | None:
    """
    Parses the raw JSON string from the LLM and validates it against the Pydantic model.
    """
    try:
        # The response from tool calling is already a JSON string
        structured_data = StructuredReceiptData.model_validate_json(raw_response)

        print("LLM response successfully parsed and validated.")
        return structured_data
    except ValidationError as e:
        print(f"Error: LLM response did not match Pydantic schema. {e}")
        print(f"Raw response was: {raw_response}")
        return None


async def _update_database(receipt_id: str, data: StructuredReceiptData) -> bool:
    """
    Updates the 'receipts' table and inserts new 'items' into the database.
    """
    try:
        # 1. Update the 'receipts' table with the extracted general info
        update_data = {
            "merchant": data.merchant,
            "receipt_date": data.receipt_date.isoformat(),
            "total_amount": float(data.total_amount),
            "status": Status.PROCESSED,
        }
        supabase.table("receipts").update(update_data).eq("id", receipt_id).execute()

        # 2. Prepare the list of items for batch insertion
        items_to_insert = []
        for item in data.items:
            items_to_insert.append(
                {
                    "receipt_id": receipt_id,
                    "name": item.name,
                    "quantity": item.quantity,
                    "price": float(item.price),
                    "category": item.category.value,
                }
            )

        # 3. Insert all items into the 'items' table
        if items_to_insert:
            supabase.table("items").insert(items_to_insert).execute()

        print(f"Successfully processed and saved data for receipt ID: {receipt_id}")
        return True

    except Exception as e:
        print(f"Database error while updating receipt {receipt_id}: {e}")
        # Rollback status to 'failed'
        supabase.table("receipts").update({"status": Status.FAILED}).eq(
            "id", receipt_id
        ).execute()
        return False


# Public Main Function


async def process_pending_receipts():
    """
    Orchestrator function:
    1. Fetches pending receipts.
    2. Processes each one through the LLM.
    3. Updates the database with the results.
    """
    print("Starting LLM processing batch...")

    try:
        response = (
            supabase.table("receipts")
            .select("id, extracted_text")
            .eq("status", Status.PENDING)
            .execute()
        )
        pending_receipts = response.data
    except Exception as e:
        print(f"Error fetching pending receipts: {e}")
        return

    if not pending_receipts:
        print(f"No pending receipts found : {pending_receipts}")
        return

    print(f"Found {len(pending_receipts)} receipts to process.")
    processed_count = 0

    for receipt in pending_receipts:
        receipt_id = receipt["id"]
        text = receipt["extracted_text"]

        print(f"Processing receipt ID: {receipt_id}...")

        try:
            # Mark as 'processing' to prevent other workers from grabbing it
            supabase.table("receipts").update({"status": Status.PROCESSING}).eq(
                "id", receipt_id
            ).execute()

            # 1. Create Prompt
            prompt = _create_llm_prompt(text)

            # 2. Call LLM
            raw_response = await _call_llm_api(prompt)
            if not raw_response:
                raise ValueError("LLM API call failed or returned empty response.")

            # 3. Validate Response
            structured_data = _parse_and_validate_response(raw_response)
            if not structured_data:
                raise ValueError("LLM response failed Pydantic validation.")

            # 4. Update Database
            success = await _update_database(receipt_id, structured_data)
            if success:
                processed_count += 1

        except Exception as e:
            print(f"Failed to process receipt {receipt_id}: {e}")
            # Mark as 'failed' if any step in the try block fails
            supabase.table("receipts").update({"status": Status.FAILED}).eq(
                "id", receipt_id
            ).execute()

    print(
        f"LLM processing batch finished. Successfully processed {processed_count}/{len(pending_receipts)} receipts."
    )
