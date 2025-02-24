# Usa una imagen ligera de Python
FROM python:3.13-slim  

# Define el directorio de trabajo dentro del contenedor
WORKDIR /app  

# Copia el archivo de dependencias
COPY requirements.txt requirements.txt  

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt  

# Copia todos los archivos del proyecto al contenedor
COPY . .  

# Comando para ejecutar el bot en Railway
CMD ["python", "bot_telegram.py"]
