#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run database migrations
python manage.py migrate

# Add to build.sh after migrations
python manage.py shell -c "
from claims.models import UserProfile
UserProfile.objects.all().update(profile_picture=None)
print('Profile pictures reset')
"