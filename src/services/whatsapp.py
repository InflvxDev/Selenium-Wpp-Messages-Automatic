import requests
from typing import Dict, Any
from src.core import logger, WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID

class WhatsAppAPI:

    BASE_URL = "https://graph.facebook.com/v19.0"
    DEFAULT_LANGUAGE = "es"
    
    def __init__(self): #Inicializa el cliente con los headers necesarios.
        self.headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }

    def _build_url(self, endpoint: str = "messages") -> str: #Construye la URL para la API de WhatsApp
        return f"{self.BASE_URL}/{WHATSAPP_PHONE_NUMBER_ID}/{endpoint}"
    
    def _make_request(self, payload: Dict[str, Any]) -> bool: #Realiza una peticion POST a la API de WhatsApp
        try:
            response = requests.post(self._build_url(), json=payload, headers=self.headers)
            response.raise_for_status()
            return True
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error en la petición a WhatsApp API: {e}")
            return False
    
    def send_message(self, phone_number: str, message: str) -> bool: #Envía un mensaje de texto a un número de teléfono específico.
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": "text",
            "text": {
                "body": message
            }
        }
        
        if self._make_request(payload):
            logger.info(f"Mensaje enviado a {phone_number}: {message}")
            return True
        return False
    
    def send_template_message(self, phone_number: str, template_name: str, language_code: str = DEFAULT_LANGUAGE) -> bool: #Envía un mensaje de plantilla a un número de teléfono específico.
        payload = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        return self._make_request(payload)

# Instancia global de la API
whatsapp_api = WhatsAppAPI()