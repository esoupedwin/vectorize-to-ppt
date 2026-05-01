# VECTORISE

Convert raster images (PNG/JPG) into editable PowerPoint slides made of smooth vector freeform shapes with Bezier handles.

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 18 + Vite + TypeScript |
| Backend | FastAPI + Uvicorn |
| Image processing | OpenCV, Pillow, SciPy |
| Vectorisation | K-means quantisation → contour extraction → Gaussian smoothing → Catmull-Rom Bezier |
| PowerPoint | python-pptx + direct OOXML (`<a:cubicBezTo>`) |

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

API running at **http://localhost:8000** · Swagger docs at **http://localhost:8000/docs**

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

App running at **http://localhost:5173**

---

## Usage

1. Open **http://localhost:5173** in a browser.
2. Drop or upload a PNG/JPG image (max 10 MB).
3. Adjust sliders:
   - **Colour layers** — number of K-means colour clusters (2–24). More clusters = finer colour detail but more shapes.
   - **Detail level** — controls contour smoothness (0 % = most smoothed/simplified, 100 % = closest to original pixel outline).
4. Click **Convert to PowerPoint**.
5. Click **Download .pptx** when the button appears.
6. Open in PowerPoint. Right-click any shape → **Edit Points** to adjust Bezier vertices.

---

## Pipeline

```
Image bytes
    │
    ▼  preprocess.py
Composite transparency → white background
Resize to max 1200 px (longest edge)
K-means colour quantisation  →  quantized image + palette centers
    │
    ▼  vectorize.py
Build dark-separator mask
│   Union all dark colours (luminance < 50)
│   Dilate 4 px (5×5 ellipse kernel × 2 iterations)
│   → closes outline gaps in line art / JPEG artefacts
│
For each palette colour:
│   Binary mask via cv2.inRange
│   Light colours: AND-NOT with dark-separator
│   │   → forces enclosed regions (white body) apart from background
│   Morphological close (3×3) to seal hairline gaps
│   cv2.findContours  RETR_TREE + CHAIN_APPROX_NONE
│   Even-depth filter  (depth 0, 2, 4 … = foreground; odd = holes)
│   For each valid contour:
│       Gaussian 1-D smoothing  (scipy.ndimage.gaussian_filter1d, mode=wrap)
│       Uniform arc-length resample to N evenly-spaced points
│       Append (area, colour, points) to global list
│
Sort all shapes by area descending  →  large backgrounds paint first
    │
    ▼  pptx_builder.py
Scale pixel coords → EMU (centred, aspect-ratio preserved, 16:9 slide)
For each shape:
│   Compute Catmull-Rom cubic Bezier control points
│   │   CP1 = P[i]   + (P[i+1] − P[i−1]) / 6
│   │   CP2 = P[i+1] − (P[i+2] − P[i])   / 6
│   Bounding box over endpoints + control points (control pts can overshoot)
│   Build <a:moveTo> + N×<a:cubicBezTo> + <a:close> inside <a:path>
│   Wrap in <p:sp> with solidFill and noFill border
│   Parse with lxml, append directly to slide._spTree
    │
    ▼
.pptx bytes → HTTP response
```

### Why these design choices?

| Decision | Reason |
|---|---|
| Dark separator mask | Line-art images: white background and white interior share one K-means cluster. A 1-px outline gap makes them one connected component → black silhouette covers everything. Dilating dark colours 4 px forces them apart. |
| RETR_TREE + even-depth | `RETR_EXTERNAL` only returns outermost contours. Depth-2 contours (island inside hole, e.g. the white body inside a black ring) are invisible to it. Even-depth filter keeps foreground at all nesting levels. |
| Gaussian smooth + uniform resample | Raw OpenCV contours are integer pixel coordinates (staircase noise). Gaussian wrapping removes noise. Uniform arc-length spacing is required so Catmull-Rom's equal-Δt formula produces correct handles — non-uniform spacing causes bad tangents at clustered points. |
| Catmull-Rom → cubic Bezier | The curve passes through every resampled point with C1 continuity. Each segment needs only 3 numbers (cp1, cp2, endpoint) — compact and directly expressible as `<a:cubicBezTo>`. |
| Direct OOXML instead of FreeformBuilder | python-pptx's `FreeformBuilder` only emits `<a:lnTo>` (straight-line segments). Smooth Bezier curves require `<a:cubicBezTo>`, which must be written directly into the XML. |
| Per-shape Z-order, not per-colour grouping | A black outline ring's `cv2.contourArea` includes its enclosed interior, so it sorts before the white island inside it. Grouping by colour would put both whites together, rendering the interior before the black ring and producing a silhouette. |

---

## API

```
POST /convert
  ?n_colors=8          (int, 2–24, default 8)
  ?detail_level=0.7    (float, 0.0–1.0, default 0.7)
  body: multipart/form-data { image: <file> }

→ 200  application/vnd.openxmlformats-officedocument.presentationml.presentation
→ 400  unsupported content type
→ 413  file too large (> 10 MB)
→ 422  image could not be processed
→ 500  internal processing error
```

`detail_level` controls two coupled parameters:

| detail_level | target point spacing | Gaussian σ |
|---|---|---|
| 0.0 (smoothest) | 28 px | 3.5 |
| 0.5 (default) | 17 px | 2.25 |
| 1.0 (most detailed) | 6 px | 1.0 |

---

## Tips for best results

| Image type | Colour layers | Detail level |
|---|---|---|
| Simple icon / logo (2–3 colours) | 4–6 | 50–70 % |
| Flat cartoon / sticker | 8–12 | 60–80 % |
| Outlined line art | 8–14 | 50–70 % |
| UI screenshot / diagram | 12–16 | 65–85 % |

- Works best on **flat, high-contrast images** — logos, icons, stickers, diagrams.
- For line art with a black outline, keep colour count high enough to separate the outline from fills.
- Photorealistic photos produce hundreds of small shapes; lower colour count and detail level significantly.
- Transparent PNGs are composited onto white before processing.
- The white background becomes a white shape on the slide — select and delete it if not needed.

---

## Project structure

```
VECTORISE/
├── backend/
│   ├── main.py                  FastAPI app, /health, /convert endpoint
│   ├── requirements.txt
│   └── pipeline/
│       ├── preprocess.py        PIL load, alpha composite, resize, K-means quantisation
│       ├── vectorize.py         Dark separator, RETR_TREE contours, Gaussian smooth,
│       │                        uniform resample, global area sort
│       └── pptx_builder.py      Catmull-Rom → cubic Bezier, direct OOXML <p:sp> builder
├── frontend/
│   ├── index.html
│   ├── vite.config.ts           Proxy /convert → localhost:8000
│   ├── package.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx              Drag-drop upload, colour/detail sliders, download
│       └── App.css
├── start-backend.ps1
├── start-frontend.ps1
└── README.md
```

---

## Known limitations

- Very detailed images (high colour count + high detail) can produce thousands of shapes, which may make the PPTX slow to open in PowerPoint.
- JPEG compression artefacts create colour fringing near edges; the dark separator mitigates this for outlined images but fine detail may still produce noisy edge shapes.
- Gradients are approximated as flat colour bands — increase colour count to reduce banding.
- Processing time scales with image area and colour count; images above 1200 px are automatically downscaled.
