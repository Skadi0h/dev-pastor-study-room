import socket
import threading
import time
import rsa

BUFFER_SIZE = 2048
public_key, private_key = rsa.newkeys(
    BUFFER_SIZE)  # Maybe save private key on a client disk and read after program runs again? ( For check on a server-side )


def listen_to_messages_from_server(client: socket.socket) -> None:  # socket, not general object, specify return types
    try:
        while 1:
            message = client.recv(BUFFER_SIZE).decode("utf-8")
            if message:
                print(f"[{message}]")
            else:
                print("Message from server is empty")
                break
    except OSError as e:
        print(f"Flow interrupted by exception {e}, stop!'")


def send_message_to_server(client: socket.socket) -> None:
    while 1:
        option = input("Enter '1' to send message or exit to close: ")  # Don`t repeat question every message

        if option == "1":
            message = input("Enter message: ").encode()
            client.sendall(message)
        elif option == "exit":
            break


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        HOST = "127.0.0.1"  # Move constants to root of the module
        PORT = 5000
        try:
            client.connect((HOST, PORT))
            print("Successfully connected to server")

            # Start listening to messages from the server in a separate thread
            print("Your history messages: ")
            listen_thread = threading.Thread(target=listen_to_messages_from_server, args=(client,))
            listen_thread.start()

            time.sleep(2)
            send_message_to_server(client)
        except KeyboardInterrupt:
            print("Stopping!")
            if listen_thread.is_alive():
                client.shutdown(socket.SHUT_RDWR)


if __name__ == "__main__":
    main()
