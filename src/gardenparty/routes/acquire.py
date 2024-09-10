from fastapi import APIRouter, HTTPException

router = APIRouter('acquire')

@router.post("/process")
async def process_image(image):
    try:
        image = prepare_image(image)
    except HTTPException as e:
        raise e
    return {"image": image}

