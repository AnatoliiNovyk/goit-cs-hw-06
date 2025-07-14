import socket
import mimetypes
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from multiprocessing import Process
from pathlib import Path
from datetime import datetime
import json
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

# --- Конфігурація ---
HTTP_HOST = '0.0.0.0'
HTTP_PORT = 3000
SOCKET_HOST = '0.0.0.0'
SOCKET_PORT = 5000
MONGO_HOST = 'mongo' # Назва сервісу в docker-compose
MONGO_PORT = 27017
MONGO_DB_NAME = 'messages_db'
MONGO_COLLECTION_NAME = 'messages'


# --- HTTP Сервер ---
class SimpleHttpHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == '/':
            self.send_html_file('front-init/index.html')
        elif url.path == '/message.html':
            self.send_html_file('front-init/message.html')
        else:
            # Створюємо шлях до статичного файлу, додаючи 'front-init' попереду
            file_path = Path('front-init').joinpath(url.path[1:])
            if file_path.exists():
                self.send_static_file(file_path)
            else:
                self.send_html_file('front-init/error.html', 404)

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        # Відправляємо дані на Socket-сервер
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.sendto(post_data, (SOCKET_HOST, SOCKET_PORT))
        except socket.error as e:
            print(f"Помилка відправки даних через сокет: {e}")

        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def send_html_file(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as f:
            self.wfile.write(f.read())

    def send_static_file(self, filename, status_code=200):
        self.send_response(status_code)
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            self.send_header('Content-type', mime_type)
        else:
            self.send_header('Content-type', 'text/plain')
        self.end_headers()
        with open(filename, 'rb') as f:
            self.wfile.write(f.read())

def run_http_server():
    server_address = (HTTP_HOST, HTTP_PORT)
    http_server = HTTPServer(server_address, SimpleHttpHandler)
    print(f"HTTP сервер запущено на {HTTP_HOST}:{HTTP_PORT}")
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()

# --- Socket Сервер ---
def save_to_mongodb(data):
    try:
        client = MongoClient(host=MONGO_HOST, port=MONGO_PORT)
        db = client[MONGO_DB_NAME]
        collection = db[MONGO_COLLECTION_NAME]
        collection.insert_one(data)
        client.close()
    except ConnectionFailure as e:
        print(f"Не вдалося підключитися до MongoDB: {e}")
    except Exception as e:
        print(f"Помилка при збереженні в MongoDB: {e}")

def run_socket_server():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((SOCKET_HOST, SOCKET_PORT))
        print(f"Socket сервер запущено на {SOCKET_HOST}:{SOCKET_PORT}")
        while True:
            data, addr = sock.recvfrom(1024)
            print(f"Отримано дані від {addr}: {data.decode()}")
            
            # Парсимо дані
            data_parse = urllib.parse.unquote_plus(data.decode())
            data_dict = {key: value for key, value in [el.split('=') for el in data_parse.split('&')]}
            
            # Додаємо час та зберігаємо в MongoDB
            message_to_save = {
                "date": str(datetime.now()),
                "username": data_dict.get("username"),
                "message": data_dict.get("message")
            }
            save_to_mongodb(message_to_save)

# --- Головна функція ---
if __name__ == '__main__':
    http_process = Process(target=run_http_server)
    socket_process = Process(target=run_socket_server)

    http_process.start()
    socket_process.start()

    http_process.join()
    socket_process.join()
