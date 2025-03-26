import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager

SESSION_DIR = r"C:\Users\sebas\AppData\Local\Microsoft\Edge\User Data"
EDGE_DRIVER_PATH = EdgeChromiumDriverManager().install()


options = Options()
options.add_argument("--start-maximized")
options.add_argument(f"--user-data-dir={SESSION_DIR}")
options.add_argument("--no-sandbox") 


driver = None

def iniciar_driver():
    """Inicia el WebDriver solo si no está inicializado."""
    global driver
    if driver is None:
        try:
            service = Service(executable_path=EDGE_DRIVER_PATH)
            driver = webdriver.Edge(service=service, options=options)
            driver.get("https://web.whatsapp.com/")
            print("🔄 Inicializando sesión de WhatsApp...")

            # Esperar carga inicial (verificar lista de chats)
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//div[@role="grid"]'))
            )
        except Exception as e:
            print(f"❌ Error crítico al iniciar el navegador: {str(e)}")
            driver.quit()
            exit()
    return driver

def enviar_mensaje(contacto, mensaje):
    """Envía un mensaje de WhatsApp."""
    try:
        driver = iniciar_driver()
        url = f"https://web.whatsapp.com/send?phone={contacto}&text={mensaje}"
        driver.get(url)
        
        time.sleep(8)

        driver.find_element(By.XPATH, "//footer//button[@data-tab='11' and @aria-label='Enviar']").click()
        print("✅ Mensaje enviado con éxito!")

        time.sleep(5)
    except Exception as e:
        print(f"❌ Error al enviar mensaje a {contacto}: {e}")


