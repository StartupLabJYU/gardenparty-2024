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
    """Send given prompt to LLM provider."""
    results = some_llm_provider(prompt)
    return results