from config import supabase
from datetime import datetime, timedelta

def buscar_cita(tipo_documento:str ,documento):
    """Busca una cita en la base de datos por documento."""
    try:
        response = supabase.table("Citas").select("*").eq("tipoDocumento", tipo_documento.upper()).eq("documento", documento).execute()

        if response.data and len(response.data) > 0:
            return response.data[0]  # Devuelve la primera cita encontrada
        else:
            return None
    except Exception as e:
        print(f"Error al consultar la cita: {e}")
        return None
    
def actualizar_confirmacion_cita(documento, confirmacion):
    """Actualiza la confirmación de la cita en la base de datos."""
    try:
        response = supabase.table("Citas").update({"confirmacionCita": confirmacion}).eq("documento", documento).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error al actualizar la confirmación de la cita: {e}")
        return None
    
def obtener_citas_proximas():
    try:
        fecha_objetivo = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")

        response = supabase.table("Citas").select("*").eq("fechaCita", fecha_objetivo).execute()

        return response.data if response.data else []
    
    except Exception as e:
        print(f"Error al obtener citas próximas: {e}")
        return []