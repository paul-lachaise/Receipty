from supabase import Client, create_client

from receipty.config import settings

supabase: Client = create_client(settings.supabase_url, settings.supabase_api_key)


async def fetch_pending_receipts():
    try:
        reponse = (
            supabase.table("receipts").select("*").eq("status", "pending").execute()
        )
        return reponse.data
    except Exception as e:
        raise Exception(f"❌ Error during Supabase call: {e}")
