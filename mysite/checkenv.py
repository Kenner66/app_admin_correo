from dotenv import load_dotenv
import os

# Cargar las variables del archivo .env
load_dotenv()

# Imprimir los valores de las variables de entorno
print("MS_CLIENT_ID:", os.getenv("MS_CLIENT_ID"))
print("MS_CLIENT_SECRET:", os.getenv("MS_CLIENT_SECRET"))
