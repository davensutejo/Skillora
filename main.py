from website import create_app
import logging
import sys
import os

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=8000)


