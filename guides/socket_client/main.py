import logging
import os
import platform
import socket
import time

from threading import Thread

from rsa import (
    PrivateKey,
    PublicKey,
    decrypt,
    encrypt, common
)

from config import CONFIG

logger = logging.getLogger(__name__)
log_handler = logging.StreamHandler()
logger.addHandler(log_handler)
logger.setLevel(logging.INFO)

MESSAGE_HISTORY: str = ''


def get_clear_command() -> str:
    match platform.system():
        case 'Windows':
            return 'cls'
        case _:
            return 'clear'


CLEAR_COMMAND: str = get_clear_command()


def get_username() -> str:
    if os.path.exists(CONFIG.username_file):
        with open(CONFIG.username_file, 'r') as f:
            return f.read()
    user_name = input("Enter your name: ")
    with open(CONFIG.username_file, 'w') as f:
        f.write(user_name)
    return user_name

def handle_input(
        _socket: socket.socket,
        _private_key: PrivateKey,
        _message_history: str
) -> None:
    while True:
        try:
            data = _socket.recv(
                common.byte_size(_private_key.n)
            )
            if not data:
                continue

            decrypted_message = decrypt(
                data,
                _private_key
            )

            os.system(CLEAR_COMMAND)
            _message_history = f'{_message_history}\n{decrypted_message.decode()}'
            print(_message_history)
        except Exception as e:
            logger.error(msg=str(e), exc_info=True)
            break


def handle_output(
        _socket: socket,
        _public_key: PublicKey
) -> None:
    while True:
        try:
            client_message = input(':')
            if not client_message:
                continue
            encrypted = encrypt(client_message.encode(), _public_key)
            _socket.send(encrypted)
        except Exception as e:
            logger.error(msg=str(e), exc_info=True)
            break


def main() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((CONFIG.host, CONFIG.port))
        public_key, private_key = CONFIG.client_keys  # switch to _generate_new_keys if needed
        input_name = get_username()
        handshake_request = CONFIG.sign_message_prefix + public_key.save_pkcs1() + f':{input_name}'.encode()
        client_socket.send(handshake_request)
        handshake_answer = client_socket.recv(CONFIG.buffer_size)
        if handshake_answer:
            logger.info(handshake_answer)
        _, public_key = handshake_answer.split(b':')

        logger.info(f"Received server public key: {public_key}")
        server_public_key = PublicKey.load_pkcs1(public_key.replace(b'\\n', b'\n'))
        time.sleep(1)
        os.system(CLEAR_COMMAND)

        input_thread = Thread(
            target=handle_input,
            args=(client_socket, private_key, MESSAGE_HISTORY),
            daemon=True
        )

        output_thread = Thread(
            target=handle_output,
            args=(client_socket, server_public_key),
            daemon=True
        )

        input_thread.start()
        output_thread.start()

        while input_thread.is_alive() and output_thread.is_alive():
            time.sleep(0.1)



if __name__ == '__main__':
    main()
