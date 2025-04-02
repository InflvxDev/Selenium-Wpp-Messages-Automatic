import requests
from config import logger, WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID

class WhatsAppAPI:
    BASE_URL = "https://graph.facebook.com/v19.0"
    
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {WHATSAPP_TOKEN}",
            "Content-Type": "application/json"
        }
    
    def send_message(self, phone_number: str, message: str) -> bool:
        """Envía un mensaje a través de WhatsApp Business API"""
        url = f"{self.BASE_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_number,
            "type": "text",
            "text": {
                "body": message
            }
        }
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            logger.info(f"Mensaje enviado a {phone_number}")
            return True
        except Exception as e:
            logger.error(f"Error al enviar mensaje: {e}")
            return False
    
    def send_template_message(self, phone_number: str, template_name: str, language_code: str = "es") -> bool:
        """Envía un mensaje de plantilla"""
        url = f"{self.BASE_URL}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
        
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
        
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Error al enviar plantilla: {e}")
            return False

# Instancia global de la API
whatsapp_api = WhatsAppAPI()