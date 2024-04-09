import os
from functools import cached_property
from pathlib import Path

import rsa
from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict
)
from rsa import PrivateKey, PublicKey


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='SOCKET_SERVER_')
    host: str = Field(default="localhost")
    port: int = Field(default=8000)
    buffer_size: int = Field(default=2048)
    sign_message_prefix: bytes = b'PUBLIC_KEY:'
    rsa_key_length: int = Field(default=2048)
    rsa_keys_path: Path = Field(default=Path.cwd() / '.rsa')
    rsa_private_key_name: str = Field(default='private.pem')
    rsa_public_key_name: str = Field(default='public.pem')
    username_file: str = Field(default='username.txt')

    def _generate_new_keys(self) -> tuple[PublicKey, PrivateKey]:
        public_key, private_key = rsa.newkeys(self.rsa_key_length)
        os.makedirs(self.rsa_keys_path, exist_ok=True)
        with open(self.rsa_keys_path / self.rsa_private_key_name, 'wb') as private_file:
            private_file.write(private_key.save_pkcs1())
        with open(self.rsa_keys_path / self.rsa_public_key_name, 'wb') as public_file:
            public_file.write(public_key.save_pkcs1())
        return public_key, private_key

    def _load_existing_keys(self) -> tuple[PublicKey, PrivateKey]:
        with open(self.rsa_keys_path / self.rsa_private_key_name, 'rb') as private_file:
            private_key = rsa.PrivateKey.load_pkcs1(private_file.read())
        with open(self.rsa_keys_path / self.rsa_public_key_name, 'rb') as public_file:
            public_key = rsa.PublicKey.load_pkcs1(public_file.read())
        return public_key, private_key

    @cached_property
    def client_keys(self) -> tuple[PublicKey, PrivateKey]:
        if Path.exists(self.rsa_keys_path):
            return self._load_existing_keys()
        return self._generate_new_keys()


CONFIG = Config()
__all__ = ['CONFIG']
