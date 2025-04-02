import os
from urllib.parse import urlparse
from typing import Optional
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

def setup_logging() -> logging.Logger:  # Configuración básica del logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    return logging.getLogger(__name__)

logger = setup_logging()
load_dotenv()

class ConfigError(Exception):
    pass

def validate_supabase_url(url: str) -> bool: #Valida que una URL tenga el formato correcto.
    try:
        parsed = urlparse(url)
        return all([parsed.scheme in ['http', 'https'], parsed.netloc])
    except Exception as e:
        logger.error(f"Error validando Url: {e}")
        return False

def get_required_env_var(var_name: str) -> str: #Valida que la variable de entorno requerida.
    value = os.getenv(var_name)
    if value is None:
        logger.error(f"Error: la variable de entorno {var_name} no está configurada.")
    return value

# Configuración de Supabase
SUPABASE_URL = get_required_env_var("SUPABASE_URL")
SUPABASE_KEY = get_required_env_var("SUPABASE_KEY")

if not validate_supabase_url(SUPABASE_URL):
    raise ConfigError("Error: SUPABASE_URL no es una URL válida.")

# Configuración de WhatsApp
WHATSAPP_TOKEN = get_required_env_var("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = get_required_env_var("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID") #opcional
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN") #opcional

def create_supabase_client(url: str, key: str) -> Client: #Creacion Cliente Supabase
    try: 
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Error creando cliente de Supabase: {e}")
        raise ConfigError(f"No se pudo inicializar Supabase: {e}")

supabase : Client = create_supabase_client(SUPABASE_URL, SUPABASE_KEY)