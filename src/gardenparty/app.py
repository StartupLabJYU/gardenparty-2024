import io
import os
import PIL
from fastapi import FastAPI, HTTPException
import pillowfight
import pathlib
from pydantic import BaseModel, ConfigDict, Field

from typing import Optional, List
from typing_extensions import Annotated
from pydantic.functional_validators import BeforeValidator
from PIL import Image
import gradio as gr

os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', 'False')

PyObjectId = Annotated[str, BeforeValidator(str)]

# class ImageModel(BaseModel):
#     id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")

def create_app():
    app = FastAPI()

    @app.on_event("startup")
    async def startup_event():
        pathlib.Path("instance").mkdir(exist_ok=True)

    @app.get("/")
    async def read_root():
        return {"Hello": "World"}

    # Run the Gradio interface when the app starts
    @app.on_event("startup")
    async def startup_event():
        create_gradio_interface()

    return app

app = create_app()

def deskew_and_crop_image(img: Image.Image) -> PIL.Image.Image:
    try:
        # Load the image from bytes
        if isinstance(img, bytes):
            img = Image.open(io.BytesIO(img))

        img = pillowfight.deskew()

        # Crop the image
        img = pillowfight.crop(img)

        # # Save the image to bytes
        # buffered = io.BytesIO()
        # img.save(buffered, format="JPEG")
        # img_bytes = buffered.getvalue()
        # return img_bytes

    except Exception as e:
        raise RuntimeError(f"Error during image processing: {e}")


# Gradio Functionality to capture and process images from the camera
def capture_and_process_image(img):
    try:
        # Convert Gradio image (numpy array) to PIL Image and then to bytes
        if isinstance(img, PIL.Image.Image):
            img_pil = img
        else:
            img_pil = Image.fromarray(img)

        # buffered = io.BytesIO()
        # img_pil.save(buffered, format="JPEG")
        # img_bytes = buffered.getvalue()

        # Process the image (deskew and crop)
        processed_image = deskew_and_crop_image(img_pil)

        # Save processed image to MongoDB
        #save_image_to_mongodb("processed_captured_image.jpg", processed_image_data)

        # Return the processed image
        #processed_image = Image.open(io.BytesIO(processed_image_data))
        return processed_image

    except Exception as e:
        raise RuntimeError(f"Error during image capture and processing: {e}")



def create_gradio_interface():
    """Create a Gradio interface to capture and process images from the camera."""

    interface = gr.Interface(
        fn=capture_and_process_image,            # Function to process image
        inputs=gr.Image(sources=["webcam", "upload"], type="pil"),  # Input type: Image from the camera
        outputs="image",                         # Output type: Processed image
        title="Document Scanner",
        description="Capture an image with the camera, deskew and crop it."
    )
    interface.launch(share=True)