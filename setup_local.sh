#!/bin/bash

# Jump4Fun Client Booking System - Local Setup Script
# This script automates the setup of the booking system on your local machine

set -e  # Exit on error

echo "🦘 Jump4Fun Client Booking System - Local Setup"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "ℹ $1"
}

# Check if we're in the right directory
if [ ! -d "backend" ]; then
    print_error "Error: backend directory not found. Are you in the repository root?"
    echo "Please run this script from your Jump4Fun repository root directory."
    exit 1
fi

print_success "Found backend directory"

# Check if git is initialized
if [ ! -d ".git" ]; then
    print_error "Error: Not a git repository. Please run this from the repository root."
    exit 1
fi

print_success "Git repository detected"

# Get current branch
current_branch=$(git branch --show-current)
print_info "Current branch: $current_branch"

# Ask if user wants to create new branch
echo ""
echo "Do you want to create a new feature branch? (recommended)"
read -p "Create new branch 'feature/client-booking-system'? (y/n): " create_branch

if [ "$create_branch" = "y" ]; then
    # Check if branch already exists
    if git show-ref --verify --quiet refs/heads/feature/client-booking-system; then
        print_warning "Branch 'feature/client-booking-system' already exists"
        read -p "Switch to existing branch? (y/n): " switch_branch
        if [ "$switch_branch" = "y" ]; then
            git checkout feature/client-booking-system
            print_success "Switched to existing branch"
        fi
    else
        git checkout -b feature/client-booking-system
        print_success "Created and switched to new branch: feature/client-booking-system"
    fi
else
    print_warning "Continuing on branch: $current_branch"
fi

echo ""
echo "📂 Creating directory structure..."

# Create accounts app structure
mkdir -p backend/accounts/management/commands
mkdir -p backend/accounts/migrations

print_success "Created accounts app directories"

# Check if source files exist
SOURCE_DIR="."
if [ -d "jump4fun_booking/backend" ]; then
    SOURCE_DIR="jump4fun_booking"
    print_success "Found implementation files in jump4fun_booking/"
elif [ -d "../jump4fun_booking/backend" ]; then
    SOURCE_DIR="../jump4fun_booking"
    print_success "Found implementation files in ../jump4fun_booking/"
else
    print_error "Cannot find implementation files."
    echo ""
    echo "Please ensure the jump4fun_booking directory is in one of these locations:"
    echo "  - Current directory: ./jump4fun_booking/"
    echo "  - Parent directory: ../jump4fun_booking/"
    echo ""
    echo "Download from: /mnt/user-data/outputs/jump4fun_booking/"
    exit 1
fi

echo ""
echo "📋 Copying implementation files..."

# Copy accounts app files
cp "$SOURCE_DIR/backend/accounts/__init__.py" backend/accounts/ 2>/dev/null || print_warning "Could not copy accounts/__init__.py"
cp "$SOURCE_DIR/backend/accounts/admin.py" backend/accounts/ 2>/dev/null || print_warning "Could not copy accounts/admin.py"
cp "$SOURCE_DIR/backend/accounts/apps.py" backend/accounts/ 2>/dev/null || print_warning "Could not copy accounts/apps.py"
cp "$SOURCE_DIR/backend/accounts/forms.py" backend/accounts/ 2>/dev/null || print_warning "Could not copy accounts/forms.py"
cp "$SOURCE_DIR/backend/accounts/middleware.py" backend/accounts/ 2>/dev/null || print_warning "Could not copy accounts/middleware.py"
cp "$SOURCE_DIR/backend/accounts/models.py" backend/accounts/ 2>/dev/null || print_warning "Could not copy accounts/models.py"
cp "$SOURCE_DIR/backend/accounts/signals.py" backend/accounts/ 2>/dev/null || print_warning "Could not copy accounts/signals.py"
cp "$SOURCE_DIR/backend/accounts/urls.py" backend/accounts/ 2>/dev/null || print_warning "Could not copy accounts/urls.py"
cp "$SOURCE_DIR/backend/accounts/views.py" backend/accounts/ 2>/dev/null || print_warning "Could not copy accounts/views.py"

print_success "Copied accounts app core files"

# Copy management commands
cp "$SOURCE_DIR/backend/accounts/management/__init__.py" backend/accounts/management/ 2>/dev/null || print_warning "Could not copy management/__init__.py"
cp "$SOURCE_DIR/backend/accounts/management/commands/__init__.py" backend/accounts/management/commands/ 2>/dev/null || print_warning "Could not copy commands/__init__.py"
cp "$SOURCE_DIR/backend/accounts/management/commands/create_user_accounts_for_members.py" backend/accounts/management/commands/ 2>/dev/null || print_warning "Could not copy management command"

print_success "Copied management commands"

# Copy migrations
cp "$SOURCE_DIR/backend/accounts/migrations/__init__.py" backend/accounts/migrations/ 2>/dev/null || print_warning "Could not copy migrations/__init__.py"
cp "$SOURCE_DIR/backend/accounts/migrations/0001_initial.py" backend/accounts/migrations/ 2>/dev/null || print_warning "Could not copy migration 0001"

print_success "Copied migrations"

# Copy equipment assignment
cp "$SOURCE_DIR/backend/equipment/assignment.py" backend/equipment/ 2>/dev/null || print_warning "Could not copy equipment assignment"

print_success "Copied equipment assignment module"

# Copy bookings schedules
cp "$SOURCE_DIR/backend/bookings/schedule_models.py" backend/bookings/ 2>/dev/null || print_warning "Could not copy schedule_models.py"
cp "$SOURCE_DIR/backend/bookings/schedule_admin.py" backend/bookings/ 2>/dev/null || print_warning "Could not copy schedule_admin.py"
cp "$SOURCE_DIR/backend/bookings/migrations/0004_add_session_schedules.py" backend/bookings/migrations/ 2>/dev/null || print_warning "Could not copy schedule migration"

