"""

Important environment variables:
- :env:`os.environ['WASMIOT_ORCHESTRATOR_URL']` - URL of orchestrator
"""

import os
from pydantic import Field
from pydantic_settings import BaseSettings

os.environ.setdefault('WASMIOT_ORCHESTRATOR_URL', 'http://localhost:3000')
os.environ.setdefault('WASMIOT_LOGGING_ENDPOINT', f"{os.environ['WASMIOT_ORCHESTRATOR_URL']}/device/logs")

class Settings(BaseSettings):
    LOG_PULL_DELAY: float = Field(2.5,
                                  env="LOG_PULL_DELAY",
                                  description="Delay between log pulls from orchestrator")

    STEP_DELAY: float = Field(1.5,
                              env="STEP_DELAY",
                              description="Delay between steps in the demo")

    WASMIOT_ORCHESTRATOR_URL: str = "http://localhost:3000"
    WASMIOT_LOGGING_ENDPOINT: str = f"{WASMIOT_ORCHESTRATOR_URL}/device/logs"

    DEMO_URL: str = "http://localhost:7860"

settings = Settings()
