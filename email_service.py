import os
import smtplib
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import logger


# Cargar variables de entorno
load_dotenv()

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.sender_email = os.getenv("SENDER_EMAIL")
        self.receive_email = os.getenv("RECEIVE_EMAIL")

        if not all([self.smtp_server, self.smtp_user, self.smtp_password]):
            logger.error("Faltan configuraciones SMTP en las variables de entorno")
            raise ValueError("Configuración SMTP incompleta")

    def enviar_email_cancelacion(self, cita):
        """Envía email de cancelación usando Gmail"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.receive_email 
            msg['Subject'] = f"Cancelación de cita - {cita.nombrePaciente}"
            
            body = f"""
            <h2>Cancelación de cita médica</h2>
            <p>Se ha cancelado la siguiente cita:</p>
            <ul>
                <li><strong>Paciente:</strong> {cita.nombrePaciente}</li>
                <li><strong>Documento:</strong> {cita.tipoDocumento} {cita.documento}</li>
                <li><strong>Especialidad:</strong> {cita.especialidad}</li>
                <li><strong>Médico:</strong> {cita.nombreMedico}</li>
                <li><strong>Fecha:</strong> {cita.fechaCita}</li>
                <li><strong>Teléfono:</strong> {cita.telefonoPaciente}</li>
            </ul>
            """
            
            msg.attach(MIMEText(body, 'html'))  # Usamos HTML para mejor formato

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(
                    self.sender_email, 
                    msg['To'], 
                    msg.as_string()
                )
                
            logger.info(f"Email enviado a {msg['To']} sobre cancelación de cita {cita.id}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            logger.error("Error de autenticación con el servidor SMTP")
            return False
        except Exception as e:
            logger.error(f"Error al enviar email: {str(e)}")
            return False