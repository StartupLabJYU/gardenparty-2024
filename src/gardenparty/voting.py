import random
from .app import create_app, settings
from .models import Vote
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request


app = create_app()

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
    """
    Send a vote to the server.
    
    TODO: Record the vote
    """
    return f"Voted for {vote.winner}!"

@app.get('/vote')
def get_votes():
    """"
    Frontend can use this endpoint to get the number of votes.
    """
    ...


def get_biased_pair():
    """
    TODO: Read the vote, and use biased sampling to return a pair of images.
    """
    # For now select two random images from settings.generated_images_dir
    images = list(settings.generated_images_dir.glob('*.png'))
    return random.sample(images, k=2)
