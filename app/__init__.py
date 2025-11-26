import secrets
from nicegui import ui

from app.server import configure_endpoints

def start_web_server():
    configure_endpoints()
    storage_secret = secrets.token_hex(16)
    # Starting the server in `native` mode to enable file dialogs easily
    # Ideally we could do this in non-native mode, but need to investigate more
    ui.run(storage_secret=storage_secret, port=8090, native=True)
