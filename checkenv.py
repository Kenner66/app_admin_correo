from dotenv import load_dotenv
import os
from django.conf import settings

# Cargar las variables del archivo .env
load_dotenv()

# Imprimir los valores de las variables de entorno
print("MS_CLIENT_ID por os.getenv:", os.getenv("MS_CLIENT_ID"))
print("MS_CLIENT_SECRET por os.getenv:", os.getenv("MS_CLIENT_SECRET"))

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from django.conf import settings

print("MS_CLIENT_ID por settings:", settings.MS_CLIENT_ID)

