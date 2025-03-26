from config import supabase

def buscar_cita(documento):
    """Busca una cita en la base de datos por documento."""
    try:
        response = supabase.table("Cita").select("*").eq("documento", documento).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error al consultar la cita: {e}")
        return None