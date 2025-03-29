import time
import json
import threading
from whatsapp import enviar_mensaje, iniciar_driver
from database import buscar_cita, actualizar_confirmacion_cita, obtener_citas_proximas
from selenium.webdriver.common.by import By

driver = iniciar_driver()

estado_usuarios = {}
ultimo_mensaje_enviado = {}

def guardar_estado():
    with open("estado_usuarios.json", "w") as f:
        json.dump(estado_usuarios, f)

def cargar_estado():
    global estado_usuarios
    try:
        with open("estado_usuarios.json", "r") as f:
            estado_usuarios = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        estado_usuarios = {}

cargar_estado()

def obtener_ultimo_mensaje():
    """Obtiene el último mensaje recibido en la conversación activa."""
    try:
        mensajes = driver.find_elements(By.XPATH, "//div[@class='_akbu']//span[@class='_ao3e selectable-text copyable-text']")
        if mensajes:
            return mensajes[-1].text  # Último mensaje recibido
        return None
    except Exception as e:
        print(f"❌ Error al obtener mensaje: {e}")
        return None

def leer_mensajes(numero_contacto):
    """Lee mensajes nuevos y responde según el flujo de conversación."""
    print("✅  Inicializado sesión de WhatsApp Correctamente")

    try:
        if numero_contacto not in estado_usuarios:
            enviar_mensaje(numero_contacto, "🤖 ¡Hola! Soy *OHIBot*, tu asistente virtual. %0A%0A¿Necesitas información sobre tu cita? Escribe *Cita* para comenzar.")
            estado_usuarios[numero_contacto] = "inicio"
            ultimo_mensaje_enviado[numero_contacto] = "hola"
            guardar_estado()
        else:
            enviar_mensaje(numero_contacto, "🤖 ¡Hola de nuevo! %0A%0A¿Necesitas información sobre tu cita? Escribe *Cita* para comenzar.")
            ultimo_mensaje_enviado[numero_contacto] = "hola de nuevo"
            estado_usuarios[numero_contacto] = "inicio"
            guardar_estado()    
        
        cita = None
        tipo_documento = None
        time.sleep(10)
        
        while True:
            
            respuesta = obtener_ultimo_mensaje()
            if respuesta:

                estado_actual = estado_usuarios.get(numero_contacto, "inicio")

                print(f"📩 Respuesta recibida: {respuesta}")
                if estado_actual == "inicio":

                    if respuesta.lower() == "cita":
                        enviar_mensaje(numero_contacto, "📄 Por favor, ingresa el tipo de documento a consultar: *CC / TI / CE*")
                        ultimo_mensaje_enviado[numero_contacto] = "por favor, ingresa el tipo de documento a consultar: cc / ti / ce"
                        estado_usuarios[numero_contacto] = "esperando numero documento"
                        guardar_estado()    
                
                elif estado_actual == "esperando numero documento":
                    
                    
                    if respuesta.lower() in ["cc", "ti", "ce"]:
                        tipo_documento = respuesta.upper()
                        enviar_mensaje(numero_contacto, "🔢 Ahora, por favor ingresa tu número de documento (sin puntos ni espacios):")
                        ultimo_mensaje_enviado[numero_contacto] = "ahora, por favor ingresa tu número de documento (sin puntos ni espacios):"
                        estado_usuarios[numero_contacto] = "esperando cita"
                        guardar_estado()

                    elif respuesta.strip().lower() != ultimo_mensaje_enviado[numero_contacto].strip().lower():
                            enviar_mensaje(numero_contacto, "❌ El tipo de documento ingresado no es válido. Inténtalo de nuevo.")
                            ultimo_mensaje_enviado[numero_contacto] = "el tipo de documento ingresado no es válido. inténtalo de nuevo."

                elif estado_actual == "esperando cita":

                    if respuesta.isdigit():

                        cita = buscar_cita(tipo_documento ,respuesta)

                        if cita:

                            if cita['confirmacionCita'] in ["", None]:

                                mensaje = (
                                    f"📅 *Cita encontrada:* %0A%0A"
                                    f"📝 *Documento Paciente:* {cita['tipoDocumento']} {cita['documento']}%0A"
                                    f"👨 *Nombre Paciente:* {cita['nombrePaciente']}%0A"
                                    f"👨‍⚕️ *Médico:* {cita['nombreMedico']}%0A"
                                    f"🏥 *Especialidad:* {cita['especialidad']}%0A"
                                    f"🗓 *Fecha:* {cita['fechaCita']}%0A%0A"
                                    f"✅ ¿Asistirás a la cita? Responde con *si* o *no*."
                                )
                                ultimo_mensaje_enviado[numero_contacto] = respuesta
                                estado_usuarios[numero_contacto] = "esperando confirmacion"
                            
                            else:
                                
                                mensaje = (
                                    f"⚠ *Tu cita ya fue confirmada.* Te muestro los detalles: %0A%0A"
                                    f"📝 *Documento Paciente:* {cita['tipoDocumento']} {cita['documento']}%0A"
                                    f"👨 *Nombre Paciente:* {cita['nombrePaciente']}%0A"
                                    f"👨‍⚕️ *Médico:* {cita['nombreMedico']}%0A"
                                    f"🏥 *Especialidad:* {cita['especialidad']}%0A"
                                    f"🗓 *Fecha:* {cita['fechaCita']}%0A"
                                    f"📌 *Asistencia:* {cita['confirmacionCita']}%0A%0A"
                                    f"Si deseas otra consulta, escribe: *Cita*"
                                )
                                estado_usuarios[numero_contacto] = "inicio"
                        else:

                            mensaje = "⚠ No encontré ninguna cita con ese documento. Si deseas intentar otra consulta, escribe: *Cita*"
                            estado_usuarios[numero_contacto] = "inicio"

                        enviar_mensaje(numero_contacto, mensaje)
                        guardar_estado()

                    elif respuesta.strip().lower() != ultimo_mensaje_enviado[numero_contacto].strip().lower():
                            enviar_mensaje(numero_contacto, "❌ El número de documento ingresado no es válido. Inténtalo de nuevo.")
                            ultimo_mensaje_enviado[numero_contacto] = "el número de documento ingresado no es válido. inténtalo de nuevo."

                elif estado_actual == "esperando confirmacion":

                    if respuesta.lower() == "si":

                        enviar_mensaje(numero_contacto, f"✅ ¡Genial! Te esperamos el *{cita['fechaCita']}* para tu cita programada. Si necesitas otra consulta, escribe: *Cita*.")
                        actualizar_confirmacion_cita(cita['documento'], respuesta)
                        estado_usuarios[numero_contacto] = "inicio"

                    elif respuesta.lower() == "no":

                        enviar_mensaje(numero_contacto, "👍 Entendido. Si deseas otra consulta, escribe: *Cita*.")
                        actualizar_confirmacion_cita(cita['documento'], respuesta)
                        estado_usuarios[numero_contacto] = "inicio"

                    elif respuesta.strip().lower() != ultimo_mensaje_enviado[numero_contacto].strip().lower():
                        enviar_mensaje(numero_contacto, "❓ Por favor, responde con *si* o *no*.")
                        ultimo_mensaje_enviado[numero_contacto] = "por favor, responde con si o no."

                    guardar_estado()

            time.sleep(5)
    except Exception as e:
        print(f"❌ Error en el chatbot: {e}")



