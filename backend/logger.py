import logging

def get_logger(name="smartsearch"):
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

def get_chroma_logger():
    # Configure logging to only show errors for ChromaDB
    logger = logging.getLogger('chromadb').setLevel(logging.ERROR)
    return logger
