
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
        # Create the instance folder if it doesn't exist
        
        pathlib.Path(settings.original_images_dir).mkdir(exist_ok=True, mode=0o777, parents=True)
        pathlib.Path(settings.original_images_dir).mkdir(exist_ok=True, mode=0o777, parents=True)
        csv_path = pathlib.Path("instance/vote_results.csv", mode=0o777)
        if not csv_path.exists():
            with open(csv_path, mode='w', newline='') as csv_file:
                csv_writer = csv.writer(csv_file)
                csv_writer.writerow(["image1", "image2", "winner"])


    return app

def app():
    app = create_app()
    return app
