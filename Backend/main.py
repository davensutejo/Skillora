from website import create_app
import logging
import sys
import os

# Configure logging
log_dir = 'logs'
log_file = os.path.join(log_dir, 'app.log')

# Create handler for both console and file
file_handler = logging.FileHandler(log_file)
console_handler = logging.StreamHandler(sys.stdout)

# Configure formatters
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Configure root logger
logging.root.setLevel(logging.DEBUG)
logging.root.addHandler(file_handler)
logging.root.addHandler(console_handler)

# Create Flask logger specifically
flask_logger = logging.getLogger('flask')
flask_logger.setLevel(logging.DEBUG)

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=9000)

