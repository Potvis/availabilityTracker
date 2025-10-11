#!/bin/bash

# Wait for postgres using Python
echo "Waiting for postgres..."
python << END
import sys
import time
import psycopg2
import os

suggest_unrecoverable_after = 30
start = time.time()

# Read password from environment variable
db_password = os.environ.get('DB_PASSWORD', 'kangoo_dev_password')

while True:
    try:
        psycopg2.connect(
            dbname="kangoo",
            user="kangoo",
            password=db_password,  # USE ENVIRONMENT VARIABLE
            host="db",
            port="5432",
        )
        break
    except psycopg2.OperationalError as error:
        sys.stderr.write("Waiting for PostgreSQL to become available...\n")
        if time.time() - start > suggest_unrecoverable_after:
            sys.stderr.write("  This is taking longer than expected. The following exception may be indicative of an unrecoverable error: '{}'\n".format(error))
    time.sleep(1)
END

echo "PostgreSQL started"

# Run migrations
python manage.py makemigrations
python manage.py migrate

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

# Start server
exec "$@"