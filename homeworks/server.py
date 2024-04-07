import socket
import rsa
import sqlite3
import threading
from dotenv import dotenv_values
from transformers import AutoTokenizer, AutoModelForCausalLM

BUFFER_SIZE = 2048
public_key, private_key = rsa.newkeys(BUFFER_SIZE)
active_clients: list[socket.socket] = []  # What type of clients? String, int, what?
config = dotenv_values(".env")


class ThreadManager:  # Use this class for manipulate another classes
    def __init__(self):
        self.threads: list[threading.Thread] = []

    def add_thread(self, thread: threading.Thread) -> None:  # Specify types
        self.threads.append(thread)

    def stop_all_threads(self) -> None:
        for thread in self.threads:
            if thread.is_alive():
                thread.join()  # stop??? Maybe .join()?


thread_manager = ThreadManager()


def add_message_to_database(message: bytes) -> None:
    with sqlite3.connect(config["DB_NAME"]) as conn:
        cursor = conn.cursor()
        encrypted_message = rsa.encrypt(message, public_key)
        cursor.execute("INSERT INTO storage (data, public_key) VALUES(?, ?)",
                       (encrypted_message, public_key.save_pkcs1()))


def client_handler(client: socket.socket) -> None:  # socket, not general object, specify return types
    active_clients.append((client,))

    while 1:
        message = client.recv(BUFFER_SIZE)
        if message:
            generate_response(client, message.decode())
            add_message_to_database(message)
            send_message_to_all(message)
        else:
            break


def send_message_to_client(clint: socket.socket, message: bytes):  # socket, not general object, specify return types
    clint.sendall(message)


def send_message_to_all(message: bytes):
    for user in active_clients:
        send_message_to_client(user[0], message)


def send_history_messages(client: socket.socket):  # socket, not general object, specify return types
    with sqlite3.connect(config["DB_NAME"]) as conn:  # move db name in separate constant or env variable
        cursor = conn.cursor()
        #  Get encrypted messages for the given public key from the database
        encrypted_messages = cursor.execute("SELECT data FROM storage WHERE public_key=?",
                                            (public_key.save_pkcs1(),)).fetchall()

        # Decode and send each message
        for row in encrypted_messages:
            decrypted_message = rsa.decrypt(row[0], private_key)
            client.sendall(decrypted_message)


def create_storage_if_not_exists() -> None:
    with sqlite3.connect(config["DB_NAME"]) as conn:  # move db name in separate constant or env variable
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS storage( 
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              data BLOB NOT NULL,
              public_key BLOB NOT NULL
          );
          """)


def generate_response(client:socket.socket, message: str):
    checkpoint = "google/gemma-2b-it"
    tokenizer = AutoTokenizer.from_pretrained(checkpoint, token=config["HF_TOKEN"])
    model = AutoModelForCausalLM.from_pretrained(checkpoint, token=config["HF_TOKEN"])

    input_ids = tokenizer.encode(message, return_tensors="pt")

    outputs = model.generate(input_ids, max_new_tokens=1000)
    response = tokenizer.decode(outputs[0], skip_special_tokens=True).encode()
    client.sendall(b'Assistant: ' + response)

def main():
    create_storage_if_not_exists()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        HOST = "127.0.0.1"  # Move constants to root of the module
        PORT = 5000
        LISTENER_LIMIT = 2
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        print(f"Running the server on {HOST} {PORT}")

        server.listen(LISTENER_LIMIT)

        try:
            while 1:
                client, address = server.accept()
                print(f"Successfully connected to client {address[0]}, {address[1]}")

                listen_thread = threading.Thread(target=client_handler, args=(client,))
                thread_manager.add_thread(listen_thread)
                listen_thread.start()

                # Send history messages to each client
                send_history_messages(client)

        except KeyboardInterrupt:
            print("Stopping!")
            thread_manager.stop_all_threads()


if __name__ == "__main__":
    main()
