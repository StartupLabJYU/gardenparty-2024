# calls to server and external 3rd parties

from app import app # our app
from fastapi import FastAPI
from typing import Union # use together with FastAPI

async def some_library(prompt:str) -> str: 
    return "hello world"

@app.get("/call_llm/{prompt}")
def get_llm_response(prompt:str) -> str:
    results = some_library(prompt)
    return results 