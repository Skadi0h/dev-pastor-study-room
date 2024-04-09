import logging
import socket
import dataclasses

import rsa

from queue import Queue
from threading import Thread
from typing import Self

from rsa import PublicKey

from config import CONFIG
from core.auth.context import AuthContext
from core.gemma.service import GemmaService
from core.handlers import UserHandler, MessageHandler
from core.models import User, Message

logger = logging.getLogger(__name__)
log_handler = logging.StreamHandler()
logger.addHandler(log_handler)
logger.setLevel(logging.INFO)

logger.info('Gemma loading...Wait')
gemma = GemmaService()


@dataclasses.dataclass(slots=True)
class SignedMessage:
    auth_context: AuthContext
    content: bytes

    @classmethod
    def validate(cls, message: bytes) -> tuple[PublicKey, str]:
        assert message.startswith(CONFIG.sign_message_prefix)
        logger.info(f"Received handshake request: {message}")
        _, public_key, user_name = message.split(b':')

        logger.info(f"Received public key: {public_key}")
        logger.info(f"Received user name: {user_name}")
        return (
            rsa.PublicKey.load_pkcs1(public_key.replace(b'\\n', b'\n')),
            user_name.decode('utf-8')
        )


@dataclasses.dataclass(slots=True)
class ClientThread:
    context: AuthContext
    _thread: Thread | None = None

    def listen(self, message_queue: Queue):
        with self.context.socket as _socket:
            while True:
                try:
                    data = _socket.recv(CONFIG.buffer_size)
                    if not data:
                        continue
                    message = MessageHandler.upsert_instance(
                        instance=Message(
                            user_id=self.context.user.id,
                            content=data,
                            user_name=self.context.user.name
                        )
                    )
                    decrypted_message = rsa.decrypt(message.content, CONFIG.server_keys[1])
                    signed_message = f'{self.context.user.name}: {decrypted_message.decode()}'
                    message_queue.put(
                        SignedMessage(
                            auth_context=self.context,
                            content=signed_message.encode()
                        )
                    )
                except ConnectionResetError:
                    break

    def start(self, message_queue: Queue) -> None:
        self._thread = Thread(target=self.listen, args=(message_queue,), daemon=True)
        self._thread.start()

    def join(self):
        if self._thread is not None:
            self._thread.join()


@dataclasses.dataclass(slots=True)
class ClientContext:
    client_thread: ClientThread
    auth_context: AuthContext

    def __str__(self) -> str:
        return (
            f'CONTEXT: '
            f'{self.client_thread.context.user.name} '
            f'{self.client_thread.context.user.public_key}'
        )

    @classmethod
    def from_socket(cls, _socket: socket.socket) -> Self:
        conn, _ = _socket.accept()
        client_public_key, user_name = SignedMessage.validate(
            message=conn.recv(CONFIG.buffer_size)
        )
        server_public_key = CONFIG.server_keys[0]
        conn.send(CONFIG.sign_message_prefix + server_public_key.save_pkcs1())
        client_public_key = client_public_key.save_pkcs1()
        users = UserHandler.read_instances(
            filters=(User.public_key == client_public_key,)
        )
        if users:
            user = users[0]
        else:
            user = UserHandler.upsert_instance(
                instance=User(
                    public_key=client_public_key,
                    name=user_name
                )
            )
        auth_context = AuthContext(
            user=user,
            socket=conn
        )
        return cls(
            client_thread=ClientThread(
                context=auth_context
            ),
            auth_context=auth_context
        )


@dataclasses.dataclass(slots=True)
class Server:
    message_queue = Queue()
    gemma_queue = Queue()
    client_contexts: list[ClientContext] = dataclasses.field(default_factory=list)

    def sync_messages_for_current_context(
            self,
            context: ClientContext
    ) -> None:
        for message in MessageHandler.read_instances():
            decrypted_content = rsa.decrypt(message.content, CONFIG.server_keys[1])
            secured_signed_message = SignedMessage(
                auth_context=context.auth_context,
                content=f'{message.user_name}: {decrypted_content.decode()}'.encode()
            )
            self.send_message_to_context(
                message=secured_signed_message.content,
                auth_context=context.auth_context
            )

    @staticmethod
    def send_message_to_context(
            message: bytes,
            auth_context: AuthContext
    ) -> None:
        public_key = rsa.PublicKey.load_pkcs1(
            keyfile=auth_context.user.public_key
        )
        encrypted = rsa.encrypt(message, pub_key=public_key)
        auth_context.socket.send(encrypted)

    def handle_messages(self) -> None:
        while True:
            message: SignedMessage = self.message_queue.get()
            if b'Gemma' in message.content:
                self.gemma_queue.put(message)
            contexts_to_clear = []
            for client_context in self.client_contexts:
                try:
                    self.send_message_to_context(
                        message=message.content,
                        auth_context=client_context.auth_context
                    )
                except OSError:
                    contexts_to_clear.append(client_context)
            for client_context in contexts_to_clear:
                self.client_contexts.remove(client_context)
            self.message_queue.task_done()

    def handle_gemma_questions(self) -> None:
        while True:
            question_to_gemma: SignedMessage = self.gemma_queue.get()
            gemma_answer = gemma.get_answer(
                message=question_to_gemma.content.decode()
            )
            self.send_message_to_context(
                f'Gemma: {gemma_answer}'.encode(),
                auth_context=question_to_gemma.auth_context
            )

    def serve(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as _socket:
            _socket.bind((CONFIG.host, CONFIG.port))
            logger.info(f'BIND on {CONFIG.host}:{CONFIG.port}')
            logger.info(msg='Waiting for connections..')
            _socket.listen()
            message_thread = Thread(target=self.handle_messages, daemon=True)
            message_thread.start()
            gemma_thread = Thread(target=self.handle_gemma_questions, daemon=True)
            gemma_thread.start()
            while True:
                try:
                    client_context = ClientContext.from_socket(_socket=_socket)
                    self.client_contexts.append(client_context)
                    logger.info(msg=f'New client context: {client_context}')
                    self.sync_messages_for_current_context(context=client_context)
                    logger.info(msg='Messages for current context synced')
                    client_context.client_thread.start(message_queue=self.message_queue)
                except Exception as e:
                    logger.error(str(e), exc_info=True)
                except KeyboardInterrupt:
                    message_thread.join()
                    for client_context in self.client_contexts:
                        client_context.client_thread.join()
                    exit()


if __name__ == "__main__":
    Server().serve()
