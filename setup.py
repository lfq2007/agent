from dotenv import load_dotenv
from modules.YA_Common.utils.logger import get_logger

logger = get_logger("setup")


def setup():
    """Setup your environment and dependencies here."""
    try:
        load_dotenv()
        logger.info("Setup complete.")
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        raise e
