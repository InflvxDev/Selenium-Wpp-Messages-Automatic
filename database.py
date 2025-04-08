from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from config import supabase, logger
import logging

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



def buscar_cita(tipo_documento: str, documento: str) -> Optional[Cita]:
    """Busca una cita en la base de datos por documento con validación."""
    try:

        if not documento.isdigit():
            logger.warning(f"Documento no numérico: {documento}")
            return None

        fecha_actual = datetime.now().strftime("%Y-%m-%d")

        response = supabase.table("Citas").select("*").eq(
            "tipoDocumento", tipo_documento.upper()
        ).eq("documento", documento).execute()

        citas_filtradas = []

        for cita in response.data:
            if cita["fechaCita"] >= fecha_actual:
                citas_filtradas.append(cita)

        return [Cita(**cita) for cita in citas_filtradas] if citas_filtradas else None
    except Exception as e:
        logger.error(f"Error al buscar cita: {e}", exc_info=True)
        return None
    
def actualizar_confirmacion_cita(cita_id: int, confirmacion : str) -> bool:
    """Actualiza la confirmación de la cita en la base de datos."""
    try:
        confirmacion = confirmacion.lower()
        if confirmacion not in ["si", "no"]:
            logger.warning(f"El valor de confirmación {confirmacion} no es válido. Debe ser 'si' o 'no'.")
            return False

        response = supabase.table("Citas").update({"confirmacionCita": confirmacion}).eq("id", cita_id).execute()

        return True if response.data else False
    
    except Exception as e:
        logger.error(f"Error al actualizar la confirmación de la cita: {e}", exc_info=True)
        return False
    
def obtener_citas_proximas(dias: int = 3) -> List[Cita]:
    try:
        fecha_objetivo = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")

        response = supabase.table("Citas").select("*").eq("fechaCita", fecha_objetivo).execute()
     

        return [Cita(**cita) for cita in response.data] if response.data else []
    
    except Exception as e:
        logger.error(f"Error al obtener citas próximas: {e}", exc_info=True)
        return []