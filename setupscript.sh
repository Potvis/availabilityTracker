#!/bin/bash

# Kangoo Jumping Platform - Setup Script
# This script creates the directory structure for the project

echo "🦘 Setting up Kangoo Jumping Platform..."

# Create main directories
mkdir -p backend/kangoo_project
mkdir -p backend/members
mkdir -p backend/cards
mkdir -p backend/equipment
mkdir -p backend/sessions
mkdir -p backend/templates/admin/sessions/csvimport
mkdir -p backend/media/csv_imports
mkdir -p backend/staticfiles

# Create __init__.py files for Python packages
touch backend/kangoo_project/__init__.py
touch backend/members/__init__.py
touch backend/cards/__init__.py
touch backend/equipment/__init__.py
touch backend/sessions/__init__.py

# Create apps.py files for each app
cat > backend/members/apps.py << 'EOF'
from django.apps import AppConfig

class MembersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'members'
    verbose_name = 'Leden'
EOF

cat > backend/cards/apps.py << 'EOF'
from django.apps import AppConfig

class CardsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cards'
    verbose_name = 'Sessiekaarten'
EOF

cat > backend/equipment/apps.py << 'EOF'
from django.apps import AppConfig

class EquipmentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'equipment'
    verbose_name = 'Apparatuur'
EOF

cat > backend/sessions/apps.py << 'EOF'
from django.apps import AppConfig

class SessionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sessions'
    verbose_name = 'Sessies'
EOF

echo "✅ Directory structure created!"
echo ""
echo "📝 Next steps:"
echo "1. Copy all the provided Python files into their respective directories"
echo "2. Copy docker-compose.yml to the root directory"
echo "3. Run: chmod +x backend/entrypoint.sh"
echo "4. Run: docker-compose up --build"
echo ""
echo "🎯 The application will be available at http://localhost:8000"
echo "🔐 Default admin credentials: admin / admin123"