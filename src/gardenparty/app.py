
import os
import csv
from fastapi import FastAPI, HTTPException
import pathlib

from typing_extensions import Annotated
from pydantic.functional_validators import BeforeValidator

from .models import Settings

os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', 'False')

PyObjectId = Annotated[str, BeforeValidator(str)]

# class ImageModel(BaseModel):
#     id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

settings = Settings()

def create_app():
    app = FastAPI()

    @app.on_event("startup")
    async def startup_event():

        pathlib.Path("instance").mkdir(exist_ok=True, mode=0o777)
        pathlib.Path("instance/generated").mkdir(exist_ok=True, mode=0o777)
        pathlib.Path("instance/original").mkdir(exist_ok=True, mode=0o777)
        csv_path = pathlib.Path("instance/vote_results.csv", mode=0o777)
        if not csv_path.exists():
            with open(csv_path, mode='w', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow(["image1", "image2", "winner"])


    return app

def app():
    app = create_app()
    return app
