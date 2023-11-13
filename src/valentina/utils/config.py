"""Gather configuration from environment variables."""

import os
from pathlib import Path

from dotenv import dotenv_values

DIR = Path(__file__).parents[3].absolute()
CONFIG = {
    **dotenv_values(DIR / ".env"),  # load shared variables
    **dotenv_values(DIR / ".env.secrets"),  # load sensitive variables
    **os.environ,  # override loaded values with environment variables
}
for k, v in CONFIG.items():
    CONFIG[k] = v.replace('"', "").replace("'", "").replace(" ", "")
