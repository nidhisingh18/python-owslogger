Flask Logging
=============

This logger is designed to send JSON to Loggly in a format that matches our
OWS1 standard. Installation is minimal:

```bash
pip install git+https://github.com/theorchard/logging-python-flask.git@#egg=owslogger
```

Setting your python application:

```python
from flask import Flask
import logging
import owslogger


app = Flask(__name__)
owslogger.setup(
    app, 'loggly http/s url', 'environment', 'logger_name', logging.INFO,
    'service_name', '1.0.0')
```
