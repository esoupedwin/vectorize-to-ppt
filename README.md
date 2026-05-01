# VECTORISE

Convert raster images (PNG/JPG) into editable PowerPoint slides made of vector freeform shapes.

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 18 + Vite + TypeScript |
| Backend | FastAPI + Uvicorn |
| Image processing | OpenCV, Pillow |
| Vectorisation | OpenCV contour extraction + Douglas-Peucker simplification |
| PowerPoint | python-pptx freeform shapes |

---

## Quick Start

You need **Python 3.10+** and **Node.js 18+** on your PATH.

### 1 — Backend

```powershell
# Terminal 1
.\start-backend.ps1
```

Or manually:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API is now running at **http://localhost:8000**.  
Swagger docs at **http://localhost:8000/docs**.

### 2 — Frontend

```powershell
# Terminal 2
.\start-frontend.ps1
```

Or manually:

```powershell
cd frontend
npm install
npm run dev
```

App is now running at **http://localhost:5173**.

---

## Usage

1. Open **http://localhost:5173** in a browser.
2. Drop or upload a PNG/JPG image (max 10 MB).
3. Adjust sliders:
   - **Colour layers** — number of K-means colour clusters (2–24). More = finer colour detail.
   - **Detail level** — how closely contours follow the original shape (0 = most simplified, 100 = most detailed).
4. Click **Convert to PowerPoint**.
5. Click **Download .pptx** when done.
6. Open the file in PowerPoint. Right-click any shape → **Edit Points** to adjust vertices.

---

## Pipeline

```
Image bytes
    │
    ▼ preprocess.py
Composite alpha → white bg
Resize to max 1200px
K-means colour quantisation
    │
    ▼ vectorize.py
For each colour → binary mask
OpenCV findContours (RETR_EXTERNAL)
Douglas-Peucker simplification
Sort by area (large shapes first)
    │
    ▼ pptx_builder.py
Scale image coords → EMU
build_freeform() per contour
Apply solid fill colour
No border
    │
    ▼
.pptx bytes → HTTP response
```

---

## API

```
POST /convert
  ?n_colors=8          (int, 2–24)
  ?detail_level=0.5    (float, 0.0–1.0)
  body: multipart/form-data { image: <file> }

→ 200  application/vnd.openxmlformats-…  (pptx bytes)
→ 400  bad content type
→ 413  file too large
→ 422  unprocessable image
→ 500  processing error
```

---

## Tips for best results

| Image type | Recommended settings |
|---|---|
| Simple icon (2–3 colours) | Colours: 4–6, Detail: 40–60% |
| Flat illustration | Colours: 8–12, Detail: 50–70% |
| UI screenshot | Colours: 12–16, Detail: 60–80% |

- Works best on **flat, high-contrast images** — logos, icons, diagrams.
- Photorealistic images produce many small shapes; reduce colour count and detail level.
- White backgrounds become a white shape on the slide — you can delete it.

---

## Project structure

```
VECTORISE/
├── backend/
│   ├── main.py                  FastAPI app & /convert endpoint
│   ├── requirements.txt
│   └── pipeline/
│       ├── preprocess.py        Colour quantisation (K-means)
│       ├── vectorize.py         Contour extraction & simplification
│       └── pptx_builder.py      PowerPoint freeform shape builder
├── frontend/
│   ├── index.html
│   ├── vite.config.ts           Proxy /convert → localhost:8000
│   ├── package.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx              Upload UI, sliders, download
│       └── App.css
├── start-backend.ps1
├── start-frontend.ps1
└── README.md
```
