import logging
from pathlib import Path
from typing import Counter, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import csv
import os
import time
import random
import uuid
import numpy as np
from .app import create_app, get_pkg_path, settings
from .models import Vote
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request

logger = logging.getLogger(__name__)
app = create_app()

# Path to the CSV file where the votes will be stored
CSV_FILE_PATH = Path(settings.INSTANCE_PATH) / 'vote_results.csv'
IMAGES_DIR = Path(settings.INSTANCE_PATH) / 'generated'
STATIC_DIR = get_pkg_path() / 'static'
TEMPLATES_DIR = get_pkg_path() / 'templates'

# Stores random uuids to prevent repeat voting
current_voting_tokens = {}

# Headlines for the voting page
headlines = [
    "Which image do you prefer?",
    "Click on the image you like more!",
    "Vote for your favourite image!",
    "Which image is better?",
    "Choose the best image!",
    "Help us settle this image debate!",
    "Make your choice before we call it a tie!",
    "Pick your hero from these image contenders!",
    "Which image makes you smile more?",
    "Be the judge! Which image wins the day?",
    "Let’s see which image reigns supreme!",
    "Your opinion matters! Choose the winning image!",
    "Pick the image that makes your heart skip a beat!",
    "Help decide the image showdown!",
    "Which image deserves the crown?",
    "Time to play judge! Which image is a winner?",
    "Unleash your inner critic! Pick the best image!",
    "Which image is the true superstar?",
    "Choose your champion from these image contenders!",
    "Click the image that tickles your fancy!",
    "Your vote decides the fate of these images!",
    "Cast your vote and make a difference!",
    "Every vote counts! Choose your favorite!",
    "Help us choose the ultimate image champion!",
    "Be a part of the image battle! Make your pick!"
]

# Voting responses
voting_responses = [
    "Thanks for letting us know your preference!",
    "Your choice has been recorded. Thanks for voting!",
    "We appreciate your vote! Thanks for helping us decide!",
    "Thanks for your input! We value your choice!",
    "Your vote is in! Thanks for helping us choose the best image!",
    "Thanks for breaking the tie! We appreciate your vote!",
    "Your vote has saved the day! Thanks for being awesome!",
    "You've picked a hero! Thanks for helping us choose!",
    "Thanks for making us smile with your vote!",
    "You’ve crowned a winner! Thanks for your vote!",
    "Thank you for choosing the supreme image!",
    "We value your opinion! Thanks for casting your vote!",
    "Your pick has been noted! Thanks for adding your touch!",
    "Thanks for making the decision in the image showdown!",
    "The image crown is awarded, thanks to your vote!",
    "Judge complete! Thanks for making your choice!",
    "Your inner critic is spot on! Thanks for voting!",
    "You’ve chosen the superstar! Thanks for your vote!",
    "Champion chosen! Thanks for picking the best contender!",
    "Tickled our fancy with your choice! Thanks for voting!",
    "Your vote has made a difference! Thanks for participating!",
    "Thanks for casting your vote and shaping the outcome!",
    "Every vote counts, and we appreciate yours! Thanks!",
    "Thanks for helping us choose the ultimate image champion!",
    "You’ve been a key player in the image battle! Thanks for voting!"
]




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
app.mount("/generated_images", StaticFiles(directory=IMAGES_DIR), name="generated_images")
app.mount("/orginal_images", StaticFiles(directory=Path(settings.INSTANCE_PATH) / 'original'), name="orginal_images")

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
                "headline": "",
                "request": request,
            }
        )

    # Create vote token and get image names
    vote_token = str(uuid.uuid4())
    img1_name = images[0].split("/")[-1]
    img2_name = images[1].split("/")[-1]
    current_voting_tokens[vote_token] = [img1_name, img2_name]

    # Random headline and corresponding vote response
    headline = random.choice(headlines)
    vote_response = voting_responses[headlines.index(headline)]

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
            "headline": headline,
            "vote_response": vote_response,
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

