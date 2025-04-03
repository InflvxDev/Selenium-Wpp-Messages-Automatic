from fastapi import APIRouter, Request, Response, status
from src.core import logger, VERIFY_TOKEN, StateManager
from src.services.message_handlers import MessageHandler

router = APIRouter()

# Inicializamos las dependencias
state_manager = StateManager()
message_handler = MessageHandler(state_manager)

@router.get("/webhook")
async def verify_webhook(request: Request):
    """Endpoint de verificación para el webhook de WhatsApp"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode and token and mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook verificado correctamente")
        return Response(content=challenge, status_code=status.HTTP_200_OK)
    
    logger.error("Fallo en la verificación del webhook")
    return Response(status_code=status.HTTP_403_FORBIDDEN)

@router.post("/webhook")
async def process_webhook(request: Request):
    """Endpoint principal para procesar mensajes entrantes de WhatsApp"""
    try:
        data = await request.json()
        entry = data["entry"][0]["changes"][0]["value"]
        
        if "messages" in entry:
            message_data = entry["messages"][0]
            phone_number = message_data["from"]
            message_text = message_data["text"]["body"]
            
            logger.info(f"Mensaje recibido de {phone_number}: {message_text}")
            message_handler.process_message(phone_number, message_text)
            
    except Exception as e:
        logger.error(f"Error procesando webhook: {e}", exc_info=True)
    
    return Response(status_code=status.HTTP_200_OK)