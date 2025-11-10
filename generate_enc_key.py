#! /usr/bin/python3

## Generates 32 char, url safe fernet keys

from cryptography.fernet import Fernet

encryption_key = Fernet.generate_key().decode()
secret_key = Fernet.generate_key().decode()
print(f'ENCRYPTION_KEY={encryption_key}')
print(f'SECRET_KEY={secret_key}')

