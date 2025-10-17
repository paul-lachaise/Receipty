import sys
import random
from faker import Faker
from supabase import create_client, Client
from decimal import Decimal, ROUND_HALF_UP

try:
    from config import settings
except ImportError:
    print("Error: Could not import 'settings' from 'config.py'.")
    print("Please ensure the file exists.")
    sys.exit(1)

supabase: Client = create_client(settings.supabase_url, settings.supabase_api_key)
fake = Faker("fr_FR")

# ADVANCED SIMULATION DATA
COHERENT_ITEMS_BY_CATEGORY = {
    "Alimentation": [
        "Baguette Tradition",
        "Lait UHT 1L",
        "Camembert Président",
        "Jambon Blanc",
        "Pâtes Barilla",
    ],
    "Loisirs": ["Livre 'Dune'", "Jeu de société", "Place de cinéma", "Jeu Vidéo PS5"],
    "Transport": ["Plein Essence SP98", "Billet de train SNCF", "Ticket de Métro"],
    "Maison": ["Liquide Vaisselle", "Éponges Spontex", "Lessive Ariel"],
    "Santé": ["Boîte de Paracétamol", "Pansements", "Dentifrice"],
}

TEMPLATE_CONFIG = {
    "supermarket": {
        "merchants": ["Carrefour", "Leclerc", "Auchan"],
        "categories": ["Alimentation", "Maison", "Santé"],
    },
    "gas_station": {
        "merchants": ["TotalEnergies", "Esso"],
        "categories": ["Transport"],
    },
    "generic_store": {
        "merchants": ["Fnac", "Pharmacie", "Boulangerie", "SNCF"],
        "categories": ["Loisirs", "Santé", "Alimentation", "Transport"],
    },
}

FAKE_USER_ID = "00000000-0000-0000-0000-000000000000"
VAT_RATE = Decimal("0.20")  # Define a 20% VAT rate


def _generate_receipt_items(allowed_categories):
    """
    Generates a list of item lines and calculates the total amount based on allowed categories.
    Returns a tuple containing the formatted text of the items and their total sum.

    Parameters
    ----------
    allowed_categories : list[str]
        A list of category names from which to randomly select items.

    Returns
    -------
    tuple[str, Decimal]
        A tuple containing two elements:
        1. The formatted multi-line string of all item lines.
        2. The calculated total amount as a Decimal object.
    """
    items_text = ""
    total_amount = Decimal("0.0")
    num_items = random.randint(2, 5)

    for _ in range(num_items):
        category = random.choice(allowed_categories)
        item_name = random.choice(COHERENT_ITEMS_BY_CATEGORY[category])
        quantity = random.randint(1, 3)
        price = Decimal(str(round(random.uniform(1.5, 45.0), 2)))
        line_total = price * quantity
        total_amount += line_total

        item_line = f"{quantity} x {item_name:<20}"
        items_text += f"{item_line:<25} {f'{line_total:.2f} EUR'}\n"

    return items_text, total_amount


def generate_receipt_text():
    """
    Randomly selects a template and generates a complete, realistic receipt text.

    This function simulates the output of an Optical Character Recognition (OCR)
    process on a French receipt by building a multi-line string with a random
    merchant, items, and a calculated total including VAT.

    Returns
    -------
    str
        A multi-line string simulating the raw text content of a French receipt.
    """
    template_type = random.choice(list(TEMPLATE_CONFIG.keys()))

    config = TEMPLATE_CONFIG[template_type]
    merchant = random.choice(config["merchants"])
    allowed_categories = config["categories"]

    date_str = fake.date_this_year().strftime("%d/%m/%Y")
    time_str = fake.time(pattern="%H:%M:%S")

    items_text, total_amount = _generate_receipt_items(allowed_categories)

    vat_amount = (total_amount * VAT_RATE).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    text_block = f"{merchant.upper()}\n"
    if template_type == "supermarket":
        text_block += (
            f"{fake.street_address()}\n{fake.postcode()} {fake.city().upper()}\n"
        )

    text_block += f"\nDate: {date_str}   Heure: {time_str}\n"
    text_block += "--------------------------------------\n"
    text_block += items_text
    text_block += "--------------------------------------\n"

    if template_type != "gas_station":
        text_block += f"SOUS-TOTAL                 {f'{total_amount:.2f} EUR'}\n"
        text_block += (
            f"DONT TVA ({VAT_RATE:.0%})             {f'{vat_amount:.2f} EUR'}\n"
        )

    text_block += f"TOTAL A PAYER              {f'{total_amount:.2f} EUR'}\n\n"
    text_block += "MERCI DE VOTRE VISITE\n"

    return text_block


def simulate_ocr_insertion(num_receipts=5):
    """
    Inserts a specified number of raw, OCR-like text records into the 'receipts' table.

    This function simulates the initial data ingestion step where raw text from an
    OCR process is stored. For each receipt, it calls `generate_receipt_text()`
    to create a text block and then inserts a new row into the database. It populates
    only the essential fields ('user_id', 'extracted_text', 'status') to prepare
    the record for subsequent processing by an LLM.

    Parameters
    ----------
    num_receipts : int, optional
        The number of raw receipt records to generate and insert. Defaults to 5.

    Returns
    -------
    None
        This function does not return any value; it prints its progress to the console.
    """
    print("Starting OCR input simulation...")
    for i in range(num_receipts):
        ocr_text = generate_receipt_text()
        receipt_to_insert = {
            "user_id": FAKE_USER_ID,
            "extracted_text": ocr_text,
            "status": "pending",
        }
        try:
            response = supabase.table("receipts").insert(receipt_to_insert).execute()
            new_id = response.data[0]["id"]
            print(f"Successfully inserted raw receipt. ID: {new_id}")
        except Exception as e:
            print(f"Error inserting raw receipt: {e}")


if __name__ == "__main__":
    print("add new data to existing tables...")

    simulate_ocr_insertion(5)

    response = supabase.table("receipts").select("id", count="exact").execute()
    count = response.count
    print(f"Total of fake clean receipts in table 'receipts': {count}")
