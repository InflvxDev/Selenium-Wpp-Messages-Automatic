import re
from datetime import datetime, timedelta
from src.core import SesionUsuario, EstadoUsuario, Cita, StateManager 
from src.services import whatsapp_api, buscar_cita, actualizar_confirmacion_cita


class MessageHandler:
    def __init__(self, state_manager: StateManager):
        self.state = state_manager
        self.max_attempts = 3
        self.block_time = timedelta(minutes=30)
        self.ignored_groups = ["EgresadosIngSistUPC", "EspañitaSoviética"]

    def normalize_message(self, text: str) -> str:
        if not text:
            return ""
        text_no_emoji = text.encode('ascii', 'ignore').decode('ascii')
        clean_text = re.sub(r'[^\w\s]', '', text_no_emoji)
        return clean_text.lower().strip()

    def is_user_blocked(self, number: str) -> bool:
        session = self.state.sessions.get(number, SesionUsuario())
        
        if session.bloqueado_hasta and datetime.now() < session.bloqueado_hasta:
            remaining_time = session.bloqueado_hasta - datetime.now()
            minutes = int(remaining_time.total_seconds() / 60)

            if not session.ultimo_mensaje_bloqueo or \
               (datetime.now() - session.ultimo_mensaje_bloqueo).total_seconds() > 600:
                whatsapp_api.send_message(
                    number,
                    f"⏳ Has excedido el número máximo de intentos. Por favor intenta nuevamente en {minutes} minutos."
                )
                session.ultimo_mensaje_bloqueo = datetime.now()
                self.state.sessions[number] = session
                self.state.save_state()

            return True
        
        elif session.bloqueado_hasta:
            session.bloqueado_hasta = None
            session.intentos = 0
            self.state.sessions[number] = session
            
        return False

    def handle_initial_message(self, number: str, message: str):
        """Maneja el estado inicial de la conversación."""
        session = self.state.sessions.get(number, SesionUsuario())
        norm_message = self.normalize_message(message)
        
        if norm_message == "hola":
            response = ("🤖 ¡Hola! Soy *OHIBot*, tu asistente virtual. %0A%0A"
                       "¿Necesitas información sobre tu cita? Escribe *Cita* para comenzar.")
            whatsapp_api.send_message(number, response)
            session.estado = EstadoUsuario.INICIO
            session.ultimo_mensaje = self.normalize_message(response)
            
        elif norm_message == "cita" and session.estado == EstadoUsuario.INICIO:
            response = "📄 Por favor, ingresa el tipo de documento a consultar: *CC / TI / CE*"
            whatsapp_api.send_message(number, response)
            session.estado = EstadoUsuario.ESPERANDO_TIPO_DOCUMENTO
            session.ultimo_mensaje = self.normalize_message(response)
            
        self.state.sessions[number] = session
        self.state.save_state()

    def handle_document_type(self, number: str, message: str):
        """Maneja la entrada del tipo de documento."""
        if number not in self.state.sessions:
            return
            
        if self.is_user_blocked(number):
            return
            
        norm_message = self.normalize_message(message)
        session = self.state.sessions[number]
        
        # Evitar procesar repeticiones del mensaje del bot
        if session.ultimo_mensaje and norm_message == session.ultimo_mensaje.lower():
            return
            
        doc_type = norm_message.strip()
        if doc_type in ["cc", "ti", "ce"]:
            session.tipo_documento = doc_type.upper()
            session.estado = EstadoUsuario.ESPERANDO_NUMERO_DOCUMENTO
            session.intentos = 0
            response = "🔢 Ahora, por favor ingresa tu número de documento (sin puntos ni espacios):"
            whatsapp_api.send_message(number, response)
            session.ultimo_mensaje = self.normalize_message(response)
        else:
            if not session.ultimo_mensaje or "error tipo documento" not in session.ultimo_mensaje.lower():
                session.intentos += 1
                
            if session.intentos >= self.max_attempts:
                session.bloqueado_hasta = datetime.now() + self.block_time
                response = "⏳ Has excedido el número máximo de intentos. Por favor intenta nuevamente más tarde."
            else:
                response = "❌ El tipo de documento ingresado no es válido. Inténtalo de nuevo (CC / TI / CE)."
                
            whatsapp_api.send_message(number, response)
            session.ultimo_mensaje = self.normalize_message(response)
            
        self.state.sessions[number] = session
        self.state.save_state()

    def handle_document_number(self, number: str, message: str):
        """Maneja la entrada del número de documento."""
        if number not in self.state.sessions or not self.state.sessions[number].tipo_documento:
            return
            
        if self.is_user_blocked(number):
            return
            
        norm_message = self.normalize_message(message)
        session = self.state.sessions[number]
        
        if session.ultimo_mensaje and norm_message == session.ultimo_mensaje.lower():
            return
            
        if norm_message.isdigit():
            cita = buscar_cita(session.tipo_documento, norm_message)
            session.cita_actual = cita
            session.intentos = 0
            
            if cita:
                if not cita.confirmacionCita:
                    response = (
                        f"📅 *Cita encontrada:* %0A%0A"
                        f"📝 *Documento Paciente:* {cita.tipoDocumento} {cita.documento}%0A"
                        f"👨 *Nombre Paciente:* {cita.nombrePaciente}%0A"
                        f"👨‍⚕️ *Médico:* {cita.nombreMedico}%0A"
                        f"🏥 *Especialidad:* {cita.especialidad}%0A"
                        f"🗓 *Fecha:* {cita.fechaCita}%0A%0A"
                        f"✅ ¿Asistirás a la cita? Responde con *si* o *no*."
                    )
                    session.estado = EstadoUsuario.ESPERANDO_CONFIRMACION
                else:
                    response = (
                        f"⚠ *Tu cita ya fue confirmada.* Te muestro los detalles: %0A%0A"
                        f"📝 *Documento Paciente:* {cita.tipoDocumento} {cita.documento}%0A"
                        f"👨 *Nombre Paciente:* {cita.nombrePaciente}%0A"
                        f"👨‍⚕️ *Médico:* {cita.nombreMedico}%0A"
                        f"🏥 *Especialidad:* {cita.especialidad}%0A"
                        f"🗓 *Fecha:* {cita.fechaCita}%0A"
                        f"📌 *Asistencia:* {cita.confirmacionCita}%0A%0A"
                        f"Si deseas otra consulta, escribe: *Cita*"
                    )
                    session.estado = EstadoUsuario.INICIO
            else:
                response = "⚠ No encontré ninguna cita con ese documento. Si deseas intentar otra consulta, escribe: *Cita*"
                session.estado = EstadoUsuario.INICIO
                
            whatsapp_api.send_message(number, response)
        else:
            if not session.ultimo_mensaje or "error número documento" not in session.ultimo_mensaje.lower():
                session.intentos += 1
                
            if session.intentos >= self.max_attempts:
                session.bloqueado_hasta = datetime.now() + self.block_time
                response = "⏳ Has excedido el número máximo de intentos. Por favor intenta nuevamente más tarde."
            else:
                response = "❌ El número de documento ingresado no es válido. Inténtalo de nuevo (solo números)."
                
            whatsapp_api.send_message(number, response)
            session.ultimo_mensaje = self.normalize_message(response)
            
        self.state.sessions[number] = session
        self.state.save_state()

    def handle_confirmation(self, number: str, message: str):
        """Maneja la confirmación de asistencia a la cita."""
        if number not in self.state.sessions or not self.state.sessions[number].cita_actual:
            return
            
        norm_message = self.normalize_message(message)
        session = self.state.sessions[number]
        
        if session.ultimo_mensaje and norm_message == session.ultimo_mensaje.lower():
            return
            
        response = norm_message.strip()
        if response in ["si", "no"]:
            if actualizar_confirmacion_cita(session.cita_actual.documento, response):
                if response == "si":
                    msg = (
                        f"✅ ¡Genial! Te esperamos el *{session.cita_actual.fechaCita}* "
                        f"para tu cita programada. Si necesitas otra consulta, escribe: *Cita*."
                    )
                else:
                    msg = "👍 Entendido. Si deseas otra consulta, escribe: *Cita*."
                whatsapp_api.send_message(number, msg)
            else:
                whatsapp_api.send_message(
                    number,
                    "❌ Hubo un error al actualizar tu confirmación. Por favor intenta nuevamente más tarde."
                )
            session.estado = EstadoUsuario.INICIO
            session.cita_actual = None
        else:
            if not session.ultimo_mensaje or "error confirmación" not in session.ultimo_mensaje.lower():
                session.intentos += 1
                
            if session.intentos >= self.max_attempts:
                session.bloqueado_hasta = datetime.now() + self.block_time
                msg = "⏳ Has excedido el número máximo de intentos. Por favor intenta nuevamente más tarde."
            else:
                msg = "❓ Por favor, responde con *si* o *no*."
                
            whatsapp_api.send_message(number, msg)
            session.ultimo_mensaje = self.normalize_message(response)
            
        self.state.sessions[number] = session
        self.state.save_state()

    def process_message(self, number: str, message: str):
        """Procesa el mensaje según el estado actual del usuario."""
        if not number or not message:
            return
            
        session = self.state.sessions.get(number, SesionUsuario())
        session.ultima_interaccion = datetime.now()
        
        if session.estado == EstadoUsuario.INICIO:
            self.handle_initial_message(number, message)
        elif session.estado == EstadoUsuario.ESPERANDO_TIPO_DOCUMENTO:
            self.handle_document_type(number, message)
        elif session.estado == EstadoUsuario.ESPERANDO_NUMERO_DOCUMENTO:
            self.handle_document_number(number, message)
        elif session.estado == EstadoUsuario.ESPERANDO_CONFIRMACION:
            self.handle_confirmation(number, message)
            
        self.state.sessions[number] = session
        self.state.save_state()

    def create_reminder_message(self, cita: Cita) -> str:
        """Genera el mensaje de recordatorio de cita."""
        return (
            f"📅 *Recordatorio de Cita Médica*%0A%0A"
            f"Hola {cita.nombrePaciente}, este es un recordatorio de tu cita médica.%0A"
            f"🏥 *Especialidad:* {cita.especialidad}%0A"
            f"👨‍⚕️ *Médico:* {cita.nombreMedico}%0A"
            f"📅 *Fecha:* {cita.fechaCita}%0A%0A"
            f"Por favor llega 15 minutos antes de tu hora programada."
        )