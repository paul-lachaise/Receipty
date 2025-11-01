from supabase import Client, create_client
from pydantic import ValidationError
from openai import AsyncOpenAI
from decimal import Decimal, ROUND_HALF_UP

from receipty.models.receipt_models import (
    StructuredReceiptData,
    Status,
    Categories,
)
from receipty.config import settings

supabase: Client = create_client(settings.supabase_url, settings.supabase_api_key)

client = AsyncOpenAI(api_key=settings.openai_api_key)


# Private Helper Functions


def _create_llm_prompt(receipt_text: str) -> str:
    """
    Creates a prompt for the OpenAI LLM to extract structured data from the given receipt text.
    The prompt provides critical rules for the LLM to follow when extracting information from the receipt text.

    Parameters
    ----------
    receipt_text : str
        The text content of the receipt to be analyzed.

    Returns
    -------
    str
        A formatted prompt string for the OpenAI LLM to extract structured data from the receipt text.
    """

    category_list = ", ".join([c.value for c in Categories])

    return f"""
    You are an expert financial assistant for French receipts.
    Your task is to extract information into a perfect JSON.

    --- CRITICAL RULES ---
    1.  **MERCHANT/DATE:** Extract 'merchant' and 'receipt_date' (YYYY-MM-DD).
    2.  **TOTAL:** Extract the final, after-discount 'TOTAL A PAYER' as the 'total_amount'.
    3.  **ITEMS:** Extract all real items. For each item:
        - Get 'name' (correct OCR errors, e.g., 'Jarnbon' -> 'Jambon').
        - Get 'quantity' (must be 1 or more).
        - Get 'line_price' (this MUST be the TOTAL PRICE for the line).
    4.  **CATEGORIES:** Assign a 'category' from this list: [{category_list}].
        - - Use your common sense and critical thinking to classify items. for example, Anything related to transport (e.g., fuel, train tickets, public transport) should be categorized as 'Transport'.
        - Do NOT default to 'Autre' unless an item is truly unclassifiable.
    5. If two items have the same or similar name but different prices, DO NOT merge them — treat them as separate items.
    6.  **IGNORE:** DO NOT extract discounts, promotions, or taxes as items.
    7.  **SELF-CORRECTION:** The sum of all 'line_price' fields you extract for items MUST *approximately* match the 'total_amount' you extracted. If they don't match, review the text again.

    Receipt Text:
    ---
    {receipt_text}
    ---
    """


async def _call_llm_api(prompt: str) -> str | None:
    """
    Calls the OpenAI LLM with the given prompt to extract structured data from a receipt.

    Parameters
    ----------
    prompt : str
        A formatted prompt string for the OpenAI LLM to extract structured data from the receipt text.

    Returns
    -------
    str | None
        A JSON string containing the structured data extracted by the LLM, or None if an error occurred.
    """

    tool_name = "save_structured_receipt"
    model_to_use = "gpt-4o-mini"

    try:
        response = await client.chat.completions.create(
            model=model_to_use,
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
            print(
                f"Successfully received structured data from OpenAI | model : {model_to_use}."
            )

            # --- AJOUT POUR LE DÉBOGAGE ---
            print("--- Raw JSON Response from LLM ---")
            print(raw_json_output)
            print("----------------------------------")
            return raw_json_output
        else:
            print(f"Error: LLM called unexpected tool: {tool_call.function.name}")
            return None

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None


def _parse_and_validate_response(raw_response: str) -> StructuredReceiptData | None:
    """
    Validates the JSON response from the LLM against the Pydantic schema
    defined in StructuredReceiptData.model_validate_json.

    Parameters
    ----------
    prompt : str
        A formatted prompt string for the OpenAI LLM to extract structured data from the receipt text.

    Returns
    -------
    StructuredReceiptData | None
        A StructuredReceiptData object if the response is valid, None otherwise.
    """

    try:
        # The response from tool calling is already a JSON string
        structured_data = StructuredReceiptData.model_validate_json(raw_response)

        print("LLM response successfully parsed and validated.")
        return structured_data
    except ValidationError as e:
        print(f"Error: LLM response did not match Pydantic schema. {e}")
        # --- AJOUT POUR LE DÉBOGAGE ---
        print("--- Raw Response from LLM was ---")
        print(raw_response)
        print("----------------------------------")
        return None


async def _update_database(receipt_id: str, data: StructuredReceiptData) -> bool:
    """
    Updates the database with the extracted structured data from the LLM.

    1. Updates the 'receipts' table with the extracted general info.
    2. Prepares the list of items for batch insertion.
    3. Inserts all items into the 'items' table.

    Parameters
    ----------
    receipt_id : str
        The ID of the receipt to be updated.
    data : StructuredReceiptData
        The extracted structured data from the LLM.

    Returns
    -------
    bool
        True if the database update was successful, False otherwise.
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
            # Python calculates the unit price reliably.
            unit_price = item.line_price / item.quantity
            items_to_insert.append(
                {
                    "receipt_id": receipt_id,
                    "name": item.name,
                    "quantity": item.quantity,
                    "price": float(
                        unit_price.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                    ),
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
    Process all pending receipts in the database by calling the LLM to extract structured data.

    This function fetches all pending receipts from the database, creates a prompt for the LLM,
    calls the LLM to extract structured data, validates the response against a Pydantic schema,
    and updates the database with the extracted data.
    """

    print("\nStarting LLM processing batch...")

    try:
        response = (
            supabase.table("receipts")
            .select("id, extracted_text")
            .eq("status", Status.PENDING.value)
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

        print(f"\nProcessing receipt ID: {receipt_id}...")

        try:
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
