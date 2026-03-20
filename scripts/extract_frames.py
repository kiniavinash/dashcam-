#!/usr/bin/env python3
"""
Extract frames from a video file at a target FPS using PyAV.

PyAV is already a dependency of alpamayo so no extra install needed.

Usage (standalone):
  uv run python scripts/extract_frames.py --input /data/clip.mp4 --fps 10 --output /data/frames/

Usage (as a module):
  from extract_frames import extract_frames_at_fps
  frames = extract_frames_at_fps(Path("clip.mp4"), fps=10.0)
  # returns (N, 3, H, W) float32 tensor, values in [0, 1]
"""

import argparse
from pathlib import Path

import av
import numpy as np
import torch
from PIL import Image


def extract_frames_at_fps(
    video_path: Path,
    fps: float = 10.0,
    max_frames: int | None = None,
) -> torch.Tensor:
    """
    Decode a video and sample frames at the target FPS.

    Returns a (N, 3, H, W) float32 tensor with values in [0, 1].
    Frames are resized to 224x224 to match Alpamayo's expected input resolution.
    """
    target_h, target_w = 224, 224

    container = av.open(str(video_path))
    stream = container.streams.video[0]

    # Native video FPS
    native_fps = float(stream.average_rate)
    if native_fps <= 0:
        native_fps = 30.0  # fallback

    # Sample every Nth frame to hit the target FPS
    every_n = max(1, round(native_fps / fps))

    frames = []
    for i, frame in enumerate(container.decode(stream)):
        if i % every_n != 0:
            continue

        img = frame.to_image()  # PIL Image (RGB)
        img = img.resize((target_w, target_h), Image.BILINEAR)
        arr = np.array(img, dtype=np.float32) / 255.0  # H, W, 3
        tensor = torch.from_numpy(arr).permute(2, 0, 1)  # 3, H, W
        frames.append(tensor)

        if max_frames is not None and len(frames) >= max_frames:
            break

    container.close()

    if not frames:
        raise RuntimeError(f"No frames extracted from {video_path}")

    return torch.stack(frames)  # N, 3, H, W


def save_frames_to_disk(frames: torch.Tensor, output_dir: Path):
    """Save extracted frames as PNG files (useful for debugging)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for i, frame in enumerate(frames):
        arr = (frame.permute(1, 2, 0).numpy() * 255).astype(np.uint8)
        Image.fromarray(arr).save(output_dir / f"frame_{i:05d}.png")
    print(f"Saved {len(frames)} frames to {output_dir}")


def get_video_info(video_path: Path) -> dict:
    container = av.open(str(video_path))
    stream = container.streams.video[0]
    info = {
        "path": str(video_path),
        "duration_sec": float(stream.duration * stream.time_base) if stream.duration else None,
        "native_fps": float(stream.average_rate),
        "width": stream.width,
        "height": stream.height,
        "codec": stream.codec_context.name,
    }
    container.close()
    return info


def parse_args():
    p = argparse.ArgumentParser(description="Extract frames from video at target FPS")
    p.add_argument("--input", type=Path, required=True, help="Input video file")
    p.add_argument("--fps", type=float, default=10.0, help="Target FPS (default: 10.0)")
    p.add_argument("--output", type=Path, default=None, help="Save frames as PNGs to this directory")
    p.add_argument("--max-frames", type=int, default=None, help="Limit number of frames extracted")
    p.add_argument("--info", action="store_true", help="Print video metadata and exit")
    return p.parse_args()


def main():
    args = parse_args()

    if args.info:
        info = get_video_info(args.input)
        for k, v in info.items():
            print(f"  {k}: {v}")
        return

    print(f"Extracting frames from {args.input} at {args.fps} Hz...")
    frames = extract_frames_at_fps(args.input, args.fps, args.max_frames)
    print(f"Extracted {len(frames)} frames — tensor shape: {frames.shape}")

    if args.output:
        save_frames_to_disk(frames, args.output)


if __name__ == "__main__":
    main()
