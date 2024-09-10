import random
from .app import create_app, settings
from .models import Vote
from fastapi.responses import HTMLResponse


app = create_app()

@app.get("/", response_class=HTMLResponse)
def index():
    # https://fastapi.tiangolo.com/advanced/templates/#using-jinja2templates
    return "<marguee>Hello, World!</marquee>"


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
