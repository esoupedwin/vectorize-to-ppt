from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from pipeline.preprocess import preprocess_image
from pipeline.vectorize import extract_shapes
from pipeline.pptx_builder import build_pptx

app = FastAPI(title="VECTORISE API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

PPTX_MIME = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/convert")
async def convert(
    image: UploadFile = File(...),
    n_colors: int = Query(default=8, ge=2, le=24),
    detail_level: float = Query(default=0.5, ge=0.0, le=1.0),
):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image (PNG/JPG)")

    contents = await image.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Image too large (max 10 MB)")

    try:
        quantized, h, w, centers = preprocess_image(contents, n_colors=n_colors)
        shapes_data = extract_shapes(quantized, centers, detail_level=detail_level)
        pptx_bytes = build_pptx(shapes_data, img_width=w, img_height=h)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}")

    return Response(
        content=pptx_bytes,
        media_type=PPTX_MIME,
        headers={"Content-Disposition": 'attachment; filename="vectorized.pptx"'},
    )
