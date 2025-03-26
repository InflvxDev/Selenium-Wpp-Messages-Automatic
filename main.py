import time
from whatsapp import enviar_mensaje, iniciar_driver
from database import buscar_cita
from selenium.webdriver.common.by import By

driver = iniciar_driver()

estado_usuarios = {}

def leer_mensajes(numero_contacto):
    """Lee mensajes nuevos y responde según el flujo de conversación."""
    print("✅  Inicializado sesión de WhatsApp Correctamente")
    try:
        enviar_mensaje(numero_contacto, "¿Quieres consultar una cita? Responde 'Si' o 'No'.")    
        time.sleep(10)
        
        while True:
            
            respuesta = obtener_ultimo_mensaje()
            if respuesta:
                print(f"📩 Respuesta recibida: {respuesta}")
                
                if respuesta.lower() == "si":
                    enviar_mensaje(numero_contacto, "Por favor, ingresa tu tipo y número de documento.")
                elif respuesta.lower() == "no":
                    enviar_mensaje(numero_contacto, "¡Entendido! Si necesitas algo más, avísame.")
                    break
                else:
                    enviar_mensaje(numero_contacto, "No entendí tu respuesta. Responde 'Si' o 'No'.")

            time.sleep(10)
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

    

leer_mensajes("+573046142863")


