# Uso la imagen oficial de Python
FROM python:3.11-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar dependencias primero para aprovechar el cache de Docker
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de los archivos del proyecto
COPY . .

# Exponer el puerto que usará (default: 8000)
EXPOSE 8000

# Comando por defecto al levantar el contenedor
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
