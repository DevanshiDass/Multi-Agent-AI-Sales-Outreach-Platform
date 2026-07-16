"""
config.py
---------
Centralizes all environment/config loading so the rest of the codebase
never touches os.environ directly.
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ------------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------------

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("cold_outreach_agent")


class Config:
    """
    Central configuration class.
    """

    # ---------------- API Keys ---------------- #

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    SERPER_API_KEY = os.getenv("SERPER_API_KEY")

    # ---------------- Model ---------------- #

    # Qwen reasoning models tend to leak reasoning in CrewAI.
    # Llama 3.3 follows formatting instructions much better.
    GROQ_MODEL = os.getenv(
        "GROQ_MODEL",
        "llama-3.3-70b-versatile",
    )

    LITELLM_MODEL_STRING = f"groq/{GROQ_MODEL}"

    # ---------------- Generation ---------------- #

    DEFAULT_TEMPERATURE = float(
        os.getenv("LLM_TEMPERATURE", "0.3")
    )

    # ---------------- Output ---------------- #

    OUTPUT_DIR = os.getenv(
        "OUTPUT_DIR",
        "output/emails",
    )

    # ---------------- Retry Configuration ---------------- #

    # Retry ONLY the writer
    WRITER_MAX_ATTEMPTS = int(
        os.getenv(
            "WRITER_MAX_ATTEMPTS",
            "2",
        )
    )

    # Keep this low while debugging
    MAX_RPM = int(
        os.getenv(
            "MAX_RPM",
            "2",
        )
    )

    # ---------------- Validation ---------------- #

    @classmethod
    def validate(cls):

        missing = []

        if not cls.GROQ_API_KEY:
            missing.append("GROQ_API_KEY")

        if not cls.SERPER_API_KEY:
            missing.append("SERPER_API_KEY")

        if missing:
            logger.error(
                "Missing required environment variable(s): %s",
                ", ".join(missing),
            )
            sys.exit(1)

        # Export so LiteLLM/CrewAI can read them.
        os.environ["GROQ_API_KEY"] = cls.GROQ_API_KEY
        os.environ["SERPER_API_KEY"] = cls.SERPER_API_KEY

        logger.info(
            "Config validated. Using model: %s",
            cls.LITELLM_MODEL_STRING,
        )