#!/bin/bash
# Cron script to charge past sessions hourly
cd /root/docker/availabilityTracker
docker compose -f docker-compose.prod.ssl.yml exec -T web python manage.py charge_past_sessions >> /var/log/kangoo_charge.log 2>&1
