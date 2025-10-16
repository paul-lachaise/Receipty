from supabase import Client, create_client

from ..config import settings

supabase: Client = create_client(settings.supabase_url, settings.supabase_api_key)


async def get_receipts():
    try:
        response = supabase.table("receipts").select("*").execute()
        return response.data
    except Exception as e:
        raise Exception(f"❌ Error during Supabase call: {e}")
