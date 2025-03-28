from config import supabase

def buscar_cita(documento):
    """Busca una cita en la base de datos por documento."""
    try:
        response = supabase.table("Citas").select("*").eq("documento", documento).execute()
        return response.data[0] if response.data else None
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