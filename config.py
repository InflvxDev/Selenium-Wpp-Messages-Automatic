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

try: 
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    raise ConfigError(f"Error al crear el cliente de Supabase: {e}")