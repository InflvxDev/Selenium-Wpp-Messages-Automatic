import json
import time
import threading
import re
from typing import Dict, Optional, Tuple, List
from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from whatsapp import whatsapp_driver
from database import buscar_cita, actualizar_confirmacion_cita, obtener_citas_proximas, Cita
from config import logger

class EstadoUsuario(Enum):
    INICIO = auto()
    ESPERANDO_TIPO_DOCUMENTO = auto()
    ESPERANDO_NUMERO_DOCUMENTO = auto()
    ESPERANDO_CONFIRMACION = auto()
    CITA_ENCONTRADA = auto()
    SELECIONANDO_OPCIONES = auto()
    CANCELANDO_CITA = auto()
    CONFIRMANDO_CANCELACION = auto()

@dataclass
class SesionUsuario:
    estado: EstadoUsuario = EstadoUsuario.INICIO
    intentos: int = 0
    citas_confirmadas: List[Cita] = field(default_factory=list)
    cita_actual: Optional[Cita] = None
    ultimo_mensaje: Optional[str] = None
    ultimo_mensaje_bloqueo: Optional[datetime] = None 
    tipo_documento: Optional[str] = None
    ultima_interaccion: datetime = datetime.now()
    bloqueado_hasta: Optional[datetime] = None

class OHIBot:
    def __init__(self):
        self.estado_usuarios: Dict[str, SesionUsuario] = {}
        self.cargar_estado()
        self.grupos_ignorados = ["EgresadosIngSistUPC", "EspañitaSoviética"]
        self.max_intentos = 10
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

    def obtener_ultimo_mensaje(self) -> Tuple[Optional[str], Optional[str]]:
        """Obtiene el último mensaje recibido con manejo robusto de errores."""
        try:
            driver = whatsapp_driver.iniciar_driver()
            if not driver:
                return None, None

            contactos = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, '_ak8q')]//span[@title]"))
            )
            mensajes = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, '_ak8k')]"))
            )

            if mensajes and contactos:
                ultimo_mensaje = mensajes[0].text
                ultimo_contacto = contactos[0].text.replace(" ", "")

                if ultimo_contacto in self.grupos_ignorados:
                    return None, None

                if ultimo_contacto.startswith("+"):
                    return ultimo_contacto, ultimo_mensaje

            return None, None
        except Exception as e:
            logger.error(f"Error al obtener mensaje: {e}", exc_info=True)
            return None, None

    def usuario_bloqueado(self, numero: str) -> bool:
        """Verifica si el usuario está temporalmente bloqueado."""
        sesion = self.estado_usuarios.get(numero, SesionUsuario())
        if sesion.bloqueado_hasta and datetime.now() < sesion.bloqueado_hasta:
            tiempo_restante = sesion.bloqueado_hasta - datetime.now()
            minutos = int(tiempo_restante.total_seconds() / 60)

            ultimo_mensaje_bloqueo = getattr(sesion, "ultimo_mensaje_bloqueo", None)
            if not ultimo_mensaje_bloqueo or (datetime.now() - ultimo_mensaje_bloqueo).total_seconds() > 600:
                
                whatsapp_driver.enviar_mensaje(
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

        if not texto:
            return ""

        # Diccionario de reemplazo para tildes
        replacements = {
            'á': 'a',
            'é': 'e',
            'í': 'i',
            'ó': 'o',
            'ú': 'u',
            'ü': 'u',
            'Á': 'A',
            'É': 'E',
            'Í': 'I',
            'Ó': 'O',
            'Ú': 'U',
            'Ü': 'U',
            'ñ': 'n',
            'Ñ': 'N'
        }

        # Reemplazar caracteres acentuados
        for old, new in replacements.items():
            texto = texto.replace(old, new)

        # Remover emojis (conservando signos de puntuación)
        texto_sin_emojis = texto.encode('ascii', 'ignore').decode('ascii')

        # Conservar letras, números, espacios y signos de puntuación básicos
        texto_limpio = re.sub(r'[^\w\s.,;:?¿!¡]', '', texto_sin_emojis)

         # 1. Reemplazar múltiples espacios por uno solo
        texto_limpio = re.sub(r'\s+', ' ', texto_limpio)

        # Estandarizar formato de listas: "1. medico" → "1. medico" (espacio después del punto)
        texto_limpio = re.sub(r'(\d+)\.\s*', r'\1. ', texto_limpio)

        # Estandarizar dos puntos: "fecha:20250417" → "fecha: 20250417"
        texto_limpio = re.sub(r':\s*', ': ', texto_limpio) 

        # Convertir a minúsculas y quitar espacios extras
        texto_normalizado = texto_limpio.lower().strip()


        # Manejar caso especial de "escribiendo..."
        if "escribiendo" in texto_normalizado:
            return "escribiendo"

        return texto_normalizado

    def manejar_mensaje_inicio(self, numero: str, mensaje: str):
        """Maneja el estado INICIO de la conversación."""
        sesion = self.estado_usuarios.get(numero, SesionUsuario())
        
        if mensaje.lower() == "hola":
            respuesta = (
                "🤖 ¡Hola! Soy *BOHI*, tu asistente virtual.%0A%0A"
                "¿Quieres consultar una cita médica? Escribe *Cita* para comenzar. 🩺"
            )
            whatsapp_driver.enviar_mensaje(numero, respuesta)
            sesion.estado = EstadoUsuario.INICIO
            sesion.ultimo_mensaje = self.normalizar_mensaje(respuesta)
        
        elif mensaje.lower() == "cita" and sesion.estado == EstadoUsuario.INICIO:
            respuesta = "🆔 Por favor, indica el tipo de documento (solo las siglas):%0A%0A"
            respuesta += (  
                "- Cédula de Ciudadanía: *CC*%0A"
                "- Tarjeta de Identidad: *TI*%0A"
                "- Cédula de Extranjería: *CE*%0A"
                "- Carné Diplomático: *CD*%0A"
                "- Pasaporte: *PA*%0A"
                "- Salvoconducto de Permanencia: *SC*%0A"
                "- Permiso Especial de Permanencia: *PE*%0A"
                "- Registro Civil: *RC*%0A"
                "- Certificado de Nacido Vivo: *CN*%0A"
                "- Adulto sin Identificación: *AS*%0A"
                "- Menor sin Identificación: *MS*%0A"
                "- Permiso por Protección Temporal: *PT*%0A"
            )
            whatsapp_driver.enviar_mensaje(numero, respuesta)
            sesion.estado = EstadoUsuario.ESPERANDO_TIPO_DOCUMENTO
            sesion.ultimo_mensaje = self.normalizar_mensaje(respuesta.replace("%0A", ""))
        
        self.estado_usuarios[numero] = sesion
        self.guardar_estado()

    def manejar_tipo_documento(self, numero: str, mensaje: str):
        """Maneja la entrada del tipo de documento con verificación de repetición."""
        
        sesion = self.estado_usuarios.get(numero)
        mensaje = self.normalizar_mensaje(mensaje)

        if (
            not sesion or
            self.usuario_bloqueado(numero) or
            mensaje.lower() in ["escribiendo", "escribiendo..."] or
            (
                sesion.ultimo_mensaje and 
                mensaje.strip().lower() == sesion.ultimo_mensaje.lower()
            )
        ):
            return

        tipo_doc = mensaje.lower().strip()
        if tipo_doc in ["cc", "ti", "ce", "cd", "pa", "sc", "pe", "rc", "cn", "as", "ms", "pt"]:
            sesion.tipo_documento = tipo_doc.upper()
            sesion.estado = EstadoUsuario.ESPERANDO_NUMERO_DOCUMENTO
            sesion.intentos = 0
            respuesta = "🔢 Ahora, por favor escribe tu *número de documento* (sin puntos ni espacios):"
            whatsapp_driver.enviar_mensaje(numero, respuesta)
            sesion.ultimo_mensaje = self.normalizar_mensaje(respuesta)

        else:
            # Solo contar como intento si es un mensaje nuevo
            if not sesion.ultimo_mensaje or "error tipo documento" or "escribiendo" not in sesion.ultimo_mensaje.lower():
                sesion.intentos += 1
            
            if sesion.intentos >= self.max_intentos:
                sesion.bloqueado_hasta = datetime.now() + self.tiempo_bloqueo
                respuesta = "⏳ Has superado el número máximo de intentos. Intenta más tarde."
            else:
                respuesta = "❌ El tipo de documento que ingresaste no es válido. Por favor intenta de nuevo."
            
            whatsapp_driver.enviar_mensaje(numero, respuesta)
            sesion.ultimo_mensaje = self.normalizar_mensaje(respuesta)

        self.estado_usuarios[numero] = sesion
        self.guardar_estado()

    def manejar_numero_documento(self, numero: str, mensaje: str):
        """Maneja la entrada del número de documento con verificación de repetición."""
        sesion = self.estado_usuarios.get(numero)
        mensaje = self.normalizar_mensaje(mensaje)

        if (
            not sesion or
            self.usuario_bloqueado(numero) or
            mensaje.lower() in ["escribiendo", "escribiendo..."] or
            (
                sesion.ultimo_mensaje and 
                mensaje.strip().lower() == sesion.ultimo_mensaje.lower() or
                mensaje.lower().startswith(sesion.ultimo_mensaje.lower().split()[0]) 
            )
        ):
            return
        

        if mensaje.isdigit():

            citas = buscar_cita(sesion.tipo_documento, mensaje)
            sesion.intentos = 0
            
            if citas:
                sesion.citas_confirmadas = [cita for cita in citas if cita.confirmacionCita == "si"]
                respuesta = "📅 *Tus citas ya Programadas:*%0A%0A"
                for cita in citas:
                    estado = "✅ Confirmada" if cita.confirmacionCita.lower() == "si" else "❌ No asistirás"
                    respuesta += (
                        f"👨‍⚕️ *Médico:* {cita.nombreMedico}%0A"
                        f"🏥 *Especialidad:* {cita.especialidad}%0A"
                        f"📅 *Fecha:* {cita.fechaCita}%0A"
                        f"{estado}%0A%0A"
                    )
                respuesta += "🩺 Si necesitas otra consulta, escribe: *Cita*%0A"
                respuesta += "ℹ️ Para cancelar un cita ya programada, escribe *cancelar cita*."
                sesion.estado = EstadoUsuario.SELECIONANDO_OPCIONES
            else:
                respuesta = "⚠️ No encontré ninguna cita actual o proxima con ese documento. Si deseas intentar otra consulta, escribe: *Cita*"
                sesion.estado = EstadoUsuario.INICIO
            
            whatsapp_driver.enviar_mensaje(numero, respuesta)
            sesion.ultimo_mensaje = self.normalizar_mensaje(respuesta.replace("%0A", ""))
       
        else:
            # Solo contar como intento si es un mensaje nuevo
            if not sesion.ultimo_mensaje or "error número documento" not in sesion.ultimo_mensaje.lower():
                sesion.intentos += 1
            
            if sesion.intentos >= self.max_intentos:
                sesion.bloqueado_hasta = datetime.now() + self.tiempo_bloqueo
                respuesta = "⏳ Has excedido el número máximo de intentos. Por favor intenta nuevamente más tarde."
            else:
                respuesta = "❌ El número de documento ingresado no es válido. Inténtalo de nuevo (solo números)."
            
            whatsapp_driver.enviar_mensaje(numero, respuesta)
            sesion.ultimo_mensaje = self.normalizar_mensaje(respuesta)
            
        self.estado_usuarios[numero] = sesion
        self.guardar_estado()

    def manejar_seleccion_opciones(self, numero: str, mensaje: str):
        """Maneja la selección de cita cuando hay múltiples opciones."""
        sesion = self.estado_usuarios.get(numero)
        mensaje = self.normalizar_mensaje(mensaje)


        if (
            not sesion or
            self.usuario_bloqueado(numero) or
            mensaje.lower() in ["escribiendo", "escribiendo..."] or
            (
                sesion.ultimo_mensaje and 
                mensaje.strip().lower() == sesion.ultimo_mensaje.lower() or 
                mensaje.lower().startswith(sesion.ultimo_mensaje.lower().split()[0]) 
            )
        ):
            return
        

        if mensaje.lower().strip() == "cancelar cita" and sesion.citas_confirmadas:
            respuesta = "⚠️ *¿Cual de tus Citas confirmadas quieres cancelar?:*%0A%0A"
            for i, cita in enumerate(sesion.citas_confirmadas):
                respuesta += (
                    f"{i+1}. 👨‍⚕️ *Médico:* {cita.nombreMedico}%0A"
                    f"   🏥 *Especialidad:* {cita.especialidad}%0A"
                    f"   📅 *Fecha:* {cita.fechaCita}%0A%0A"
                )
            respuesta += "✏️ Escribe el número de la cita que deseas cancelar.%0A"
            respuesta += "ℹ️ si quieres terminar el proceso de cancelacion, escribe *terminar*."

            whatsapp_driver.enviar_mensaje(numero, respuesta)
            sesion.ultimo_mensaje = self.normalizar_mensaje(respuesta.replace("%0A", ""))
            sesion.estado = EstadoUsuario.CANCELANDO_CITA

        elif mensaje.lower().strip() == "cita":
            sesion.estado = EstadoUsuario.INICIO
            sesion.cita_actual = None
            sesion.citas_confirmadas = []

        else:
            return
        
        
        self.estado_usuarios[numero] = sesion
        self.guardar_estado()

    def manejar_cancelacion_cita(self, numero: str, mensaje: str):
        sesion = self.estado_usuarios.get(numero)
        mensaje = self.normalizar_mensaje(mensaje)


        if (
            not sesion or
            self.usuario_bloqueado(numero) or
            mensaje.lower() in ["escribiendo", "escribiendo..."] or
            (
                sesion.ultimo_mensaje and 
                mensaje.strip().lower() == sesion.ultimo_mensaje.lower() or 
                mensaje.lower().startswith(sesion.ultimo_mensaje.lower().split()[0]) 
            )
        ):
            return
        
        if mensaje.lower().strip() == "terminar":
            respuesta = "ℹ️ Has terminado la cancelacion de citas. Si deseas otra consulta, escribe: *Cita*."
            whatsapp_driver.enviar_mensaje(numero, respuesta)
            sesion.ultimo_mensaje = self.normalizar_mensaje(respuesta.replace("%0A", ""))
            sesion.estado = EstadoUsuario.INICIO
            sesion.cita_actual = None
            sesion.citas_confirmadas = []
            self.estado_usuarios[numero] = sesion
            self.guardar_estado()
            return
        
        elif mensaje.isdigit():
            seleccion = int(mensaje)
            if 1 <= seleccion <= len(sesion.citas_confirmadas):
                sesion.cita_actual = sesion.citas_confirmadas[seleccion - 1]
                respuesta = self._crear_mensaje_cita(sesion.cita_actual)
                sesion.estado = EstadoUsuario.CONFIRMANDO_CANCELACION
            else:
                if not sesion.ultimo_mensaje or "error número documento" not in sesion.ultimo_mensaje.lower():
                    sesion.intentos += 1
                
                if sesion.intentos >= self.max_intentos:
                    sesion.bloqueado_hasta = datetime.now() + self.tiempo_bloqueo
                    respuesta = "⏳ Has excedido el número máximo de intentos. Por favor intenta nuevamente más tarde."
                else:
                    respuesta = f"❌ Selección inválida. Escribe un número entre 1 y {len(sesion.citas_confirmadas):}."
                
        else:
            if not sesion.ultimo_mensaje or "error número documento" not in sesion.ultimo_mensaje.lower():
                sesion.intentos += 1
            
            if sesion.intentos >= self.max_intentos:
                sesion.bloqueado_hasta = datetime.now() + self.tiempo_bloqueo
                respuesta = "⏳ Has excedido el número máximo de intentos. Por favor intenta nuevamente más tarde."
            else:
                respuesta = "❌ Por favor, escribe solo el número de la cita que deseas confirmar."
        
        whatsapp_driver.enviar_mensaje(numero, respuesta)
        sesion.ultimo_mensaje = self.normalizar_mensaje(respuesta.replace("%0A", ""))
        self.estado_usuarios[numero] = sesion
        self.guardar_estado()
    
    def manejar_confirmacion_cancelacion(self, numero: str, mensaje: str):

        sesion = self.estado_usuarios.get(numero)
        mensaje = self.normalizar_mensaje(mensaje)


        if (
            not sesion or
            self.usuario_bloqueado(numero) or
            mensaje.lower() in ["escribiendo", "escribiendo..."] or
            (
                sesion.ultimo_mensaje and 
                mensaje.strip().lower() == sesion.ultimo_mensaje.lower() or 
                mensaje.lower().startswith(sesion.ultimo_mensaje.lower().split()[0]) 
            )
        ):
            return
        
        if mensaje.lower().strip() == "terminar":
            respuesta = "ℹ️ Has terminado la cancelacion de citas. Si deseas otra consulta, escribe: *Cita*."
            whatsapp_driver.enviar_mensaje(numero, respuesta)
            sesion.ultimo_mensaje = self.normalizar_mensaje(respuesta.replace("%0A", ""))
            sesion.estado = EstadoUsuario.INICIO
            sesion.cita_actual = None
            sesion.citas_confirmadas = []
            self.estado_usuarios[numero] = sesion
            self.guardar_estado()
            return

        if mensaje == "si":
            exito = actualizar_confirmacion_cita(sesion.cita_actual.id, "no")
            if exito:
                respuesta = "✅ Tu cita ha sido *cancelada exitosamente*. Si deseas otra consulta, escribe: *Cita*."
            else:
                respuesta = "❌ Ocurrió un error al cancelar la cita. Intenta más tarde."
            sesion.estado = EstadoUsuario.INICIO
            sesion.cita_actual = None
            sesion.citas_confirmadas = []
        elif mensaje == "no":
            respuesta = "📅 Entendido. Tu cita *no será cancelada*. Si deseas otra consulta, escribe: *Cita*."
            sesion.estado = EstadoUsuario.INICIO
            sesion.cita_actual = None
            sesion.citas_confirmadas = []
        else:
            if not sesion.ultimo_mensaje or "error número documento" not in sesion.ultimo_mensaje.lower():
                sesion.intentos += 1
            
            if sesion.intentos >= self.max_intentos:
                sesion.bloqueado_hasta = datetime.now() + self.tiempo_bloqueo
                respuesta = "⏳ Has excedido el número máximo de intentos. Por favor intenta nuevamente más tarde."
            else:
                respuesta = "❓ Por favor responde con *si* o *no* para confirmar la cancelacion."

        whatsapp_driver.enviar_mensaje(numero, respuesta)
        sesion.ultimo_mensaje = self.normalizar_mensaje(respuesta.replace("%0A", ""))

        self.estado_usuarios[numero] = sesion
        self.guardar_estado()


    def _crear_mensaje_cita(self, cita: Cita) -> str:

        return (
            f"⚠️ *Cita a cancelar:*%0A%0A"
            f"📝 *Documento Paciente:* {cita.tipoDocumento} {cita.documento}%0A"
            f"👤 *Nombre Paciente:* {cita.nombrePaciente}%0A"
            f"👨‍⚕️ *Médico:* {cita.nombreMedico}%0A"
            f"🏥 *Especialidad:* {cita.especialidad}%0A"
            f"📅 *Fecha:* {cita.fechaCita}%0A%0A"
            f"⚠️ ¿Estas de seguro de cancelar esta cita? Responde con *si* o *no*.%0A"
            f"ℹ️ Para terminar el proceso, escribe *terminar*."
        )

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
        elif sesion.estado == EstadoUsuario.SELECIONANDO_OPCIONES:
            self.manejar_seleccion_opciones(numero, mensaje)
        elif sesion.estado == EstadoUsuario.CANCELANDO_CITA:
            self.manejar_cancelacion_cita(numero, mensaje)
        elif sesion.estado == EstadoUsuario.CONFIRMANDO_CANCELACION:
            self.manejar_confirmacion_cancelacion(numero, mensaje)
        
        self.estado_usuarios[numero] = sesion
        self.guardar_estado()

    def enviar_recordatorios(self):
        while True:
            try:
                # Esperar conexión estable
                if not self._esperar_conexion_whatsapp():
                    time.sleep(60)
                    continue

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
                    
                    if not self._enviar_mensaje_seguro(numero, mensaje):
                        logger.error(f"No se pudo enviar recordatorio a {cita.nombrePaciente}")
                        # Reintentar conexión si falla
                        if not self._esperar_conexion_whatsapp():
                            break  # Salir del bucle de citas si no se puede reconectar

                    time.sleep(2)  # Pausa entre mensajes

                time.sleep(86400)  # Esperar 24 horas

            except Exception as e:
                logger.error(f"Error crítico en recordatorios: {e}", exc_info=True)
                time.sleep(3600)  # Esperar 1 hora antes de reintentar

    def _esperar_conexion_whatsapp(self, timeout_min=5) -> bool:
        """Espera hasta que WhatsApp esté conectado."""
        timeout = time.time() + 60 * timeout_min
        while time.time() < timeout:
            if whatsapp_driver.iniciar_driver():
                return True
            time.sleep(10)
        return False

    def _enviar_mensaje_seguro(self, numero: str, mensaje: str) -> bool:
        """Intenta enviar mensaje con múltiples reintentos."""
        max_intentos = 3
        for intento in range(max_intentos):
            try:
                if whatsapp_driver.enviar_mensaje(numero, mensaje):
                    return True
            except Exception as e:
                logger.warning(f"Intento {intento + 1} fallido: {str(e)}")
                time.sleep(5)
        return False

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
        
    def iniciar(self):
        """Inicia el bot principal."""
        try:
            # Hilo para recordatorios
            threading.Thread(
                target=self.enviar_recordatorios,
                daemon=True
            ).start()

            # Bucle principal
            logger.info("OHIBot iniciado. Esperando mensajes...")
            while True:
                numero, mensaje = self.obtener_ultimo_mensaje()
                if numero and mensaje:
                    self.procesar_mensaje(numero, mensaje)
                time.sleep(5)

        except KeyboardInterrupt:
            logger.info("Deteniendo OHIBot...")
        finally:
            whatsapp_driver.cerrar()
            self.guardar_estado()

if __name__ == "__main__":
    bot = OHIBot()
    bot.iniciar()