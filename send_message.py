import time
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


SESSION_DIR = r"C:\Users\sebas\AppData\Local\Microsoft\Edge\User Data"
EDGE_DRIVER_PATH = EdgeChromiumDriverManager().install()


options = Options()
options.add_argument(f"--user-data-dir={SESSION_DIR}")
options.add_argument("--start-maximized")
options.add_argument("--disable-infobars")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--remote-debugging-port=9222")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)


try:
    service = Service(executable_path=EDGE_DRIVER_PATH)
    driver = webdriver.Edge(service=service, options=options)
    driver.get("https://web.whatsapp.com/")
    print("🔄 Inicializando sesión de WhatsApp...")

    # Esperar carga inicial (verificar lista de chats)
    WebDriverWait(driver, 45).until(
        EC.presence_of_element_located((By.XPATH, '//div[@role="grid"]'))
    )
except Exception as e:
    print(f"❌ Error crítico al iniciar el navegador: {str(e)}")
    driver.quit()
    exit()


def enviar_mensaje(numero, mensaje):
    try:
        # Codificar mensaje para URL
        mensaje_codificado = quote(mensaje)
        url = f"https://web.whatsapp.com/send?phone={numero}&text={mensaje_codificado}"
        
        driver.get(url)
        print("🔄 Cargando chat...")

        time.sleep(8)

        driver.find_element(By.XPATH, "//footer//button[@data-tab='11' and @aria-label='Enviar']").click()

        print("✅ Mensaje enviado con éxito!")
        time.sleep(3)

    except Exception as e:
        print(f"❌ Error al enviar mensaje: {str(e)}")
        driver.save_screenshot("error.png")


enviar_mensaje("+573135360339", "Hola desde Selenium!, Este es un mensaje automatico xd")
driver.quit()
