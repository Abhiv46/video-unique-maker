# Video Unique Maker (वीडियो यूनिक मेकर)

A small Flask web app that processes an uploaded video to produce a "unique" variant of it, using MoviePy / OpenCV / Pillow for the video work.

## Tech stack

- **Flask 2.3** + flask-cors (web app in `app.py`)
- **MoviePy**, **OpenCV**, **NumPy**, **Pillow** (video/image processing)
- **gunicorn** for serving; `Procfile` and `runtime.txt` included for PaaS deployment, plus a `vercel.json`
- FFmpeg is required (`IMAGEIO_FFMPEG_EXE` is set to `/usr/bin/ffmpeg` in `app.py`)

## Running locally

```bash
pip install -r requirements.txt
python app.py
```

Then open the page served by Flask (UI template: `templates/index.html`, Hindi UI).

## Notes

- Uploaded/processed files are handled with per-request unique IDs (`uuid`) in `app.py`.
