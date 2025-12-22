import os
import hvac
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

class VaultSecretManager:
    def __init__(self):
        self.client = hvac.Client(url=os.getenv('VAULT_ADDR'))
        self.client.auth.approle.login(
            role_id=os.getenv('VAULT_ROLE_ID'),
            secret_id=os.getenv('VAULT_SECRET_ID')
        )
    
    def get_fernet_key(self):
        secret = self.client.secrets.kv.v2.read_secret_version(
            path=os.getenv('VAULT_SECRET_PATH'),
            mount_point=os.getenv('VAULT_KV_MOUNT')
        )
        return secret['data']['data']['FERNET_KEY'].encode()

secret_mgr = VaultSecretManager()
FERNET_KEY = secret_mgr.get_fernet_key()
cipher_suite = Fernet(FERNET_KEY)
