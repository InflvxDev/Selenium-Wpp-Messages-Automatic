import time
from whatsapp import enviar_mensaje, iniciar_driver
from database import buscar_cita, actualizar_confirmacion_cita
from selenium.webdriver.common.by import By

driver = iniciar_driver()

estado_usuarios = {}

def leer_mensajes(numero_contacto):
    """Lee mensajes nuevos y responde según el flujo de conversación."""
    print("✅  Inicializado sesión de WhatsApp Correctamente")
    try:
        enviar_mensaje(numero_contacto, "🤖 ¡Hola! Soy *OHIBot*, tu asistente virtual. ¿Necesitas información sobre tu cita? Escribe *Cita* para comenzar.")
        estado_actual = "inicio"
        cita = None
        ultimo_mensaje_enviado = None
        time.sleep(10)
        
        while True:
            
            respuesta = obtener_ultimo_mensaje()
            if respuesta:

                print(f"📩 Respuesta recibida: {respuesta}")
                if estado_actual == "inicio":

                    if respuesta.lower() == "cita":
                        enviar_mensaje(numero_contacto, "📄 Por favor, ingresa el tipo de documento a consultar: *CC / TI / CE*")
                        ultimo_mensaje_enviado = "por favor, ingresa el tipo de documento a consultar: cc / ti / ce"
                        estado_actual = "esperando numero documento"    
                
                elif estado_actual == "esperando numero documento":
                    

                    if respuesta.lower() in ["cc", "ti", "ce"]:
                        enviar_mensaje(numero_contacto, "🔢 Ahora, por favor ingresa tu número de documento (sin puntos ni espacios):")
                        ultimo_mensaje_enviado = "ahora, por favor ingresa tu número de documento (sin puntos ni espacios):"
                        estado_actual = "esperando cita"

                    elif respuesta.strip().lower() != ultimo_mensaje_enviado.strip().lower():
                            enviar_mensaje(numero_contacto, "❌ El tipo de documento ingresado no es válido. Inténtalo de nuevo.")
                            ultimo_mensaje_enviado = "el tipo de documento ingresado no es válido. inténtalo de nuevo."

                elif estado_actual == "esperando cita":

                    if respuesta.isdigit():

                        cita = buscar_cita(respuesta)

                        if cita:

                            if cita['confirmacionCita'] == "":

                                mensaje = f"📅 *Cita encontrada: *\n👨‍⚕️ Médico: {cita['nombreMedico']}\n 🏥 Especialidad: {cita['especialidad']}\n 🗓 Fecha: {cita['fechaCita']}\n\n ✅ ¿Asistirás a la cita? Responde con *si* o *no*."
                                estado_actual = "esperando confirmacion"
                            
                            else:
                                mensaje = f"⚠ Tu cita ya fue confirmada, te puedo dar la informacion de la Cita: 👨‍⚕️ Médico: *{cita['nombreMedico']}* 🏥 Especialidad: *{cita['especialidad']}* 🗓 Fecha: *{cita['fechaCita']}* Asistencia: *{cita['confirmacionCita']}*. Si deseas otra consulta, escribe: *Cita*"
                                estado_actual = "inicio"
                        else:

                            mensaje = "⚠ No encontré ninguna cita con ese documento. Si deseas intentar otra consulta, escribe: *Cita*"
                            estado_actual = "inicio"

                        enviar_mensaje(numero_contacto, mensaje)

                    elif respuesta.strip().lower() != ultimo_mensaje_enviado.strip().lower():
                            enviar_mensaje(numero_contacto, "❌ El número de documento ingresado no es válido. Inténtalo de nuevo.")
                            ultimo_mensaje_enviado = "el número de documento ingresado no es válido. inténtalo de nuevo."

                elif estado_actual == "esperando confirmacion":

                    if respuesta.lower() == "si":

                        enviar_mensaje(numero_contacto, f"✅ ¡Genial! Te esperamos el *{cita['fechaCita']}* para tu cita programada. Si necesitas otra consulta, escribe: *Cita*.")
                        estado_actual = "inicio"
                        actualizar_confirmacion_cita(cita['documento'], respuesta)

                    elif respuesta.lower() == "no":

                        enviar_mensaje(numero_contacto, "👍 Entendido. Si deseas otra consulta, escribe: *Cita*.")
                        estado_actual = "inicio"
                        actualizar_confirmacion_cita(cita['documento'], respuesta)

                    elif respuesta.strip().lower() != ultimo_mensaje_enviado.strip().lower():
                        enviar_mensaje(numero_contacto, "❓ Por favor, responde con *si* o *no*.")
                        ultimo_mensaje_enviado = "por favor, responde con si o no."

            time.sleep(5)
    except Exception as e:
        print(f"❌ Error en el chatbot: {e}")

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

    

leer_mensajes("+573135360339")


