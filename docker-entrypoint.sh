#!/bin/bash

# Configurar variables de entorno para Django
export DJANGO_DEBUG=True
export DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Asegurarse de que los directorios existen y tienen los permisos correctos
mkdir -p /app/static /app/staticfiles
chmod -R 755 /app/static /app/staticfiles

# Esperar a que la base de datos esté lista (si es necesario)
# echo "Esperando a que la base de datos esté lista..."
# while ! nc -z db 5432; do
#   sleep 0.1
# done
# echo "Base de datos lista!"

# Aplicar migraciones
echo "Aplicando migraciones..."
python manage.py migrate

# Recolectar archivos estáticos
echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput --clear

# Iniciar el servidor
echo "Iniciando servidor Django..."
exec python manage.py runserver 0.0.0.0:8000 