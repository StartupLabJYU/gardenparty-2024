from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import csv
import os
import random
from .app import create_app, settings
from .models import Vote
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request


app = create_app()
# Path to the CSV file where the votes will be stored
CSV_FILE_PATH = 'vote_results.csv'

# Ensure CSV file exists and has the header
if not os.path.exists(CSV_FILE_PATH):
    with open(CSV_FILE_PATH, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Image 1', 'Image 2', 'Winner'])  # Write header if the file is created


# Pydantic model for vote data validation
class Vote(BaseModel):
    img1: str
    img2: str
    winner: str

app.mount("/static", StaticFiles(directory="/app/src/gardenparty/static"), name="static")
templates = Jinja2Templates(directory="/app/src/gardenparty/templates")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # https://fastapi.tiangolo.com/advanced/templates/#using-jinja2templates
    # get_biased_pair()
    return templates.TemplateResponse(
        name="front.html", 
        context={
            "img1": "https://picsum.photos/300?random=1", 
            "img2": "https://picsum.photos/300?random=2",
            "img1_name": "Image 1",
            "img2_name": "Image 2",
            "request": request,
        }
    )


@app.post('/vote')
def vote(vote: Vote):
   try:
        # Append the vote to the CSV file
        with open(CSV_FILE_PATH, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([vote.img1, vote.img2, vote.winner])
        return f"Voted for {vote.winner}!"
   except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/vote')
def get_votes():
    """"
    Frontend can use this endpoint to get the number of votes.
    """
    try:
        votes = []
        with open(CSV_FILE_PATH, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                votes.append(row)

        return votes

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_biased_pair():
    """
    TODO: Read the vote, and use biased sampling to return a pair of images.
    """
    # For now select two random images from settings.generated_images_dir
    images = list(settings.generated_images_dir.glob('*.png'))
    return random.sample(images, k=2)
