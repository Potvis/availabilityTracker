# SSL/TLS Setup Guide - Let's Encrypt with Nginx

This guide will help you set up free SSL certificates from Let's Encrypt on your Nginx server.

## Prerequisites

✅ You have a domain name (e.g., `yourdomain.com`)
✅ DNS A record points to your server's public IP
✅ Ports 80 and 443 are open in your firewall
✅ No other service is using ports 80/443 (stop Pangolin if running)

## Step-by-Step Setup

### 1. Update Configuration Files

**Edit `init-letsencrypt.sh`** - Update these lines:

```bash
domains=(yourdomain.com www.yourdomain.com)  # Your actual domain(s)
email="your-email@example.com"               # Your email
staging=0                                     # Set to 1 for testing
```

**Edit `nginx/nginx.conf`** - Replace `yourdomain.com` with your actual domain (3 places):
- Line 6: `server_name yourdomain.com www.yourdomain.com;`
- Line 18: `server_name yourdomain.com www.yourdomain.com;`
- Line 21-22: Certificate paths

**Edit `.env.prod`** - Update hosts:

```env
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 2. Test with Staging First (Recommended)

Let's Encrypt has rate limits (5 certificates per week). Test with staging first:

```bash
# In init-letsencrypt.sh, set:
staging=1
```

### 3. Prepare the Environment

```bash
# Stop any existing containers
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.simple.yml down

# Stop Pangolin if running
sudo systemctl stop pangolin  # or however you stop it

# Verify ports are free
sudo lsof -i :80
sudo lsof -i :443
# Should return nothing
```

### 4. Initial Setup (Without SSL)

First, start with HTTP only to get certificates:

```bash
# Temporarily rename nginx.conf
mv nginx/nginx.conf nginx/nginx-ssl.conf
mv nginx/nginx-init.conf nginx/nginx.conf

# Start the stack
docker-compose -f docker-compose.prod.ssl.yml up -d

# Verify it's running
curl http://yourdomain.com/admin/login/
# Should return the login page
```

### 5. Run the Certificate Setup

```bash
# Make the script executable
chmod +x init-letsencrypt.sh

# Run the initialization script
./init-letsencrypt.sh
```

You should see output like:

```
### Preparing directories ...
### Downloading recommended TLS parameters ...
### Creating dummy certificate for yourdomain.com ...
### Starting nginx ...
### Deleting dummy certificate for yourdomain.com ...
### Requesting Let's Encrypt certificate for yourdomain.com ...
Saving debug log to /var/log/letsencrypt/letsencrypt.log
...
Successfully received certificate.
Certificate is saved at: /etc/letsencrypt/live/yourdomain.com/fullchain.pem
...
### Reloading nginx ...
```

### 6. Switch to SSL Configuration

```bash
# Stop containers
docker-compose -f docker-compose.prod.ssl.yml down

# Restore SSL configuration
mv nginx/nginx.conf nginx/nginx-init.conf.backup
mv nginx/nginx-ssl.conf nginx/nginx.conf

# Start with SSL
docker-compose -f docker-compose.prod.ssl.yml up -d

# Watch the logs
docker-compose -f docker-compose.prod.ssl.yml logs -f nginx
```

### 7. Test HTTPS

```bash
# Test HTTPS access
curl https://yourdomain.com/admin/login/

# Test HTTP redirect
curl -I http://yourdomain.com/
# Should return: HTTP/1.1 301 Moved Permanently

# Test SSL with detailed info
curl -vI https://yourdomain.com 2>&1 | grep -E "SSL|TLS|subject|issuer"
```

### 8. Verify with SSL Labs

Go to: https://www.ssllabs.com/ssltest/

Enter your domain and check the grade. You should get an A or A+ rating.

## If Using Staging Certificates

If you tested with `staging=1`, you'll see "Fake LE" certificates. To get real ones:

```bash
# Update init-letsencrypt.sh
staging=0  # Change to 0

# Remove staging certificates
sudo rm -rf certbot/conf/live
sudo rm -rf certbot/conf/archive
sudo rm -rf certbot/conf/renewal

# Run again
./init-letsencrypt.sh

