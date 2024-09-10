from .app import create_app, settings
import base64
from fastapi import FastAPI
from openai import OpenAI
import os
import requests
from typing import Union, Dict # use together with FastAPI
app = create_app()

# Add routes
@app.get("/all_templates")
def get_templates() -> Dict:
    """Returns a dictionary object with the list of templates to select."""
    if os.path.exists("./src/gardenparty/prompt_templates"):
        files = []
        print("Prompt templates exists")
        for root, dirnames, filenames in os.walk('./src/gardenparty/prompt_templates/'):
            for filename in filenames:
                files.append(os.path.join(root, filename))
        
        return {'files':files}
    return {'files':None}


@app.get("/describe_image/{img}")
def describe_image(img:str) -> Dict:
    """Using OpenAI describe the content of given image."""

    # You can try with: ./original/hunger_in_the_olden_days.jpg
    input_filename = os.path.join(settings.original_images_dir, img)
    print('input_filename: ', input_filename)
    print('os.getcwd(): ', os.getcwd())

    # Function to encode the image
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    # Getting the base64 string
    base64_image = encode_image(input_filename)

    # set up client credentials
    headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
    }

    # set encoded image to request body
    payload = {
    "model": "gpt-4o-mini",
    "messages": [
        {
        "role": "user",
        "content": [
            {
            "type": "text",
            "text": "What’s in this image?"
            },
            {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{base64_image}"
            }
            }
        ]
        }
    ],
    "max_tokens": 300
    }

    # get description
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    #print(response.json()['choices'][0]['message']['content'])
    
    # return reply in a dict
    return {'img': input_filename, 'reply':response.json()['choices'][0]['message']['content']}


# calls to server and external 3rd parties
def some_llm_provider(prompt:str) -> Dict: 
    """Use some LLM provider to get a response to prompt."""

    # set up client credentials
    client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            )

    # make the call with chosen model
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": f"Explain what is this: {prompt}"
            }
        ]
    )

    # return reply in a dict
    #print(completion.choices[0].message)
    return {'prompt': prompt, 'reply':completion.choices[0].message.content}


@app.get("/call_llm/{prompt}")
def get_llm_response(prompt:str) -> Dict:
    """Send given prompt to LLM provider and do expect a textual answer back."""
    results = some_llm_provider(prompt)
    return results


@app.get("/img_to_image/{strength}/{img}/{prompt}")
@app.get("/img_to_image/{img}/{prompt}")
async def image_to_image(img:str, prompt:str, seed:int=42, strength:float=0.6):
    """Image to image using stable diffusion's service. Please note that the image file name must end with .jpg not .jpeg."""
    import requests
    from .app import settings

    print('settings.original_images_dir: ', settings.original_images_dir)

    # You can try with: ./original/hunger_in_the_olden_days.jpg
    input_filename = os.path.join(settings.original_images_dir, img)
    
    response = requests.post(
        f"https://api.stability.ai/v2beta/stable-image/generate/sd3",
        headers={
            "authorization": f"Bearer {settings.STABILITYAI_API_KEY}",
            "accept": "image/*"
        },
        files={
            "image": open(input_filename, "rb"),
        },
        data={
            "prompt": prompt,
            "image": input_filename,
            "output_format": "jpeg",
            "strength":strength,
            "mode":"image-to-image",
            "model":"sd3-medium",
            "seed":seed,
            "negative_prompt":"penis"
        },
    )

    if response.status_code == 200:
        output_filename = os.path.join(settings.generated_images_dir, img)
        with open(output_filename, 'wb') as file:
            file.write(response.content)
        
        return {"result": 200, "prompt":prompt, "strength":strength, "seed":seed}

    else:
        if response.json()['name'] == 'content_moderation':
            return {"result": "Dirty word detected!", "prompt":prompt, "strength":strength, "seed":seed, "response": str(response.json())}
        

def merge_template_prompt(prompt_template:str, description:str):
    """Merge selected prompt template with description of the scanned image."""
    # set up client credentials
    client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            )

    # make the call with chosen model
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": f"Merge these user inputs into a prompt for creating an image. INPUT 1: {prompt_template}, INPUT 2: {description}."
            }
        ]
    )

    # return reply in a dict
    #print(completion.choices[0].message)
    return {
        'prompt_template': prompt_template, 
        'description':description, 
        'reply':completion.choices[0].message.content
        }
