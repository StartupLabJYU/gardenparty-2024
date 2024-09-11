import json
import logging
from pathlib import Path
import re

from pydantic import BaseModel, Field
from .app import create_app, settings
import base64
from fastapi import FastAPI
from openai import OpenAI
import os
import pathlib
import requests
from typing import Union, Dict # use together with FastAPI

from jinja2 import Template

app = create_app()

logger = logging.getLogger(__name__)


# Prompts. They are in Jinja2 format.
DESCRIBE_IMAGE_PROMPT = """
Here is a drawing in a paper. Describe the drawing, and features it has with locations. Avoid Ambiguity. Incorporate Emotions and Atmosphere. Include Context. Use Descriptive Language. No yapping. 
"""

MERGE_PROMPTS_PROMPT = """
To write image generation prompt, the following is recommended:
 - Detailed Prompts: A good prompt needs to be specific and detailed, including keywords for the subject, medium, style, and additional details.
 - Keyword Categories: Use categories like subject, medium, style, resolution, and additional details to refine your prompt.
 - Negative Prompts: These specify what you don’t want in the image, helping to steer the output more precisely.
 - Keyword Weighting: Adjust the importance of keywords using syntax to fine-tune the generated images.
 - `prompt`: What you wish to see in the output image. A strong, descriptive prompt that clearly defines elements, colors, and subjects will lead to better results. To control the weight of a given word use the format (word:weight), where word is the word you'd like to control the weight of and weight is a value between 0 and 1. For example: The sky was a crisp (blue:0.3) and (green:0.8) would convey a sky that was blue and green, but more green than blue.
 - `negative_prompt`: A blurb of text describing what you do not wish to see in the output image.

You are given a task to write an image generation prompt from the description. Focus on the description, supplement with provided theme.

## Theme for context

    {{prompt_template|indent(4)}}    

## Image description

    {{description|indent(4)}}

## Repsonse

You MUST Write response in the following json format:

```json
{
    "prompt": "<prompt>",
    "negative_prompt": "<negative prompt>",
}
```
"""

def gen_prompt(template: str, **kwargs):
    """Render a prompt template with the given keyword arguments."""
    return Template(template).render(**kwargs)


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
    input_filename = settings.INSTANCE_PATH / "original" / img
    print('input_filename: ', input_filename)
    print('os.getcwd(): ', os.getcwd())

    # Function to encode the image
    def encode_image(image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    # Getting the base64 string
    base64_image = encode_image(input_filename)

    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OpenAI API key not set")

    # set up client credentials
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
    }

    prompt = gen_prompt(DESCRIBE_IMAGE_PROMPT)    

    # set encoded image to request body
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": prompt,
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
        "max_tokens": 600
    }

    # get description
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

    #print(response.json()['choices'][0]['message']['content'])

    logger.info(f"Image description: {response.json()}")

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
def image_to_image(img:str, prompt:str, negative_prompt:str="", seed:int=42, strength:float=0.6):
    """Image to image using stable diffusion's service. Please note that the image file name must end with .jpg not .jpeg."""
    

    print('settings.original_images_dir: ', settings.INSTANCE_PATH / 'original' / img)

    # You can try with: ./original/hunger_in_the_olden_days.jpg
    input_filename = settings.INSTANCE_PATH / 'original' / img
    
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
            "negative_prompt": negative_prompt,
            "image": input_filename,
            "output_format": "jpeg",
            "strength":strength,
            "mode":"image-to-image",
            "model":"sd3-medium",
            "seed":seed
        },
    )

    if response.status_code == 200:
        print("200")
        output_filename = settings.INSTANCE_PATH / 'generated'/ f"{img}"
        output_filename = str(output_filename)
        with open(output_filename, 'wb') as file:
            file.write(response.content)

        return {"result": 200, "prompt":prompt, "strength":strength, "seed":seed, 'output_filename': output_filename}

    else:
        if response.json()['name'] == 'content_moderation':
            return {"result": "Dirty word detected!", "prompt":prompt, "strength":strength, "seed":seed, "response": str(response.json())}
        else:
            print("No luck!")
            return response.json()
        

def merge_template_prompt(prompt_template:str, description:str):
    """Merge selected prompt template with description of the scanned image."""

    # prompt_template = """Make environment as nature scant as possible. Add to the background high rises, forms of transport, and neon signs and neon colors. 
    #     Depict chaos in the background while promoting unity of IT faculty. Contrast between chaos and unity. 
    #     DO NOT force the background color."""

    # description = """
    #     The image features a simple drawing on a blue background. 
    #     On the left, there is a stick figure holding a spear, pointing it upwards. 
    #     On the right, there is a sketch of an animal that resembles a pig. 
    #     The overall scene suggests a possible hunting or spear-throwing scenario involving the animal."""

    # set up client credentials
    client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            )

    prompt = gen_prompt(MERGE_PROMPTS_PROMPT, prompt_template=prompt_template, description=description)

    print(prompt)

    # make the call with chosen model
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": prompt
            }   
        ]
    )
    
    response = completion.choices[0].message.content
    response_prompt = response
    response_negative_prompt = "penis"

    try:
        # Try extracting the json block from the response
        match = re.split(r"```json\n(.*)\n```", response, flags=re.MULTILINE | re.DOTALL)
        logger.debug("Match: %r", match)
        text = match[1]
        data = json.loads(text)
        response_prompt = data["prompt"]
        response_negative_prompt = data["negative_prompt"]
    except Exception as e:
        logger.error("Error extracting JSON block: %r", e)
 
    # return reply in a dict
    #print(completion.choices[0].message)
    return {
        'prompt_template': prompt_template, 
        'description':description, 
        'reply':completion.choices[0].message.content,
        'prompt':response_prompt,
        'negative_prompt':response_negative_prompt
        }


@app.get("/merge/{prompt_template_name}/{img}")
@app.get("/merge/{prompt_template_name}/{img}/{strength}")
async def merged_prompt_to_image(prompt_template_name:str, img:str, strength:float=0.6) -> Dict:
    """Take prompt template name and image name. return merged prompt text."""

    # get prompt template content
    prompt_template = None
    prompt_template_path = os.path.join('./src/gardenparty/prompt_templates', prompt_template_name)
    with open(prompt_template_path, 'r') as f:
        prompt_template = f.readlines()[0]

    #print("prompt_template OK")

    # get description
    description = describe_image(img)['reply']
    #print("description OK")

    # new merged prompt
    prompt = merge_template_prompt(prompt_template, description)['reply']
    #print("prompt OK")
    # make the new image
    response = await image_to_image(img, prompt, seed=42, strength=strength)
    #print("response OK")
    print(response)
    return response


def generate_themed_prompt(theme, context):
    """
    Combine theme and context to generate an prompt.
    """
    theme_files = get_templates()['files']
    
    # Find matching theme file
    for f in theme_files:
        if theme == Path(f).stem:
            with open(f, 'r') as file:
                theme_prompt = file.read()
                break
    else:
        raise ValueError(f"Theme {theme!r} not found in the prompt_templates directory.")
    
    # Merge theme and context
    return merge_template_prompt(theme_prompt, context)