@app.get('/test_page')
def test_page(request: Request):
    """"
    Returns the winner
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
    Read the votes, and use biased sampling to return a pair of images.
    """
    # Get the full list of all generated images
    images = list(Path(IMAGES_DIR).glob('*'))
    image_paths = [f"/generated_images/{img.name}" for img in images]

    # Filter out images that have their creation time less than 2 minutes ago
    image_paths = [img for img in image_paths if time.time() - os.path.getctime(IMAGES_DIR / img.split("/")[-1]) > 120]

    # Create a matrix to hold votes, and a corresponding matrix to hold related pairs of images.
    # Matrix cells are in same order as in the image_names variable (left to right, top to bottom)
    image_names = [i.split("/")[-1] for i in image_paths]
    vote_matrix = np.full((len(image_names), len(image_names)), 0.1)
    np.fill_diagonal(vote_matrix, 0)
    pair_matrix = np.empty((5, 5), dtype=object)
    for y in list(range(0, len(image_names))):
        for x in list(range(0, len(image_names))):
            pair_matrix[y, x] = (image_names[y], image_names[x])

    # Read the votes so far, and fill the vote matrix correspondingly
    vote_count = 0
    with open(CSV_FILE_PATH, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            x_index = image_names.index(row['Image 1'])
            y_index = image_names.index(row['Image 2'])
            if vote_matrix[x_index, y_index] < 1:
                vote_matrix[x_index, y_index] = 1
            else:
                vote_matrix[x_index, y_index] += 1
            vote_count += 1

    # Create a new array that has all cells from matrix EXCEPT the diagonal (cant choose between same image)
    # Remove the diagonal from flattened matrix, and remove corresponding pairs from the pair matrix
    flat_vote_matrix = vote_matrix.flatten()
    flat_pair_matrix = pair_matrix.flatten()
    remove_indexes = np.ones(flat_vote_matrix.shape, dtype=bool)
    for index, value in enumerate(flat_vote_matrix):
        if value == 0:
            remove_indexes[index] = False
    flat_vote_matrix = flat_vote_matrix[remove_indexes]
    flat_pair_matrix = flat_pair_matrix[remove_indexes]

    # Without votes, use unbiased sampling
    if vote_count == 0:
        unbiased_pair = np.random.choice(image_paths, [1,2], replace=False)
        return unbiased_pair
    
    # Add an extra element that makes sure even the most voted item has a small chance of appearing in a vote
    most_voted = np.max(flat_vote_matrix)
    flat_vote_matrix = np.insert(flat_vote_matrix, 0, most_voted + 1, axis=0)
    flat_pair_matrix = np.insert(flat_pair_matrix, 0, 0, axis=0)
    
    # Calculate the weights for choosing the biased pair
    inverse_counts = 1 / flat_vote_matrix
    weights = inverse_counts / inverse_counts.sum()
    
    # Select a pair of images using the biased sampling distribution
    biased_pair = np.random.choice(flat_pair_matrix, p=weights, replace=False)

    # In case the extra element is actually chosen, choose again (the extra element is just 0)
    while not biased_pair:
        biased_pair = np.random.choice(flat_pair_matrix, p=weights, replace=False)

    # Return the result
    return (f"/generated_images/{biased_pair[0]}", f"/generated_images/{biased_pair[1]}")


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

@app.get("/ga")

class VoteResult(BaseModel):
    image: str
    wins: int
    losses: int
    relative_votes: float

@app.get('/scores.json')
def get_scores() -> List[VoteResult]:
    """
    Returns the scores of votes.
    """
    wins = Counter()
    displays = Counter()
    r = []

    with open(CSV_FILE_PATH, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            wins[row['Winner']] += 1
            displays[row['Image 1']] += 1
            displays[row['Image 2']] += 1

    for image in displays:
        if not Path(IMAGES_DIR / image).exists():
            logger.debug(f"Image {image} does not exist") 
            continue
        r.append(VoteResult(
            image=image,
            wins=wins[image],
            losses=displays[image] - wins[image],
            relative_votes=wins[image] / displays[image]
        ))

    return r

def sort_by_results(results: List[VoteResult]) -> List[VoteResult]:
    """
    Sorts the results
    """

    return sorted(results, key=lambda x: (x.relative_votes, x.wins - x.losses), reverse=True)


@app.get('/results', response_class=HTMLResponse)
def results(request: Request):
    """
    Returns the results of the votes.
    """
    results = get_scores()
    results = sort_by_results(results)
    
    origina_urls = [f"/orginal_images/{img.image}" for img in results] 
    generated_urls = [f"/generated_images/{img.image}" for img in results]

    return templates.TemplateResponse(
        name="results.html", 
        context={
            "request": request,
            "results": results,
            "original_urls": origina_urls,
            "generated_urls": generated_urls
        }
    )
