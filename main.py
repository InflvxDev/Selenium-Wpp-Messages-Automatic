import json
import threading
import re
from typing import Dict, Optional
from enum import Enum, auto
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from fastapi import FastAPI, Request, Response, status
from pydantic import BaseModel
import uvicorn
from whatsapp import whatsapp_api
from database import buscar_cita, actualizar_confirmacion_cita, obtener_citas_proximas, Cita
from config import logger, VERIFY_TOKEN

app = FastAPI()

class EstadoUsuario(Enum):
    INICIO = auto()
    ESPERANDO_TIPO_DOCUMENTO = auto()
    ESPERANDO_NUMERO_DOCUMENTO = auto()
    ESPERANDO_CONFIRMACION = auto()
    CITA_ENCONTRADA = auto()

@dataclass
class SesionUsuario:
    estado: EstadoUsuario = EstadoUsuario.INICIO
    intentos: int = 0
    cita_actual: Optional[Cita] = None
    ultimo_mensaje: Optional[str] = None
    ultimo_mensaje_bloqueo: Optional[datetime] = None 
    tipo_documento: Optional[str] = None
    ultima_interaccion: datetime = datetime.now()
    bloqueado_hasta: Optional[datetime] = None

class WhatsAppMessage(BaseModel):
    from_num: str
    message: str
    timestamp: datetime

