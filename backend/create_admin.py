#!/usr/bin/env python
"""
Create admin user script
Run this with: ./venv/bin/python create_admin.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Admin credentials
username = 'Viscous106'
password = '787898'
email = 'viscous106@admin.com'

# Check if user already exists
if User.objects.filter(username=username).exists():
    print(f'❌ User "{username}" already exists!')
    user = User.objects.get(username=username)
    # Update password
    user.set_password(password)
    user.save()
    print(f'✅ Password updated for user "{username}"')
else:
    # Create superuser
    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password
    )
    print(f'✅ Superuser "{username}" created successfully!')

print(f'\n📋 Admin Credentials:')
print(f'   Username: {username}')
print(f'   Password: {password}')
print(f'   Email: {email}')
print(f'\n🌐 Admin URL: http://localhost:8000/admin/')
