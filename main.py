
from src.app import app

HOST = '127.0.0.1'
PORT = 8080
DEBUG = True

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)

