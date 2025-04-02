import json
from datetime import datetime
from typing import Dict
from .models import SesionUsuario, Cita
from src.core import logger

class StateManager:
    def __init__(self, file_path: str = "estado_usuarios.json"):
        self.file_path = file_path
        self.sessions: Dict[str, SesionUsuario] = {}
        self.load_state()

    def load_state(self):
        try:
            with open(self.file_path, "r") as f:
                data = json.load(f)
                for number, session_data in data.items():
                    blocked_until = (
                        datetime.fromisoformat(session_data["bloqueado_hasta"])
                        if session_data.get("bloqueado_hasta")
                        else None
                    )
                    self.sessions[number] = SesionUsuario(
                        estado=session_data["estado"],
                        intentos=session_data["intentos"],
                        tipo_documento=session_data.get("tipo_documento"),
                        ultimo_mensaje=session_data.get("ultimo_mensaje"),
                        ultima_interaccion=datetime.fromisoformat(session_data["ultima_interaccion"]),
                        bloqueado_hasta=blocked_until,
                        cita_actual=Cita(**session_data["cita_actual"]) if session_data.get("cita_actual") else None
                    )
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Error loading state: {e}")

    def save_state(self):
        serializable_state = {
            number: {
                "estado": session.estado.name,
                "intentos": session.intentos,
                "tipo_documento": session.tipo_documento,
                "ultimo_mensaje": session.ultimo_mensaje,
                "ultima_interaccion": session.ultima_interaccion.isoformat(),
                "bloqueado_hasta": session.bloqueado_hasta.isoformat() if session.bloqueado_hasta else None,
                "cita_actual": session.cita_actual.model_dump() if session.cita_actual else None
            }
            for number, session in self.sessions.items()
        }
        try:
            with open(self.file_path, "w") as f:
                json.dump(serializable_state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {e}")