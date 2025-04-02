import threading
import uvicorn
from src.web.server import app
from src.core.state_manager import StateManager 
from src.services import whatsapp_api , MessageHandler
from src.core import logger
from datetime import datetime, timedelta
from src.services import obtener_citas_proximas

class ReminderService:
    def __init__(self, message_handler):
        self.message_handler : MessageHandler = message_handler
        self.check_interval = 86400  # 24 horas en segundos

    def send_reminders(self):
        """Envía recordatorios de citas programadas"""
        while True:
            try:
                citas = obtener_citas_proximas()
                if not citas:
                    logger.info("No hay citas próximas para recordatorios")
                    threading.Event().wait(self.check_interval)
                    continue

                for cita in citas:
                    if cita.confirmacionCita == "si":
                        mensaje = self.message_handler.create_reminder_message(cita)
                        numero = f"+57{cita.telefonoPaciente}"
                        if not whatsapp_api.send_message(numero, mensaje):
                            logger.error(f"Fallo enviando recordatorio a {cita.nombrePaciente}")
                        threading.Event().wait(2)  # Espera entre mensajes

                threading.Event().wait(self.check_interval)

            except Exception as e:
                logger.error(f"Error en servicio de recordatorios: {e}", exc_info=True)
                threading.Event().wait(3600)  # Espera 1 hora si hay error

def run_app():
    """Configura e inicia la aplicación"""
    # 1. Inicializar componentes principales
    state_manager = StateManager()
    message_handler = MessageHandler(state_manager)
    reminder_service = ReminderService(message_handler)

    # 2. Iniciar servicio de recordatorios en segundo plano
    reminder_thread = threading.Thread(
        target=reminder_service.send_reminders,
        daemon=True
    )
    reminder_thread.start()
    logger.info("Servicio de recordatorios iniciado")

    # 3. Iniciar servidor web
    logger.info("Iniciando servidor web en http://0.0.0.0:8000")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

if __name__ == "__main__":
    run_app()