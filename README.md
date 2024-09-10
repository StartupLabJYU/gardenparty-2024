# Gardeparty

FastAPI app for doing the drawing stuff in JYU IT's garde party event.

## Details

- Images are stored in `/app/instance/...`
- Apis can be tested in `http://localhost:8000/docs`

- To add dependencies, use command `poetry add <package>`
- To install dependencies, use command `poetry install`
- To run the app, use command `poetry run uvicorn gardenparty.voting:app --reload` 

if no poetry but conda in use then do:
- pip install -e .
- uvicorn gardenparty.voting:app --reload (you may have to be in the folder `src/gardenparty`) 

If you want to test for example backend then replace `.voting` with `.backend`.


