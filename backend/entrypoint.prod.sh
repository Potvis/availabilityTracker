#!/bin/bash

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# Run migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput --clear

# Create superuser if it doesn't exist
python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@kangoo.be', 'admin123')
    print('Superuser created: admin / admin123')
else:
    print('Superuser already exists')
END

exec "$@"