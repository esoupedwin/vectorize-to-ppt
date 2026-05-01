import { useState, useCallback, useRef, DragEvent, ChangeEvent } from 'react'

type ConvertState = 'idle' | 'converting' | 'done' | 'error'

const BACKEND = '/convert'

export default function App() {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [state, setState] = useState<ConvertState>('idle')
  const [error, setError] = useState('')
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [nColors, setNColors] = useState(8)
  const [detail, setDetail] = useState(70) // 0-100 slider → 0.0-1.0
  const fileInputRef = useRef<HTMLInputElement>(null)

  const applyFile = useCallback((f: File) => {
    if (!f.type.startsWith('image/')) {
      setError('Only PNG and JPG images are supported.')
      return
    }
    setFile(f)
    setError('')
    setState('idle')
    setDownloadUrl(null)
    if (preview) URL.revokeObjectURL(preview)
    setPreview(URL.createObjectURL(f))
  }, [preview])

  const onInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) applyFile(f)
    e.target.value = ''
  }

  const onDrop = (e: DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) applyFile(f)
  }

  const onDragOver = (e: DragEvent) => { e.preventDefault(); setIsDragging(true) }
  const onDragLeave = () => setIsDragging(false)

  const convert = async () => {
    if (!file) return
    setState('converting')
    setError('')
    setDownloadUrl(null)

    try {
      const form = new FormData()
      form.append('image', file)

      const url = `${BACKEND}?n_colors=${nColors}&detail_level=${(detail / 100).toFixed(2)}`
      const res = await fetch(url, { method: 'POST', body: form })

      if (!res.ok) {
        let msg = `HTTP ${res.status}`
        try { msg = (await res.json()).detail ?? msg } catch { /* ignore */ }
        throw new Error(msg)
      }

      const blob = await res.blob()
      const dlUrl = URL.createObjectURL(blob)
      setDownloadUrl(dlUrl)
      setState('done')
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      setState('error')
    }
  }

  const hasImage = !!preview

  return (
    <div className="app">
      <header className="header">
        <h1>VECTORISE</h1>
        <p>Convert raster images into editable PowerPoint vector shapes</p>
      </header>

      <main className="main">
        {/* ── Drop Zone ── */}
        <div
          className={`dropzone${isDragging ? ' dragging' : ''}${hasImage ? ' has-image' : ''}`}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onClick={hasImage ? undefined : () => fileInputRef.current?.click()}
          role={hasImage ? undefined : 'button'}
          tabIndex={hasImage ? undefined : 0}
          onKeyDown={hasImage ? undefined : (e) => e.key === 'Enter' && fileInputRef.current?.click()}
        >
          {hasImage ? (
            <div className="preview-wrap">
              <img src={preview!} alt="Preview" className="preview-img" />
              <button
                className="change-btn"
                onClick={() => fileInputRef.current?.click()}
              >
                Change
              </button>
            </div>
          ) : (
            <div className="dropzone-hint">
              <UploadIcon />
              <strong>Drop image here or click to upload</strong>
              <span>PNG &amp; JPG supported · max 10 MB</span>
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/png,image/jpeg,image/jpg,image/webp"
            onChange={onInputChange}
            style={{ display: 'none' }}
          />
        </div>

        {/* ── Controls ── */}
        <div className="controls">
          <div className="control-row">
            <div className="control-label">
              <span>Colour layers</span>
              <strong>{nColors}</strong>
            </div>
            <input
              type="range" min={2} max={24} step={1} value={nColors}
              onChange={(e) => setNColors(Number(e.target.value))}
            />
          </div>

          <div className="control-row">
            <div className="control-label">
              <span>Detail level</span>
              <strong>{detail}%</strong>
            </div>
            <input
              type="range" min={0} max={100} step={1} value={detail}
              onChange={(e) => setDetail(Number(e.target.value))}
            />
          </div>
        </div>

        {/* ── Actions ── */}
        <div className="actions">
          <button
            className="btn-convert"
            onClick={convert}
            disabled={!file || state === 'converting'}
          >
            {state === 'converting' && <span className="spinner" />}
            {state === 'converting' ? 'Converting…' : 'Convert to PowerPoint'}
          </button>

          {downloadUrl && (
            <a
              className="btn-download"
              href={downloadUrl}
              download="vectorized.pptx"
            >
              <DownloadIcon />
              Download .pptx
            </a>
          )}
        </div>

        {/* ── Banners ── */}
        {state === 'error' && error && (
          <div className="banner error">{error}</div>
        )}

        {state === 'done' && (
          <div className="banner success">
            Done! Open in PowerPoint, right-click any shape →{' '}
            <code>Edit Points</code> to adjust vertices.
          </div>
        )}
      </main>
    </div>
  )
}

function UploadIcon() {
  return (
    <svg
      width="44" height="44" viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth="1.4"
      strokeLinecap="round" strokeLinejoin="round"
    >
      <polyline points="16 16 12 12 8 16" />
      <line x1="12" y1="12" x2="12" y2="21" />
      <path d="M20.39 18.39A5 5 0 0018 9h-1.26A8 8 0 103 16.3" />
    </svg>
  )
}

function DownloadIcon() {
  return (
    <svg
      width="16" height="16" viewBox="0 0 24 24"
      fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round"
    >
      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  )
}
