# app.py
# Entry point for the AUBus frontend demo.
# Creates a QStackedWidget and registers each page (one file per page).
# Pages navigate by changing the current index of the shared stacked widget.

import sys
from PyQt5.QtWidgets import QApplication, QStackedWidget # type: ignore
from .login_page import LoginPage
from .register_page import RegisterPage
from .preliminary_page import PreliminaryPage
from .main_page import MainPage
from .api_client import ApiClient
from .peer import PeerServer

def build_app():
    app = QApplication(sys.argv)

    # Shared application state (in-memory). Holds authenticated user info and API client.
    app_state = {"api": ApiClient()}

    # Start a peer server for P2P chat; store in app_state so pages can register callbacks.
    peer = PeerServer(host='0.0.0.0', port=0, on_message=None)
    try:
        peer_port = peer.start()
        app_state['peer_server'] = peer
        app_state['peer_port'] = peer_port
    except Exception:
        app_state['peer_server'] = None
        app_state['peer_port'] = None

    stack = QStackedWidget()
    stack.setWindowTitle("AUBus - The Best Carpooling Service")
    stack.resize(800, 600)

    # Create pages and add them to the stack
    login = LoginPage(parent_stack=stack, app_state=app_state)
    login.setObjectName("LoginPage")
    register = RegisterPage(parent_stack=stack, app_state=app_state)
    register.setObjectName("RegisterPage")
    preliminary = PreliminaryPage(parent_stack=stack, app_state=app_state)
    preliminary.setObjectName("PreliminaryPage")
    main = MainPage(parent_stack=stack, app_state=app_state)
    main.setObjectName("MainPage")

    stack.addWidget(login)
    stack.addWidget(register)
    stack.addWidget(preliminary)
    stack.addWidget(main)

    # Set initial visible page: login
    stack.setCurrentWidget(login)
    stack.show()
    return app, stack

if __name__ == "__main__":
    app, stack = build_app()
    sys.exit(app.exec_())
