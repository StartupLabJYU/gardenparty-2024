from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from pathlib import Path

class Image(BaseModel):
    filename: str
    creator: Optional[str] = None
    prompt: Optional[str] = None


class Vote(BaseModel):
    winner: str = Field(..., help="Image filename that won the vote")
    looser: str = Field(..., help="Image filename that lost the vote")


class Settings(BaseSettings):
    original_images_dir: Path = Field(Path("/app/instance/original"), help="Directory to store original images")
    generated_images_dir: Path = Field(Path("/app/instance/generated"), help="Directory to store generated images")
    

    # to read API keys etc. from environment variables model_config should be defined in here
    OPENAI_API_KEY:str = ""
    STABILITYAI_API_KEY:str = ""
    model_config = SettingsConfigDict(env_file=".env")