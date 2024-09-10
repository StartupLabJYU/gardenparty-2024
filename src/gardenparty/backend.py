from .app import create_app
from fastapi import FastAPI
from typing import Union, Dict # use together with FastAPI
import os
app = create_app()

# Add routes

# calls to server and external 3rd parties
def some_llm_provider(prompt:str) -> Dict: 
    """Use some LLM provider to get a response to prompt."""
    from openai import OpenAI
    from .app import settings
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
        