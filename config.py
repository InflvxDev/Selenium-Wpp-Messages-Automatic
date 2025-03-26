import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Error: SUPABASE_URL o SUPABASE_KEY no están configuradas correctamente.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)