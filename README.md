# Gardeparty

FastAPI app for doing the drawing stuff in JYU IT's garde party event.

## Details

- Images are stored in `/app/instance/...`
- Apis can be tested in `http://localhost:8000/docs`

- To add dependencies, use command `poetry add <package>`
- To install dependencies, use command `poetry install`
- To run the app, use command `poetry run uvicorn gardenparty.voting:app --reload` 

if no poetry but conda in use then do:
- `pip install -e .`
- `uvicorn gardenparty.voting:app --reload` (you may have to be in the folder `src/gardenparty`) 

If you want to test for example backend then replace `.voting` with `.backend`.


- When using the models you should have .env file in your folder structure. Do not put it in `src/*`. The `.env` file must contain the environment variables (such as `OPENAI_API_KEY`) and they need to be declared in the `Settings` class in file `models.py`. 

<b>Example of .env content:</b>
OPENAI_API_KEY="abc123..."
STABILITYAI_API_KEY="xyz987..."
