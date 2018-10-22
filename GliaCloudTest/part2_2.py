from flask import Flask
from const import PYTHON_LIST
import random


app = Flask(__name__)

def root():
    """return content"""
    return random.choice(PYTHON_LIST))

# For front-end render
app.add_url_rule("/test", "ocr_root", root, methods=["GET"])

if __name__ == "__main__":

    app.run(debug=False, port=API_PORT)