print_success "Copied bookings schedule files"

echo ""
echo "⚙️  Updating configuration files..."

# Function to check if a line exists in a file
line_exists() {
    grep -Fxq "$1" "$2"
}

# Update settings.py
if ! line_exists "    'accounts'," backend/kangoo_project/settings.py; then
    # Find INSTALLED_APPS and add accounts after bookings
    sed -i "/    'bookings',/a\\    'accounts',  # Client booking system" backend/kangoo_project/settings.py
    print_success "Added 'accounts' to INSTALLED_APPS"
else
    print_warning "'accounts' already in INSTALLED_APPS"
fi

# Add middleware
if ! line_exists "    'accounts.middleware.ProfileCompletionMiddleware'," backend/kangoo_project/settings.py; then
    # Add to end of MIDDLEWARE list
    sed -i "/^MIDDLEWARE = \[/,/^\]/ s/\]$/    'accounts.middleware.ProfileCompletionMiddleware',  # Profile completion enforcement\n]/" backend/kangoo_project/settings.py
    print_success "Added ProfileCompletionMiddleware to MIDDLEWARE"
else
    print_warning "ProfileCompletionMiddleware already in MIDDLEWARE"
fi

# Update urls.py
if ! line_exists "    path('accounts/', include('accounts.urls'))," backend/kangoo_project/urls.py; then
    sed -i "/urlpatterns = \[/a\\    path('accounts/', include('accounts.urls')),  # Account management" backend/kangoo_project/urls.py
    print_success "Added accounts URLs"
else
    print_warning "accounts URLs already configured"
fi

# Update bookings/models.py
if ! line_exists "from .schedule_models import SessionSchedule, SessionBooking" backend/bookings/models.py; then
    echo -e "\n# Import schedule models\nfrom .schedule_models import SessionSchedule, SessionBooking" >> backend/bookings/models.py
    print_success "Added schedule models import to bookings/models.py"
else
    print_warning "schedule models already imported in bookings/models.py"
fi

# Update bookings/admin.py
if ! grep -q "from . import schedule_admin" backend/bookings/admin.py; then
    sed -i "1i # Import schedule admin (auto-registers via decorators)\nfrom . import schedule_admin\n" backend/bookings/admin.py
    print_success "Added schedule_admin import to bookings/admin.py"
else
    print_warning "schedule_admin already imported in bookings/admin.py"
fi

# Create .env.local if it doesn't exist
if [ ! -f "backend/.env.local" ]; then
    cat > backend/.env.local <<EOF
# Local Development Environment Variables
# DO NOT commit this file to git!

# Database
DB_PASSWORD=kangoo_dev_password_local
DATABASE_URL=postgresql://kangoo:kangoo_dev_password_local@localhost:5432/kangoo_dev

# Django
SECRET_KEY=local-dev-secret-key-$(openssl rand -hex 16)
DEBUG=True

# Hosts
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:8001,http://127.0.0.1:8001
EOF
    print_success "Created .env.local"
else
    print_warning ".env.local already exists"
fi

# Add .env.local to .gitignore
if ! grep -q ".env.local" .gitignore 2>/dev/null; then
    echo -e "\n# Local development environment\n.env.local" >> .gitignore
    print_success "Added .env.local to .gitignore"
else
    print_warning ".env.local already in .gitignore"
fi

# Create docker-compose.local.yml if it doesn't exist
if [ ! -f "docker-compose.local.yml" ]; then
    cp "$SOURCE_DIR/docker-compose.local.yml" docker-compose.local.yml 2>/dev/null || print_warning "Could not copy docker-compose.local.yml"
    if [ -f "docker-compose.local.yml" ]; then
        print_success "Created docker-compose.local.yml"
    fi
fi

echo ""
echo "📊 Verification..."

# Verify key files exist
files_ok=true

if [ -f "backend/accounts/models.py" ]; then
    print_success "accounts app files present"
else
    print_error "accounts app files missing"
    files_ok=false
fi

if [ -f "backend/equipment/assignment.py" ]; then
    print_success "equipment assignment present"
else
    print_error "equipment assignment missing"
    files_ok=false
fi

if [ -f "backend/bookings/schedule_models.py" ]; then
    print_success "schedule models present"
else
    print_error "schedule models missing"
    files_ok=false
fi

echo ""
echo "================================================"
echo ""

if [ "$files_ok" = true ]; then
    print_success "Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Start Docker containers:"
    echo "   docker-compose -f docker-compose.local.yml up -d"
    echo ""
    echo "2. Run migrations:"
    echo "   docker-compose -f docker-compose.local.yml exec web python manage.py migrate"
    echo ""
    echo "3. Create superuser:"
    echo "   docker-compose -f docker-compose.local.yml exec web python manage.py createsuperuser"
    echo ""
    echo "4. Access admin interface:"
    echo "   http://localhost:8001/admin/"
    echo ""
    echo "5. Commit your changes:"
    echo "   git add ."
    echo "   git commit -m 'Add client booking system'"
    echo "   git push origin $(git branch --show-current)"
    echo ""
    echo "For detailed instructions, see: LOCAL_DEVELOPMENT_SETUP.md"
else
    print_error "Setup completed with errors"
    echo ""
    echo "Some files could not be copied. Please:"
    echo "1. Check that jump4fun_booking directory is in the correct location"
    echo "2. Manually copy missing files"
    echo "3. Re-run this script or follow LOCAL_DEVELOPMENT_SETUP.md"
fi

echo ""