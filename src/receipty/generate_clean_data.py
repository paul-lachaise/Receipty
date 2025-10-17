import sys
import random
from faker import Faker
from supabase import create_client, Client


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
    Populates the database with clean, fake receipts and their associated items.

    This function serves as a utility to create a complete and structured dataset
    for demonstration or testing purposes. It generates a specified number of
    parent 'receipt' records with all fields populated (e.g., merchant, total_amount),
    simulating a fully processed state. For each receipt, it also generates
    a random number of corresponding 'item' records with coherent names and categories.

    Parameters
    ----------
    num_receipts : int, optional
        The number of complete receipt records to generate. Defaults to 10.

    Returns
    -------
    None
        This function does not return any value. Its primary effects are
        database mutations and printing progress to the console.
    """
    print("Starting clean data generation...")

    for i in range(num_receipts):
        receipt_data = {
            "user_id": FAKE_USER_ID,
            "merchant": random.choice(MERCHANTS),
            "receipt_date": fake.date_between(
                start_date="-1y", end_date="today"
            ).isoformat(),
            "total_amount": round(random.uniform(5.0, 300.0), 2),
            "status": "processed",
        }

        try:
            response_receipt = supabase.table("receipts").insert(receipt_data).execute()
            new_receipt_id = response_receipt.data[0]["id"]
            print(
                f"Created receipt for '{receipt_data['merchant']}' with ID: {new_receipt_id}"
            )
        except Exception as e:
            print(f"Error creating receipt: {e}")
            continue

        num_items = random.randint(2, 8)
        items_to_insert = []
        for _ in range(num_items):
            item_category = random.choice(CATEGORIES)
            item_name = random.choice(COHERENT_ITEMS_BY_CATEGORY[item_category])
            item_data = {
                "receipt_id": new_receipt_id,
                "name": item_name,
                "price": round(random.uniform(0.5, 50.0), 2),
                "quantity": random.randint(1, 5),
                "category": item_category,
            }
            items_to_insert.append(item_data)

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

    generate_clean_data(10)

    response = supabase.table("receipts").select("id", count="exact").execute()
    count = response.count
    print(f"Total of fake clean receipts in table 'receipts': {count}")
