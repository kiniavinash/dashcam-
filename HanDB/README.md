# HanDB — Personal Dashcam Dataset

HanDB is a collection of dashcam video clips recorded from a personal vehicle. It serves as the primary test dataset for the dashcam inference pipeline in this repository.

## Contents

```
HanDB/
├── README.md          # This file
├── clips/             # Raw dashcam video files (.mp4)
└── egomotion/         # Optional GPS/IMU data per clip (.csv)
```

Videos are stored in Google Drive and can be browsed via the [dashcam web app](../README.md) or downloaded locally for inference.

## Recording Setup

| Field | Value |
|---|---|
| Camera | Consumer dashcam (front-facing) |
| Resolution | 1080p or 720p |
| Frame rate | 30 fps (native) |
| GPS/IMU | Not available (single-camera only) |
| Location | Mixed urban / suburban driving |

> **Note on egomotion:** Alpamayo-R1 was trained with GPS/IMU egomotion data at 10 Hz.
> HanDB clips do **not** include egomotion, so inference runs with zero-motion assumed.
> Trajectory predictions will be less accurate than on datasets with GPS/IMU.
> If a GPS-equipped dashcam is used in future recordings, pass `--egomotion <clip>.csv` to the inference script.

## Download

Videos are stored in Google Drive. Use the download script to pull clips locally:

```bash
# Download a single clip by URL
uv run python scripts/download_gdrive.py \
  --url "https://drive.google.com/file/d/FILE_ID/view" \
  --output data/

# Download all clips from the HanDB folder
uv run python scripts/download_gdrive.py \
  --url "https://drive.google.com/drive/folders/FOLDER_ID" \
  --output data/
```

Or use the **Download for Inference** button in the web app to fetch a clip directly.

## Running Inference

Once a clip is in `data/`, run Alpamayo-R1 inference:

```bash
# Single clip — no egomotion
uv run python scripts/run_inference.py \
  --mode video \
  --input data/clip.mp4 \
  --output results/

# Single clip — with egomotion CSV (if available)
uv run python scripts/run_inference.py \
  --mode video \
  --input data/clip.mp4 \
  --egomotion data/clip_gps.csv \
  --output results/
```

Results are written to `results/<clip_stem>_inference.json` with per-window reasoning traces and trajectory predictions.

### Inference options

| Flag | Default | Description |
|---|---|---|
| `--window` | `2.0` | Sliding window length in seconds |
| `--stride` | `1.0` | Stride between windows in seconds |
| `--temperature` | `0.6` | Sampling temperature |
| `--top-p` | `0.98` | Top-p sampling |
| `--max-new-tokens` | `2048` | Max tokens per window |

## Egomotion CSV Format

If your dashcam records GPS/IMU data, export it as a CSV with these columns:

```
timestamp_us, x, y, z, qw, qx, qy, qz
```

- `timestamp_us`: microseconds since epoch (must align with video timestamps)
- `x, y, z`: position in metres (local ENU frame)
- `qw, qx, qy, qz`: orientation as unit quaternion

## Known Limitations

- **No egomotion** — trajectory predictions are less accurate without GPS/IMU
- **Single camera** — Alpamayo was trained on multi-camera rigs; single-camera input reduces spatial coverage
- **Variable lighting** — clips include night driving and direct sunlight; model performance may vary

## Related

- [Inference pipeline — scripts/](../scripts/)
- [Docker inference container — Dockerfile.inference](../Dockerfile.inference)
- [Alpamayo-R1 paper](https://github.com/NVlabs/alpamayo)
