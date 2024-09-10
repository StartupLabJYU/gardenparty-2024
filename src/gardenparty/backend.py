from .app import create_app
from fastapi import FastAPI
from typing import Union # use together with FastAPI

app = create_app()

# Add routes


# calls to server and external 3rd parties
def some_library(prompt:str) -> str: 
    return prompt + " world"

@app.get("/call_llm/{prompt}")
def get_llm_response(prompt:str) -> str:
    results = some_library(prompt)
    return results 