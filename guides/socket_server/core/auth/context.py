import dataclasses

from core.models import User
from socket import socket


@dataclasses.dataclass(slots=True)
class AuthContext:
    user: User
    socket: socket
