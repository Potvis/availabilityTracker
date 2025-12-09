#!/bin/bash

# Setup script for hourly card charging
# This creates the management command and sets up cron

echo "🔧 Setting up hourly card charging..."
echo ""

# Create directory structure if it doesn't exist
mkdir -p backend/bookings/management/commands
touch backend/bookings/management/__init__.py
touch backend/bookings/management/commands/__init__.py

echo "1️⃣ Directory structure created"

# Test the command first (dry run)
echo ""
echo "2️⃣ Testing command (dry run)..."
docker compose -f docker-compose.prod.ssl.yml exec web python manage.py charge_past_sessions --dry-run

echo ""
read -p "Does the dry run look correct? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Aborting setup"
    exit 1
fi

# Create cron script
cat > charge_sessions_cron.sh << 'CRONEOF'
#!/bin/bash
# Cron script to charge past sessions hourly
cd /root/docker/availabilityTracker
docker compose -f docker-compose.prod.ssl.yml exec -T web python manage.py charge_past_sessions >> /var/log/kangoo_charge.log 2>&1
CRONEOF

chmod +x charge_sessions_cron.sh

echo ""
echo "3️⃣ Created cron script: charge_sessions_cron.sh"

# Add to crontab
echo ""
echo "4️⃣ Adding to crontab (runs every hour at minute 5)..."

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "charge_sessions_cron.sh"; then
    echo "⚠️  Cron job already exists, skipping..."
else
    # Add new cron job
    (crontab -l 2>/dev/null; echo "5 * * * * /root/docker/availabilityTracker/charge_sessions_cron.sh") | crontab -
    echo "✅ Cron job added"
fi

# Show current crontab
echo ""
echo "📋 Current crontab:"
crontab -l | grep -v "^#"

echo ""
echo "=================================="
echo "✅ Setup complete!"
echo "=================================="
echo ""
echo "The command will now run:"
echo "  • Every hour at :05 (e.g., 13:05, 14:05, 15:05)"
echo "  • Logs saved to: /var/log/kangoo_charge.log"
echo ""
echo "Manual commands:"
echo "  • Test (dry run): docker compose -f docker-compose.prod.ssl.yml exec web python manage.py charge_past_sessions --dry-run"
echo "  • Run now: docker compose -f docker-compose.prod.ssl.yml exec web python manage.py charge_past_sessions"
echo "  • View logs: tail -f /var/log/kangoo_charge.log"
echo "  • Edit cron: crontab -e"
echo ""