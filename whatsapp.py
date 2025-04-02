import os
import time
import logging
from typing import Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException

logger = logging.getLogger(__name__)

class WhatsAppDriver:
    def __init__(self):
        self.driver = None
        self.max_reintentos = 3
        self.reintento_espera = 5  # segundos
        self.session_dir = os.path.expanduser("~/.config/ohibot/whatsapp_session")
        
        # Asegurar que el directorio existe
        os.makedirs(self.session_dir, exist_ok=True)

    def iniciar_driver(self) -> Optional[webdriver.Edge]:
        """Inicia el WebDriver con manejo de reconexión."""
        if self.driver and self._verificar_conexion_activa():
            return self.driver

        for intento in range(self.max_reintentos):
            try:
                if self.driver:
                    self.driver.quit()

                options = Options()
                options.add_argument("--start-maximized")
                options.add_argument(f"--user-data-dir={self.session_dir}")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")

                service = Service(EdgeChromiumDriverManager().install())
                self.driver = webdriver.Edge(service=service, options=options)
                self.driver.get("https://web.whatsapp.com/")

                WebDriverWait(self.driver, 30).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@role="grid"]'))
                )
                logger.info("Sesión de WhatsApp iniciada correctamente")
                return self.driver

            except Exception as e:
                logger.error(f"Intento {intento + 1} fallido: {str(e)}")
                if intento < self.max_reintentos - 1:
                    time.sleep(self.reintento_espera)
                else:
                    logger.critical("No se pudo iniciar el driver después de varios intentos")
                    return None

    def _verificar_conexion_activa(self) -> bool:
        """Verifica si la sesión del navegador sigue activa."""
        try:
            if not self.driver:
                return False
            # Comando simple para verificar conexión
            self.driver.current_url
            return True
        except (InvalidSessionIdException, WebDriverException):
            return False

    def enviar_mensaje(self, contacto: str, mensaje: str) -> bool:
        """Envía mensaje con manejo de reconexión automática."""
        for intento in range(self.max_reintentos):
            try:
                if not self._verificar_conexion_activa():
                    self.iniciar_driver()
                    if not self.driver:
                        return False

                url = f"https://web.whatsapp.com/send?phone={contacto}&text={mensaje}"
                self.driver.get(url)

                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"]'))
                )
                time.sleep(2)

                boton_enviar = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Enviar"]'))
                )
                boton_enviar.click()
                logger.info(f"Mensaje enviado a {contacto}")
                return True

            except InvalidSessionIdException:
                logger.warning(f"Sesión inválida, reintentando... (Intento {intento + 1})")
                self.driver = None
                time.sleep(self.reintento_espera)
            except Exception as e:
                logger.error(f"Error al enviar mensaje: {str(e)}")
                if intento < self.max_reintentos - 1:
                    time.sleep(self.reintento_espera)
                else:
                    return False
        return False

    def cerrar(self):
        """Cierra el driver de manera segura."""
        if self.driver:
            self.driver.quit()
            self.driver = None

# Instancia global del driver
whatsapp_driver = WhatsAppDriver()