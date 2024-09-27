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
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request

logger = logging.getLogger(__name__)
app = create_app()

# Path to the CSV file where the votes will be stored
CSV_FILE_PATH = Path(settings.INSTANCE_PATH) / 'vote_results.csv'
MODERATION_FILE_PATH = Path(settings.INSTANCE_PATH) / 'accepted.csv'
IMAGES_DIR = Path(settings.INSTANCE_PATH) / 'generated'
STATIC_DIR = get_pkg_path() / 'static'
TEMPLATES_DIR = get_pkg_path() / 'templates'

# Stores random uuids to prevent repeat voting
current_voting_tokens = {}

# Headlines for the voting page
headlines = [
    "Kumpi kuva miellyttää sinua enemmän?",
    "Klikkaa kuvaa, josta pidät enemmän!",
    "Äänestä suosikkikuvaasi!",
    "Mikä kuva on parempi?",
    "Valitse paras kuva!",
    "Auta meitä ratkaisemaan tämä kuvakiista!",
    "Tee valintasi ennen kuin julistamme tasapelin!",
    "Valitse sankarisi näistä kuvahaastajista!",
    "Mikä kuva saa sinut hymyilemään enemmän?",
    "Ole tuomari! Mikä kuva voittaa tänään?",
    "Katsotaan, mikä kuva hallitsee!",
    "Mielipiteelläsi on väliä! Valitse voittajakuva!",
    "Valitse kuva, joka saa sydämesi sykähtelemään!",
    "Auta päättämään kuvakohtaaminen!",
    "Mikä kuva ansaitsee kruunun?",
    "On aika toimia tuomarina! Mikä kuva on voittaja?",
    "Vapauta sisäinen kriitikkosi! Valitse paras kuva!",
    "Mikä kuva on todellinen supertähti?",
    "Valitse mestarisi näistä kuvahaastajista!",
    "Klikkaa kuvaa, joka miellyttää sinua eniten!",
    "Äänesi päättää näiden kuvien kohtalon!",
    "Anna äänesi ja vaikuta lopputulokseen!",
    "Jokainen ääni on tärkeä! Valitse suosikkisi!",
    "Auta meitä valitsemaan lopullinen kuvamestari!",
    "Ole osa kuvataistelua! Tee valintasi!"
]


# Voting responses
voting_responses = [
    "Kiitos, että kerroit meille mieltymyksesi!",
    "Valintasi on tallennettu. Kiitos äänestämisestä!",
    "Arvostamme ääntäsi! Kiitos, että autat meitä päättämään!",
    "Kiitos mielipiteestäsi! Arvostamme valintaasi!",
    "Äänesi on kirjattu! Kiitos, että autat valitsemaan parhaan kuvan!",
    "Kiitos, että ratkoit tasapelin! Arvostamme ääntäsi!",
    "Äänesi pelasti tilanteen! Kiitos, että olet mahtava!",
    "Olet valinnut sankarin! Kiitos, että autat meitä valitsemaan!",
    "Kiitos, että sait meidät hymyilemään äänelläsi!",
    "Olet kruunannut voittajan! Kiitos äänestäsi!",
    "Kiitos, että valitsit parhaan kuvan!",
    "Arvostamme mielipidettäsi! Kiitos, että annoit äänesi!",
    "Valintasi on huomioitu! Kiitos, että jätit jälkesi!",
    "Kiitos, että ratkaisit kuvakohtaamisen!",
    "Kuvakruunu on jaettu, kiitos äänestäsi!",
    "Tuomarin tehtävä suoritettu! Kiitos valinnastasi!",
    "Sisäinen kriitikkosi osui oikeaan! Kiitos äänestämisestä!",
    "Olet valinnut supertähden! Kiitos äänestäsi!",
    "Mestari on valittu! Kiitos, että valitsit parhaan haastajan!",
    "Valintasi ilahdutti meitä! Kiitos äänestämisestä!",
    "Äänesi on tehnyt eron! Kiitos osallistumisesta!",
    "Kiitos, että annoit äänesi ja muokkasit lopputulosta!",
    "Jokainen ääni merkitsee, ja arvostamme sinun ääntäsi! Kiitos!",
    "Kiitos, että autat meitä valitsemaan lopullisen kuvamestarin!",
    "Olet ollut avainpelaaja kuvataistelussa! Kiitos äänestämisestä!"
]





