
import os
import csv
from fastapi import FastAPI, HTTPException
import pathlib

from typing_extensions import Annotated
from pydantic.functional_validators import BeforeValidator

from .models import Settings

PyObjectId = Annotated[str, BeforeValidator(str)]

# class ImageModel(BaseModel):
#     id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

settings = Settings()

def create_app():
    app = FastAPI()

    @app.on_event("startup")
    async def startup_event():
        # Create the media directories if they don't exist
        (pathlib.Path(settings.INSTANCE_PATH)).mkdir(exist_ok=True, mode=0o777, parents=True)
        (pathlib.Path(settings.INSTANCE_PATH) / 'original').mkdir(exist_ok=True, mode=0o777, parents=True)
        (pathlib.Path(settings.INSTANCE_PATH) / 'generated').mkdir(exist_ok=True, mode=0o777, parents=True)

    return app


def app():
    app = create_app()
    return app


def get_pkg_path() -> pathlib.Path:
    """
    Return the path to the package folder.
    """
    return pathlib.Path(__file__).parent
