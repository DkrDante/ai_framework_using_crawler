import os
import logging
from datetime import datetime

# Generate a single log filename per day using the specified format
_log_filename = f"{datetime.now().strftime('%m_%d_%Y')}.log"

def get_logger(name: str) -> logging.Logger:
    """
    Configures and returns a logger with both console and file handlers.
    Creates a 'logs' directory at the root if it doesn't exist.
    """
    logger = logging.getLogger(name)
    
    # Avoid adding duplicate handlers if the logger has already been configured
    if logger.handlers:
        return logger

    # Set level to INFO to exclude DEBUG logs entirely
    logger.setLevel(logging.INFO)

    # Custom log format wrapped in brackets with line numbers
    formatter = logging.Formatter(
        "%(asctime)s %(lineno)d %(name)s %(levelname)s - %(message)s"
    )

    # Console handler (INFO level and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (INFO level and above)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.abspath(os.path.join(script_dir, "..", "logs"))
    os.makedirs(logs_dir, exist_ok=True)
    
    file_handler = logging.FileHandler(
        os.path.join(logs_dir, _log_filename),
        encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
