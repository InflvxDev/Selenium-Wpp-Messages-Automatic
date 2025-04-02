from enum import Enum, auto
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

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
    cita_actual: Optional['Cita'] = None
    ultimo_mensaje: Optional[str] = None
    ultimo_mensaje_bloqueo: Optional[datetime] = None
    tipo_documento: Optional[str] = None
    ultima_interaccion: datetime = datetime.now()
    bloqueado_hasta: Optional[datetime] = None

class WhatsAppMessage(BaseModel):
    from_num: str
    message: str
    timestamp: datetime

# Modelo de Cita movido aquí desde database.py
class Cita(BaseModel):
    id: Optional[int] = None
    tipoDocumento: str
    documento: str
    nombrePaciente: str
    especialidad: str
    nombreMedico: str
    fechaCita: str
    telefonoPaciente: str
    confirmacionCita: Optional[str] = None