@app.on_event("startup")
def startup_event():
    # Ensure CSV file exists and has the header
    if not os.path.exists(CSV_FILE_PATH):
        with open(CSV_FILE_PATH, mode='w') as file:
            writer = csv.writer(file)
            writer.writerow(['Image 1', 'Image 2', 'Winner', 'Timestamp'])  # Write header if the file is created

    if not os.path.exists(MODERATION_FILE_PATH):
        with open(MODERATION_FILE_PATH, mode='w') as file:
            writer = csv.writer(file)
            writer.writerow(['filename', 'status'])  # Write header if the file is created


# Pydantic model for vote data validation
class Vote(BaseModel):
    img1: str
    img2: str
    winner: str
    vote_token: str

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/generated_images", StaticFiles(directory=IMAGES_DIR), name="generated_images")
app.mount("/original_images", StaticFiles(directory=Path(settings.INSTANCE_PATH) / 'original'), name="original_images")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # Attempt to get images for voting, and handle case where no images are available
    images = get_biased_pair()
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
    vote_matrix = np.full((len(image_names), len(image_names)), 0.01)
    np.fill_diagonal(vote_matrix, 0)
    
    pair_matrix = np.empty((len(image_names), len(image_names)), dtype=object)
    for y in list(range(0, len(image_names))):
        for x in list(range(0, len(image_names))):
            pair_matrix[y, x] = (image_names[y], image_names[x])

    # Read the votes so far, and fill the vote matrix correspondingly
    vote_count = 0
    with open(CSV_FILE_PATH, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                x_index = image_names.index(row['Image 1'])
                y_index = image_names.index(row['Image 2'])
                if vote_matrix[x_index, y_index] < 1:
                    vote_matrix[x_index, y_index] = 1
                else:
                    vote_matrix[x_index, y_index] += 1
                vote_count += 1
            except ValueError as _:
                pass

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
        return unbiased_pair[0]
    
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


# @app.get('/moderation')
# def moderation(request: Request):
#     # Get the full list of all generated images
#     images = list(Path(IMAGES_DIR).glob('*'))
#     image_paths = [f"/generated_images/{img.name}" for img in images]

#     # Read the votes so far, and fill the vote matrix correspondingly
#     with open(MODERATION_FILE_PATH, mode='r') as file:
#         reader = csv.DictReader(file)
#         for row in reader:
#             x_index = image_names.index(row['Image 1'])
#             y_index = image_names.index(row['Image 2'])
#             if vote_matrix[x_index, y_index] < 1:
#                 vote_matrix[x_index, y_index] = 1
#             else:
#                 vote_matrix[x_index, y_index] += 1
#             vote_count += 1


# @app.get('/get_next_unmoderated')
# def get_next_unmoderated():
#     """
#     Returns a single file that is unmoderated
#     """
#     images = list(Path(IMAGES_DIR).glob('*'))
#     image_paths = [f"/generated_images/{img.name}" for img in images]

#     # Find the filepaths that are not yet in the moderation file
#     accepted_dict = {}
#     with open(MODERATION_FILE_PATH, mode='r') as file:
#         reader = csv.DictReader(file)
#         for row in reader:
#             accepted_dict[row['filename']] = row["status"]

#     for image in image_paths:

#     return image_paths

@app.get('/pair.json')
def get_image_pair():
    
    weights = []
    images = []
    for image in Path(IMAGES_DIR).glob('*'):
        images.append(f"/generated_images/{image.name}")
        # file modification time in seconds
        mtime = os.path.getmtime(image)
        # current time in seconds
        weights.append(mtime)

    # normalize weights
    weights = np.array(weights)
    weights = weights - weights.min()
    weights = weights / weights.sum()
    # Select two images with probability proportional to the time since last modification
    pair = np.random.choice(images, size=2, replace=False, p=weights/weights.sum())
    
    response = JSONResponse(content={"image1": pair[0], "image2": pair[1]})
    response.headers["Cache-Control"] = "max-age=17"

    return response


@app.get('/fullscreen')
def page_fs(request: Request):
    response = templates.TemplateResponse(
        name="fullscreen.html", 
        context={
            "request": request
        }
    )
    return response


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

    # Compare the list of images to list of accepted images
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
    # results = get_scores()
    # results = sort_by_results(results)

    images = list(Path(IMAGES_DIR).glob('*'))

    # Compare the list of images to list of accepted images
    generated_urls = [f"/generated_images/{img.name}" for img in images]
    original_urls = [f"/original_images/{img.name}" for img in images] 

    return templates.TemplateResponse(
        name="results.html", 
        context={
            "request": request,
            # "results": results,
            "original_urls": original_urls,
            "generated_urls": generated_urls
        }
    )
