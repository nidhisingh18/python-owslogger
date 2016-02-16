from flask import Flask
import logging

from owslogger import logger


app = Flask(__name__)
logger.setup(app, None, 'dev', 'logger_name', logging.INFO, 'service_name', '1.0.0')


@app.route('/')
def home():
    return 'Home'

if __name__ == '__main__':
    app.run(debug=True)
