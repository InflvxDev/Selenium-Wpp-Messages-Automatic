import datetime

def log(mensaje):
    """Guarda logs de actividad."""
    try:
        with open("logs/chatbot.log", "a") as file:
            file.write(f"{datetime.datetime.now()} - {mensaje}\n")
    except Exception as e:
        print(f"Error al escribir en el log: {e}")

