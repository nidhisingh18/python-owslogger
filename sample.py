from flask import Flask
import logging
from flask import g

from owslogger import logger

app = Flask(__name__)
logger.setup(
    app, 'https://logglyurl', 'dev', 'logger_name', logging.INFO,
    'service_name', '1.0.0')


@app.route('/')
def home():
    g.log.warning('something', resources={'upc': 'awesome'})
    return 'Home'

if __name__ == '__main__':
    app.run(debug=True)