def enviar_recordatorios():
    while True:
        try:
            citas = obtener_citas_proximas()

            if not citas:
                print("🔔 No hay citas próximas para enviar recordatorios.")
                time.sleep(86400)
                continue

            for cita in citas:
                mensaje = (
                    f"📅 *Recordatorio de Cita Médica*%0A%0A"
                    f"Hola {cita['nombrePaciente']}, este es un recordatorio de tu cita médica.%0A"
                    f"🏥 *Especialidad:* {cita['especialidad']}%0A"
                    f"👨‍⚕️ *Médico:* {cita['nombreMedico']}%0A"
                    f"📅 *Fecha:* {cita['fechaCita']}%0A%0A"
                )
                numero_contacto = f"+57{cita['telefonoPaciente']}"
                enviar_mensaje(numero_contacto, mensaje)
                time.sleep(2)

            print(f"✅ Recordatorio enviado a {cita['nombrePaciente']} ({numero_contacto})")

            time.sleep(86400)  # Esperar 24 horas antes de enviar el siguiente recordatorio
        
        except Exception as e:
            print(f"❌ Error al enviar recordatorios: {e}")
                
    
if __name__ == "__main__":
    # Iniciar el hilo para enviar recordatorios
    hilo_recordatorios = threading.Thread(target=enviar_recordatorios)
    hilo_recordatorios.start()

    # Leer mensajes y responder
    leer_mensajes("+573135360339")



