# run.py
from app import create_app
from app.config import Config
import os
import signal
import sys  

def signal_handler(sig, frame):
    print('Received signal to shut down. Shutting down gracefully...')
    sys.exit(0)


signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
signal.signal(signal.SIGINT, signal_handler)   # Interrupt signal

app = create_app()

@app.before_request
def log_request():
    from flask import request
    import logging
    logging.info(f"Received request: {request.method} {request.path}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = Config.FLASK_ENV == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)