from .app import create_app
from fastapi import FastAPI
from typing import Union # use together with FastAPI

app = create_app()

# Add routes


# calls to server and external 3rd parties
def some_llm_provider(prompt:str) -> str: 
    """Use some LLM provider to get a response to prompt."""
    
    return prompt + " world"

@app.get("/call_llm/{prompt}")
def get_llm_response(prompt:str) -> str:
    """Send given prompt to LLM provider."""
    results = some_llm_provider(prompt)
    return results 