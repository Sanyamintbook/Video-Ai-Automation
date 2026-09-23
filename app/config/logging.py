import sys
from loguru import logger
from app.config.settings import get_settings


def configure_logger() -> None:
    """Configure loguru logger based on application settings."""
    settings = get_settings()

    logger.remove()  # Remove default handler

    logger.add(
        sys.stdout,
        level=settings.log_level.upper(),
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        colorize=True,
    )

    logger.add(
        "logs/app.log",
        level=settings.log_level.upper(),
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    )
