import logging
import json
import sys
from datetime import datetime
from core.configs import configs
from rich.logging import RichHandler

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": getattr(record, 'module', ''),
            "function": record.funcName,
            "line": record.lineno,
            "pathname": record.pathname,
            "message": record.getMessage(),
            "process": record.process,
            "thread": record.thread
        }
        
        # Добавляем exception info если есть
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry, ensure_ascii=False)

def setup_logging():    
    
    if configs.LOG_FORMAT == "json":
        formatter = JSONFormatter()
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
    else:
        handler = RichHandler()

    
    root_logger = logging.getLogger()
    root_logger.handlers.clear()  # Очищаем существующие handlers
    root_logger.addHandler(handler)
    log_level = getattr(logging, configs.LOG_LEVEL.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # Настраиваем Uvicorn логгеры
    uvicorn_loggers = [
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "watchfiles.main",
        "fastapi"
    ]
    for logger_name in uvicorn_loggers:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False  # Предотвращаем дублирование логов