class OHIBot:
    def __init__(self):
        self.estado_usuarios: Dict[str, SesionUsuario] = {}
        self.cargar_estado()
        self.grupos_ignorados = ["EgresadosIngSistUPC", "EspañitaSoviética"]
        self.max_intentos = 3
        self.tiempo_bloqueo = timedelta(minutes=30)

    def cargar_estado(self):
        try:
            with open("estado_usuarios.json", "r") as f:
                data = json.load(f)
                for numero, sesion_data in data.items():
                    bloqueado_hasta = (
                        datetime.fromisoformat(sesion_data["bloqueado_hasta"]) 
                        if sesion_data.get("bloqueado_hasta") 
                        else None
                    )
                    self.estado_usuarios[numero] = SesionUsuario(
                        estado=EstadoUsuario[sesion_data["estado"]],
                        intentos=sesion_data["intentos"],
                        tipo_documento=sesion_data.get("tipo_documento"),
                        ultimo_mensaje=sesion_data.get("ultimo_mensaje"),
                        ultima_interaccion=datetime.fromisoformat(sesion_data["ultima_interaccion"]),
                        bloqueado_hasta=bloqueado_hasta,
                        cita_actual=Cita(**sesion_data["cita_actual"]) if sesion_data.get("cita_actual") else None
                    )
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            logger.warning(f"No se pudo cargar el estado: {e}")
            self.estado_usuarios = {}

    def guardar_estado(self):
        estado_serializable = {}
        for numero, sesion in self.estado_usuarios.items():
            estado_serializable[numero] = {
                "estado": sesion.estado.name,
                "intentos": sesion.intentos,
                "tipo_documento": sesion.tipo_documento,
                "ultimo_mensaje": sesion.ultimo_mensaje,
                "ultima_interaccion": sesion.ultima_interaccion.isoformat(),
                "bloqueado_hasta": sesion.bloqueado_hasta.isoformat() if sesion.bloqueado_hasta else None,
                "cita_actual": sesion.cita_actual.model_dump() if sesion.cita_actual else None
            }
        try:
            with open("estado_usuarios.json", "w") as f:
                json.dump(estado_serializable, f, indent=2)
        except Exception as e:
            logger.error(f"Error al guardar estado: {e}")

    def usuario_bloqueado(self, numero: str) -> bool:
        """Verifica si el usuario está temporalmente bloqueado."""
        sesion = self.estado_usuarios.get(numero, SesionUsuario())
        if sesion.bloqueado_hasta and datetime.now() < sesion.bloqueado_hasta:
            tiempo_restante = sesion.bloqueado_hasta - datetime.now()
            minutos = int(tiempo_restante.total_seconds() / 60)

            ultimo_mensaje_bloqueo = getattr(sesion, "ultimo_mensaje_bloqueo", None)
            if not ultimo_mensaje_bloqueo or (datetime.now() - ultimo_mensaje_bloqueo).total_seconds() > 600:
                whatsapp_api.send_message(
                    numero,
                    f"⏳ Has excedido el número máximo de intentos. Por favor intenta nuevamente en {minutos} minutos."
                )
                sesion.ultimo_mensaje_bloqueo = datetime.now()
                self.estado_usuarios[numero] = sesion
                self.guardar_estado()

            return True
        elif sesion.bloqueado_hasta:
            sesion.bloqueado_hasta = None
            sesion.intentos = 0
            self.estado_usuarios[numero] = sesion
        return False
    
    def normalizar_mensaje(self, texto: str) -> str:
        """Normaliza el texto removiendo emojis, caracteres especiales y convirtiendo a minúsculas."""
        if not texto:
            return ""
        
        # Remover emojis
        texto_sin_emojis = texto.encode('ascii', 'ignore').decode('ascii')
        
        # Remover caracteres especiales (conservando letras, números y espacios)
        texto_limpio = re.sub(r'[^\w\s]', '', texto_sin_emojis)
        
        # Convertir a minúsculas y quitar espacios extras
        texto_normalizado = texto_limpio.lower().strip()
        
        return texto_normalizado

    def manejar_mensaje_inicio(self, numero: str, mensaje: str):
        """Maneja el estado INICIO de la conversación."""
        sesion = self.estado_usuarios.get(numero, SesionUsuario())
        
        if mensaje.lower() == "hola":
            respuesta = ("🤖 ¡Hola! Soy *OHIBot*, tu asistente virtual. %0A%0A"
                       "¿Necesitas información sobre tu cita? Escribe *Cita* para comenzar.")
            whatsapp_api.send_message(numero, respuesta)
            sesion.estado = EstadoUsuario.INICIO
            sesion.ultimo_mensaje = self.normalizar_mensaje(respuesta)
        
        elif mensaje.lower() == "cita" and sesion.estado == EstadoUsuario.INICIO:
            respuesta = "📄 Por favor, ingresa el tipo de documento a consultar: *CC / TI / CE*"
            whatsapp_api.send_message(numero, respuesta)
            sesion.estado = EstadoUsuario.ESPERANDO_TIPO_DOCUMENTO
            sesion.ultimo_mensaje = self.normalizar_mensaje(respuesta)
        
        self.estado_usuarios[numero] = sesion
        self.guardar_estado()

    def manejar_tipo_documento(self, numero: str, mensaje: str):
        """Maneja la entrada del tipo de documento con verificación de repetición."""
        sesion = self.estado_usuarios.get(numero)
        if not sesion:
            return

        if self.usuario_bloqueado(numero):
            return
        
        mensaje = self.normalizar_mensaje(mensaje)
        if (sesion.ultimo_mensaje and 
            mensaje.strip().lower() == sesion.ultimo_mensaje.lower()):
            return
        
        tipo_doc = mensaje.lower().strip()
        if tipo_doc in ["cc", "ti", "ce"]:
            sesion.tipo_documento = tipo_doc.upper()
            sesion.estado = EstadoUsuario.ESPERANDO_NUMERO_DOCUMENTO
            sesion.intentos = 0
            respuesta = "🔢 Ahora, por favor ingresa tu número de documento (sin puntos ni espacios):"
            whatsapp_api.send_message(numero, respuesta)
            sesion.ultimo_mensaje = self.normalizar_mensaje(respuesta)

        else:
            if not sesion.ultimo_mensaje or "error tipo documento" not in sesion.ultimo_mensaje.lower():
                sesion.intentos += 1
            
            if sesion.intentos >= self.max_intentos:
                sesion.bloqueado_hasta = datetime.now() + self.tiempo_bloqueo
                respuesta = "⏳ Has excedido el número máximo de intentos. Por favor intenta nuevamente más tarde."
            else:
                respuesta = "❌ El tipo de documento ingresado no es válido. Inténtalo de nuevo (CC / TI / CE)."
            
            whatsapp_api.send_message(numero, respuesta)
            sesion.ultimo_mensaje = self.normalizar_mensaje(respuesta)

        self.estado_usuarios[numero] = sesion
        self.guardar_estado()

    def manejar_numero_documento(self, numero: str, mensaje: str):
        """Maneja la entrada del número de documento con verificación de repetición."""
        sesion = self.estado_usuarios.get(numero)
        if not sesion or not sesion.tipo_documento:
            return

        if self.usuario_bloqueado(numero):
            return
        
        mensaje = self.normalizar_mensaje(mensaje)
        if (sesion.ultimo_mensaje and 
            mensaje.strip().lower() == sesion.ultimo_mensaje.lower()):
            return

        if mensaje.isdigit():
            cita = buscar_cita(sesion.tipo_documento, mensaje)
            sesion.cita_actual = cita
            sesion.intentos = 0
            
            if cita:
                if not cita.confirmacionCita:
                    respuesta = (
                        f"📅 *Cita encontrada:* %0A%0A"
                        f"📝 *Documento Paciente:* {cita.tipoDocumento} {cita.documento}%0A"
                        f"👨 *Nombre Paciente:* {cita.nombrePaciente}%0A"
                        f"👨‍⚕️ *Médico:* {cita.nombreMedico}%0A"
                        f"🏥 *Especialidad:* {cita.especialidad}%0A"
                        f"🗓 *Fecha:* {cita.fechaCita}%0A%0A"
                        f"✅ ¿Asistirás a la cita? Responde con *si* o *no*."
                    )
                    sesion.estado = EstadoUsuario.ESPERANDO_CONFIRMACION
                else:
                    respuesta = (
                        f"⚠ *Tu cita ya fue confirmada.* Te muestro los detalles: %0A%0A"
                        f"📝 *Documento Paciente:* {cita.tipoDocumento} {cita.documento}%0A"
                        f"👨 *Nombre Paciente:* {cita.nombrePaciente}%0A"
                        f"👨‍⚕️ *Médico:* {cita.nombreMedico}%0A"
                        f"🏥 *Especialidad:* {cita.especialidad}%0A"
                        f"🗓 *Fecha:* {cita.fechaCita}%0A"
                        f"📌 *Asistencia:* {cita.confirmacionCita}%0A%0A"
                        f"Si deseas otra consulta, escribe: *Cita*"
                    )
                    sesion.estado = EstadoUsuario.INICIO
            else:
                respuesta = "⚠ No encontré ninguna cita con ese documento. Si deseas intentar otra consulta, escribe: *Cita*"
                sesion.estado = EstadoUsuario.INICIO
            
            whatsapp_api.send_message(numero, respuesta)
        else:
            if not sesion.ultimo_mensaje or "error número documento" not in sesion.ultimo_mensaje.lower():
                sesion.intentos += 1
            
            if sesion.intentos >= self.max_intentos:
                sesion.bloqueado_hasta = datetime.now() + self.tiempo_bloqueo
                respuesta = "⏳ Has excedido el número máximo de intentos. Por favor intenta nuevamente más tarde."
            else:
                respuesta = "❌ El número de documento ingresado no es válido. Inténtalo de nuevo (solo números)."
            
            whatsapp_api.send_message(numero, respuesta)
            sesion.ultimo_mensaje = self.normalizar_mensaje(respuesta)
            
        self.estado_usuarios[numero] = sesion
        self.guardar_estado()

    def manejar_confirmacion(self, numero: str, mensaje: str):
        """Maneja la confirmación de asistencia a la cita con verificación de repetición."""
        sesion = self.estado_usuarios.get(numero)
        if not sesion or not sesion.cita_actual:
            return
        
        mensaje = self.normalizar_mensaje(mensaje)
        if (sesion.ultimo_mensaje and 
            mensaje.strip().lower() == sesion.ultimo_mensaje.lower()):
            return

        respuesta = mensaje.lower().strip()
        if respuesta in ["si", "no"]:
            if actualizar_confirmacion_cita(sesion.cita_actual.documento, respuesta):
                if respuesta == "si":
                    mensaje_respuesta = (
                        f"✅ ¡Genial! Te esperamos el *{sesion.cita_actual.fechaCita}* "
                        f"para tu cita programada. Si necesitas otra consulta, escribe: *Cita*."
                    )
                else:
                    mensaje_respuesta = (
                        "👍 Entendido. Si deseas otra consulta, escribe: *Cita*."
                    )
                whatsapp_api.send_message(numero, mensaje_respuesta)
            else:
                whatsapp_api.send_message(
                    numero,
                    "❌ Hubo un error al actualizar tu confirmación. Por favor intenta nuevamente más tarde."
                )
            sesion.estado = EstadoUsuario.INICIO
            sesion.cita_actual = None
        else:
            if not sesion.ultimo_mensaje or "error confirmación" not in sesion.ultimo_mensaje.lower():
                sesion.intentos += 1
            
            if sesion.intentos >= self.max_intentos:
                sesion.bloqueado_hasta = datetime.now() + self.tiempo_bloqueo
                respuesta_msg = "⏳ Has excedido el número máximo de intentos. Por favor intenta nuevamente más tarde."
            else:
                respuesta_msg = "❓ Por favor, responde con *si* o *no*."
            
            whatsapp_api.send_message(numero, respuesta_msg)
            sesion.ultimo_mensaje = self.normalizar_mensaje(respuesta)
        
        self.estado_usuarios[numero] = sesion
        self.guardar_estado()

    def procesar_mensaje(self, numero: str, mensaje: str):
        """Procesa el mensaje según el estado actual del usuario."""
        if not numero or not mensaje:
            return

        sesion = self.estado_usuarios.get(numero, SesionUsuario())
        sesion.ultima_interaccion = datetime.now()

        if sesion.estado == EstadoUsuario.INICIO:
            self.manejar_mensaje_inicio(numero, mensaje)
        elif sesion.estado == EstadoUsuario.ESPERANDO_TIPO_DOCUMENTO:
            self.manejar_tipo_documento(numero, mensaje)
        elif sesion.estado == EstadoUsuario.ESPERANDO_NUMERO_DOCUMENTO:
            self.manejar_numero_documento(numero, mensaje)
        elif sesion.estado == EstadoUsuario.ESPERANDO_CONFIRMACION:
            self.manejar_confirmacion(numero, mensaje)
        
        self.estado_usuarios[numero] = sesion
        self.guardar_estado()

    def enviar_recordatorios(self):
        while True:
            try:
                citas = obtener_citas_proximas()
                if not citas:
                    logger.info("No hay citas próximas para recordatorios")
                    time.sleep(86400)
                    continue

                for cita in citas:
                    if cita.confirmacionCita != "si":
                        continue

                    mensaje = self._crear_mensaje_recordatorio(cita)
                    numero = f"+57{cita.telefonoPaciente}"
                    
                    if not whatsapp_api.send_message(numero, mensaje):
                        logger.error(f"No se pudo enviar recordatorio a {cita.nombrePaciente}")

                    time.sleep(2)

                time.sleep(86400)

            except Exception as e:
                logger.error(f"Error crítico en recordatorios: {e}", exc_info=True)
                time.sleep(3600)

    def _crear_mensaje_recordatorio(self, cita) -> str:
        """Genera el texto del mensaje de recordatorio."""
        return (
            f"📅 *Recordatorio de Cita Médica*%0A%0A"
            f"Hola {cita.nombrePaciente}, este es un recordatorio de tu cita médica.%0A"
            f"🏥 *Especialidad:* {cita.especialidad}%0A"
            f"👨‍⚕️ *Médico:* {cita.nombreMedico}%0A"
            f"📅 *Fecha:* {cita.fechaCita}%0A%0A"
            f"Por favor llega 15 minutos antes de tu hora programada."
        )

# Crear instancia global del bot
bot = OHIBot()

@app.get("/webhook")
async def verify_webhook(request: Request):
    """Verificación del webhook para WhatsApp"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            logger.info("Webhook verificado")
            return Response(content=challenge, status_code=status.HTTP_200_OK)
    
    logger.error("Fallo en verificación de webhook")
    return Response(status_code=status.HTTP_403_FORBIDDEN)

@app.post("/webhook")
async def process_webhook(request: Request):
    """Procesa los mensajes entrantes de WhatsApp"""
    data = await request.json()
    
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        
        if "messages" in value:
            message_data = value["messages"][0]
            from_num = message_data["from"]
            message = message_data["text"]["body"]
            timestamp = datetime.fromtimestamp(int(message_data["timestamp"]))
            
            # Procesar el mensaje
            bot.procesar_mensaje(from_num, message)
            
    except Exception as e:
        logger.error(f"Error procesando webhook: {e}")
    
    return Response(status_code=status.HTTP_200_OK)

def iniciar_bot():
    """Función para iniciar el bot y el servidor web"""
    # Iniciar hilo para recordatorios
    threading.Thread(
        target=bot.enviar_recordatorios,
        daemon=True
    ).start()
    
    # Iniciar servidor web
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    iniciar_bot()