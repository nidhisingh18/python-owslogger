from flask import Flask
import logging
from flask import g

from owslogger import flask_logger

app = Flask(__name__)
flask_logger.setup(
    app, 'http://logs-01.loggly.com/bulk/77c54e3f-33b7-4f8b-a2a7-dbaef3414348/tag/ows1/', 'dev', 'michael_ortali', logging.INFO,
    'grass', '1.0.0')


@app.route('/')
def home():
    g.log.warning('something', resources={'upc': 'awesome'})
    return 'Home'

if __name__ == '__main__':
    app.run(debug=True)
