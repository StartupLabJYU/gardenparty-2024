from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import csv
import os
import time
import random
import uuid
from .app import create_app, settings
from .models import Vote
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request


app = create_app()
# Path to the CSV file where the votes will be stored
CSV_FILE_PATH = '/app/instance/vote_results.csv'

# Stores random uuids to prevent repeat voting
current_voting_tokens = {}

# Ensure CSV file exists and has the header
if not os.path.exists(CSV_FILE_PATH):
    with open(CSV_FILE_PATH, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Image 1', 'Image 2', 'Winner', 'Timestamp'])  # Write header if the file is created


# Pydantic model for vote data validation
class Vote(BaseModel):
    img1: str
    img2: str
    winner: str
    vote_token: str

app.mount("/static", StaticFiles(directory="/app/src/gardenparty/static"), name="static")
app.mount("/generated_images", StaticFiles(directory="/app/instance/generated"), name="images")
templates = Jinja2Templates(directory="/app/src/gardenparty/templates")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    images = get_biased_pair()
    vote_token = str(uuid.uuid4())
    img1_name = images[0].split("/")[-1]
    img2_name = images[1].split("/")[-1]
    current_voting_tokens[vote_token] = [img1_name, img2_name]
    return templates.TemplateResponse(
        name="front.html", 
        context={
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
        votes = {}
        for row in rows:
            if row['Winner'] in votes:
                votes[row['Winner']] += 1
            else:
                votes[row['Winner']] = 1
        # Order the votes by the number of wins
        votes = dict(sorted(votes.items(), key=lambda item: item[1], reverse=True))

        # Get the winner image and id
        winner_id = list(votes.keys())[0]

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
    # For now select two random images from settings.generated_images_dir
    images = list(settings.generated_images_dir.glob('*'))
    image_paths = [f"/generated_images/{img.name}" for img in images]
    return random.sample(image_paths, k=2)


@app.get('/gallery')
def gallery(request: Request):
    """
    Returns a list of all images in the generated_images.
    Include all image type files
    """
    return templates.TemplateResponse(
        name="gallery.html", 
        context={
            "request": request
        }
    )

@app.get('/get_all_images')
def get_all_images():
    """
    Returns a list of all images in the generated_images.
    Include all image type files
    """
    images = list(settings.generated_images_dir.glob('*'))
    image_paths = [f"/generated_images/{img.name}" for img in images]
    return image_paths
