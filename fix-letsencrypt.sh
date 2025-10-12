#!/bin/bash

echo "🔧 Fixing Let's Encrypt Setup"
echo "=============================="

# Stop containers
echo "1. Stopping containers..."
docker compose -f docker-compose.prod.ssl.yml down

# Clean up old certificates
echo "2. Cleaning up old certificate attempts..."
sudo rm -rf certbot/conf/live/tracker.jayvandamme.be
sudo rm -rf certbot/conf/archive/tracker.jayvandamme.be
sudo rm -rf certbot/conf/renewal/tracker.jayvandamme.be.conf

# Ensure certbot directories exist with correct permissions
echo "3. Creating certbot directories..."
mkdir -p certbot/conf
mkdir -p certbot/www/.well-known/acme-challenge
chmod -R 755 certbot/www

# Create a test file to verify webroot is accessible
echo "test" > certbot/www/.well-known/acme-challenge/test.txt

# Make sure we're using the init config (HTTP only)
echo "4. Using HTTP-only nginx config for certificate acquisition..."
if [ ! -f "nginx/nginx-ssl.conf" ]; then
    cp nginx/nginx.conf nginx/nginx-ssl.conf
fi
cp nginx/nginx-init.conf nginx/nginx.conf

# Update domain in nginx-init.conf if needed
sed -i 's/yourdomain.com/tracker.jayvandamme.be/g' nginx/nginx-init.conf
sed -i 's/yourdomain.com/tracker.jayvandamme.be/g' nginx/nginx.conf

# Start nginx only (not certbot yet)
echo "5. Starting nginx..."
docker compose -f docker-compose.prod.ssl.yml up -d nginx

# Wait for nginx to be ready
echo "6. Waiting for nginx to start..."
sleep 5

# Test that challenge directory is accessible
echo "7. Testing challenge directory accessibility..."
curl -v http://tracker.jayvandamme.be/.well-known/acme-challenge/test.txt

echo ""
echo "=============================="
echo "If you see 'test' above, the challenge directory is accessible!"
echo ""
echo "Now run: ./init-letsencrypt.sh"
echo "=============================="
