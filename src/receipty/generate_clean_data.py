import sys
import random
from faker import Faker
from supabase import create_client, Client
from decimal import Decimal


try:
    from config import settings
except ImportError:
    print("Error: Could not import 'settings' from 'src.receipty.config'.")
    print("Please ensure the file exists and the path is correct.")
    sys.exit(1)

supabase: Client = create_client(settings.supabase_url, settings.supabase_api_key)
fake = Faker("fr_FR")  # Use the French locale for Faker

# SIMULATION DATA
COHERENT_ITEMS_BY_CATEGORY = {
    "Alimentation": [
        "Baguette Tradition",
        "Lait UHT 1L",
        "Camembert Président",
        "Jambon Blanc Herta",
        "Pâtes Barilla",
        "Tomates Grappe",
        "Eau Evian 1.5L",
    ],
    "Loisirs": [
        "Livre 'Dune'",
        "Jeu de société",
        "Place de cinéma UGC",
        "Album Musique",
        "Jeu Vidéo PS5",
    ],
    "Transport": [
        "Ticket de Métro",
        "Plein Essence SP98",
        "Billet de train SNCF",
        "Recharge Navigo",
    ],
    "Maison": [
        "Liquide Vaisselle",
        "Éponges Spontex",
        "Lessive Ariel",
        "Sacs Poubelle",
        "Ampoule LED",
    ],
    "Vêtements": [
        "T-shirt en coton",
        "Jean Levis 501",
        "Chaussettes",
        "Pull en laine",
        "Baskets Adidas",
    ],
    "Santé": [
        "Boîte de Paracétamol",
        "Pansements",
        "Dentifrice Signal",
        "Bain de bouche",
    ],
    "Factures": [
        "Facture EDF",
        "Facture Internet Free",
        "Facture téléphone Orange",
        "Loyer",
    ],
}
CATEGORIES = list(COHERENT_ITEMS_BY_CATEGORY.keys())
MERCHANTS = [
    "Carrefour",
    "Fnac",
    "Leclerc",
    "Amazon.fr",
    "Boulangerie",
    "TotalEnergies",
    "Pharmacie",
    "SNCF",
]
FAKE_USER_ID = "00000000-0000-0000-0000-000000000000"


def generate_clean_data(num_receipts=10):
    """
    Populates the database with clean, fake receipts and their associated items,
    ensuring the total amount of each receipt matches the sum of its items.
    """
    print("Starting clean data generation...")

    for i in range(num_receipts):
        # --- NEW LOGIC STEP 1: Generate items in memory and calculate their sum ---
        num_items = random.randint(2, 8)
        items_to_insert = []
        calculated_total = Decimal("0.0")

        for _ in range(num_items):
            item_category = random.choice(CATEGORIES)
            item_name = random.choice(COHERENT_ITEMS_BY_CATEGORY[item_category])
            price = Decimal(str(round(random.uniform(0.5, 50.0), 2)))
            quantity = random.randint(1, 5)

            calculated_total += price * quantity

            item_data = {
                # 'receipt_id' will be added later
                "name": item_name,
                "price": float(
                    price
                ),  # Convert Decimal to float for JSON serialization
                "quantity": quantity,
                "category": item_category,
            }
            items_to_insert.append(item_data)

        # --- NEW LOGIC STEP 2: Create the receipt with the calculated total ---
        receipt_data = {
            "user_id": FAKE_USER_ID,
            "merchant": random.choice(MERCHANTS),
            "receipt_date": fake.date_between(
                start_date="-1y", end_date="today"
            ).isoformat(),
            "total_amount": float(calculated_total),  # Use the calculated total
            "status": "processed",
        }

        try:
            response_receipt = supabase.table("receipts").insert(receipt_data).execute()
            new_receipt_id = response_receipt.data[0]["id"]
            print(
                f"Created receipt for '{receipt_data['merchant']}' with ID: {new_receipt_id} (Total: {calculated_total:.2f} €)"
            )
        except Exception as e:
            print(f"Error creating receipt: {e}")
            continue

        # --- NEW LOGIC STEP 3: Add the receipt_id to each item and insert them ---
        for item in items_to_insert:
            item["receipt_id"] = new_receipt_id

        try:
            supabase.table("items").insert(items_to_insert).execute()
            print(f"  -> Added {num_items} items for this receipt.")
        except Exception as e:
            print(f"Error adding items for receipt ID {new_receipt_id}: {e}")

    print("\nData generation complete!")


if __name__ == "__main__":
    print("Clearing existing tables...")
    supabase.table("items").delete().neq(
        "id", "00000000-0000-0000-0000-000000000000"
    ).execute()
    supabase.table("receipts").delete().neq(
        "id", "00000000-0000-0000-0000-000000000000"
    ).execute()

    generate_clean_data(1)

    response = supabase.table("receipts").select("id", count="exact").execute()
    count = response.count
    print(f"Total of fake clean receipts in table 'receipts': {count}")
