import json
import logging
import traceback
from datetime import datetime

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": "editorbot",
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log["exception"] = traceback.format_exception(*record.exc_info)

        # Add extra fields if present
        if hasattr(record, 'chat_id'):
            log["chat_id"] = record.chat_id
        if hasattr(record, 'template_id'):
            log["template_id"] = record.template_id
        if hasattr(record, 'soundtrack_id'):
            log["soundtrack_id"] = record.soundtrack_id

        return json.dumps(log)

def setup_logging(level=logging.INFO):
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
