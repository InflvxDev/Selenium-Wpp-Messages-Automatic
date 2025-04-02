from datetime import datetime, timedelta
from typing import List, Optional
from src.core import supabase, logger, Cita


def _validar_documento(documento: str) -> bool:
    if not documento.isdigit():
        logger.warning(f"Documento no numérico: {documento}")
        return False
    return True

def _valifar_confirmacion(confirmacion: str) -> bool:
    if confirmacion.lower() not in ["si", "no"]:
        logger.warning(f"El valor de confirmación {confirmacion} no es válido. Debe ser 'si' o 'no'.")
        return False
    return True

def buscar_cita(tipo_documento: str, documento: str) -> Optional[Cita]:
    if not _validar_documento(documento):
        return None
    
    try:
        response = supabase.table("Citas").select("*").eq("tipoDocumento", tipo_documento.upper()).eq("documento", documento).limit(1).execute()
        return Cita(**response.data[0]) if response.data else None
  
    except Exception as e:
        logger.error(f"Error al buscar cita: {e}", exc_info=True)
        return None
    
def actualizar_confirmacion_cita(documento: str, confirmacion: str) -> bool:
    if not _validar_documento(documento) or not _valifar_confirmacion(confirmacion):
        return False
    
    try:
        response = supabase.table("Citas").update({"confirmacionCita": confirmacion}).eq("documento", documento).execute()
        return True if response.data else False
    
    except Exception as e:
        logger.error(f"Error al actualizar la confirmación de la cita: {e}", exc_info=True)
        return False
    
def obtener_citas_proximas(dias: int = 3) -> List[Cita]:
    try:
        fecha_objetivo = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")
        response = supabase.table("Citas").select("*").eq("fechaCita", fecha_objetivo).execute()
        return [Cita(**cita) for cita in response.data] if response.data else []
    
    except Exception as e:
        logger.error(f"Error al obtener citas próximas: {e}", exc_info=True)
        return []