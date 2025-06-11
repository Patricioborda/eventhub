#!/bin/bash

# Esperar a que la base de datos esté lista (si es necesario)
# echo "Esperando a que la base de datos esté lista..."
# while ! nc -z db 5432; do
#   sleep 0.1
# done
# echo "Base de datos lista!"

# Aplicar migraciones
echo "Aplicando migraciones..."
python manage.py migrate

# Iniciar el servidor
echo "Iniciando servidor Django..."
exec python manage.py runserver 0.0.0.0:8000 