from pathlib import Path
from typing import Counter
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import csv
import os
import time
import random
import uuid
from .app import create_app, get_pkg_path, settings
from .models import Vote
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request

app = create_app()

# Path to the CSV file where the votes will be stored
CSV_FILE_PATH = Path(settings.INSTANCE_PATH) / 'vote_results.csv'
IMAGES_DIR = Path(settings.INSTANCE_PATH) / 'generated'
STATIC_DIR = get_pkg_path() / 'static'
TEMPLATES_DIR = get_pkg_path() / 'templates'

# Stores random uuids to prevent repeat voting
current_voting_tokens = {}


@app.on_event("startup")
def startup_event():
    # Ensure CSV file exists and has the header
    if not os.path.exists(CSV_FILE_PATH):
        with open(CSV_FILE_PATH, mode='w') as file:
            writer = csv.writer(file)
            writer.writerow(['Image 1', 'Image 2', 'Winner', 'Timestamp'])  # Write header if the file is created


# Pydantic model for vote data validation
class Vote(BaseModel):
    img1: str
    img2: str
    winner: str
    vote_token: str

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/generated_images", StaticFiles(directory=IMAGES_DIR), name="images")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # Attempt to get images for voting, and handle case where no images are available
    try:
        images = get_biased_pair()
    except ValueError as _:
        return templates.TemplateResponse(
            "front.html", 
            context={
                "skip": True,
                "img1": "", 
                "img2": "",
                "img1_name": "",
                "img2_name": "",
                "vote_token": "",
                "request": request,
            }
        )

    # Create vote token and get image names
    vote_token = str(uuid.uuid4())
    img1_name = images[0].split("/")[-1]
    img2_name = images[1].split("/")[-1]
    current_voting_tokens[vote_token] = [img1_name, img2_name]

    # Return the voting template
    return templates.TemplateResponse(
        "front.html", 
        context={
            "skip": False,
            "img1": images[0], 
            "img2": images[1],
            "img1_name": img1_name,
            "img2_name": img2_name,
            "vote_token": vote_token,
            "request": request,
        }
    )


@app.post('/vote')
def vote(vote: Vote):
   try:
        # Check vote validity
        if vote.vote_token not in current_voting_tokens:
            raise HTTPException(status_code=400, detail="Invalid vote")
        if vote.winner not in [vote.img1, vote.img2]:
            raise HTTPException(status_code=400, detail="Invalid vote")
        if vote.img1 != current_voting_tokens[vote.vote_token][0] or vote.img2 != current_voting_tokens[vote.vote_token][1]:
            raise HTTPException(status_code=400, detail="Invalid vote")
        
        # Append the vote to the CSV file
        with open(CSV_FILE_PATH, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([vote.img1, vote.img2, vote.winner, str(time.time())])
            current_voting_tokens.pop(vote.vote_token)
        return f"Voted for {vote.winner}!"
   except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/winner')
def winner(request: Request):
    """"
    Returns the current winner image and id
    """
    try:
        rows = []
        with open(CSV_FILE_PATH, mode='r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                rows.append(row)
        # Count the number of wins for each image
        votes = Counter(row['Winner'] for row in rows)
        winner_id, _votes = votes.most_common(1)[0]

        # Return the winner image and id
        return templates.TemplateResponse(
            name="winner.html", 
            context={
                "image_id": winner_id,
                "image_url": f"/generated_images/{winner_id}",
                "request": request
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def get_biased_pair():
    """
    TODO: Read the vote, and use biased sampling to return a pair of images.
    """
    images = list(Path(IMAGES_DIR).glob('*'))
    image_paths = [f"/generated_images/{img.name}" for img in images]
    return random.sample(image_paths, k=2)


@app.get('/gallery')
def gallery(request: Request):
    """
    Returns a list of all images in the generated_images.
    Include all image type files
    """
    response = templates.TemplateResponse(
        name="gallery.html", 
        context={
            "request": request
        }
    )
    # Cache the response for 1 minute
    response.headers["Cache-Control"] = "max-age=60"

    return response

@app.get('/get_all_images')
def get_all_images():
    """
    Returns a list of all images in the generated_images.
    Include all image type files
    """
    images = list(Path(IMAGES_DIR).glob('*'))
    image_paths = [f"/generated_images/{img.name}" for img in images]
    return image_paths
