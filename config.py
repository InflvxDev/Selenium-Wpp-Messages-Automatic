import os
from supabase import create_client
from dotenv import load_dotenv
import logging
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class ConfigError(Exception):
    pass

def validate_supabase_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except Exception:
        return False

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ConfigError("Error: SUPABASE_URL o SUPABASE_KEY no están configuradas. en el archivo .env")

if not validate_supabase_url(SUPABASE_URL):
    raise ConfigError("Error: SUPABASE_URL no es una URL válida.")

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_BUISNESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUISNESS_ACCOUNT_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

if not WHATSAPP_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
    raise ConfigError("Error: se requieren WHATSAPP_TOKEN y WHATSAPP_PHONE_NUMBER_ID en el archivo .env")


try: 
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    raise ConfigError(f"Error al crear el cliente de Supabase: {e}")