# Restart
docker-compose -f docker-compose.prod.ssl.yml restart nginx
```

## Auto-Renewal

Certificates automatically renew via the certbot container. It checks twice daily and renews certificates within 30 days of expiry.

Verify auto-renewal works:

```bash
# Test renewal (dry run)
docker-compose -f docker-compose.prod.ssl.yml run --rm certbot renew --dry-run
```

## Troubleshooting

### Problem: "Port 80 already in use"

```bash
# Find what's using it
sudo lsof -i :80

# Stop the service
sudo systemctl stop nginx  # or apache2, or pangolin
```

### Problem: "Domain validation failed"

Check DNS is correctly configured:

```bash
# Check DNS resolves to your server
nslookup yourdomain.com
dig yourdomain.com

# Should return your server's public IP
```

### Problem: "Certificate not found"

Nginx is looking for certificates before they exist. Use the 2-step process:
1. Start with `nginx-init.conf` (HTTP only)
2. Get certificates
3. Switch to `nginx.conf` (HTTPS)

### Problem: Rate limit exceeded

You hit Let's Encrypt's rate limit (5 certs/week). Either:
- Wait a week
- Use staging mode for testing
- Use a subdomain (e.g., `app.yourdomain.com`)

### Problem: HTTPS works but HTTP doesn't redirect

Check nginx logs:

```bash
docker-compose -f docker-compose.prod.ssl.yml logs nginx
```

Verify the HTTP server block is present in `nginx.conf`.

## Security Best Practices

✅ Force HTTPS (HTTP redirects to HTTPS)
✅ HSTS enabled (browsers remember to use HTTPS)
✅ Strong SSL ciphers only
✅ OCSP stapling for better performance
✅ Secure headers (X-Frame-Options, CSP, etc.)

## File Structure After Setup

```
your-project/
├── certbot/
│   ├── conf/
│   │   ├── live/
│   │   │   └── yourdomain.com/
│   │   │       ├── fullchain.pem
│   │   │       ├── privkey.pem
│   │   │       └── chain.pem
│   │   ├── options-ssl-nginx.conf
│   │   └── ssl-dhparams.pem
│   └── www/
│       └── .well-known/
├── nginx/
│   ├── Dockerfile
│   ├── nginx.conf              # SSL config (active)
│   └── nginx-init.conf.backup  # HTTP-only config (backup)
└── docker-compose.prod.ssl.yml
```

## Add More Domains

To add more domains to the certificate:

```bash
# Edit init-letsencrypt.sh
domains=(yourdomain.com www.yourdomain.com api.yourdomain.com)

# Remove existing certificates
sudo rm -rf certbot/conf/live
sudo rm -rf certbot/conf/archive
sudo rm -rf certbot/conf/renewal

# Re-run setup
./init-letsencrypt.sh

# Update nginx.conf server_name to include new domains
```

## Monitoring Certificate Expiry

```bash
# Check certificate expiry date
docker-compose -f docker-compose.prod.ssl.yml run --rm certbot certificates

# Should show:
# Certificate Name: yourdomain.com
# Expiry Date: 2024-XX-XX XX:XX:XX+XX:XX (VALID: 89 days)
```

## Rolling Back to HTTP Only

If you need to temporarily disable HTTPS:

```bash
# Stop containers
docker-compose -f docker-compose.prod.ssl.yml down

# Use HTTP-only compose file
docker-compose -f docker-compose.prod.simple.yml up -d

# Change port back to 80 in docker-compose.prod.simple.yml if needed
```

## Final Checklist

- [ ] Domain DNS points to server IP
- [ ] Ports 80 and 443 are open
- [ ] init-letsencrypt.sh has correct domain and email
- [ ] nginx.conf has correct domain name
- [ ] .env.prod has correct ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS
- [ ] Tested with staging=1 first
- [ ] Got production certificate with staging=0
- [ ] HTTPS loads correctly
- [ ] HTTP redirects to HTTPS
- [ ] SSL Labs test shows A/A+ grade
- [ ] Auto-renewal test passed

## Support

If certificates work but you still have issues:

```bash
# Check Django settings
docker-compose -f docker-compose.prod.ssl.yml exec web python manage.py check

# Check if HTTPS is being detected
docker-compose -f docker-compose.prod.ssl.yml logs web | grep -i ssl

# Test from different location
curl -I https://yourdomain.com
```

Your site should now be fully secured with HTTPS! 🔒
