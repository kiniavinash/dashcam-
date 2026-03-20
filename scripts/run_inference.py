#!/usr/bin/env python3
"""
Alpamayo-R1 inference entry point.

Two modes:
  --mode demo   Run alpamayo's built-in test on the Physical AI AV Dataset.
                Requires HF_TOKEN and HuggingFace dataset access.

  --mode video  Run inference on a local dashcam video file.
                Extracts frames at 10 Hz and feeds them to the model.
                NOTE: Alpamayo was trained with multi-camera + egomotion input.
                      Single-camera video without egomotion will work but trajectory
                      accuracy will be lower. Pass --egomotion <csv> if your dashcam
                      records GPS/IMU data (see docs for format).

Usage:
  uv run python scripts/run_inference.py --mode demo
  uv run python scripts/run_inference.py --mode video --input /data/clip.mp4
  uv run python scripts/run_inference.py --mode video --input /data/clip.mp4 --egomotion /data/clip_gps.csv
"""

import argparse
import json
import sys
import time
from pathlib import Path

import torch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_model(model_name: str = "nvidia/Alpamayo-R1-10B"):
    """Load model and processor. Weights are cached in HF_HOME."""
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from alpamayo_r1.helper import get_processor

    print(f"Loading model: {model_name}")
    print("(First run downloads ~20GB of weights — subsequent runs use cache)")

    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()
    processor = get_processor(tokenizer)

    print(f"Model loaded on: {next(model.parameters()).device}")
    return model, tokenizer, processor


def run_inference_on_frames(
    frames: torch.Tensor,
    model,
    tokenizer,
    processor,
    egomotion=None,
    sampling_params: dict | None = None,
) -> dict:
    """
    Run Alpamayo inference on a batch of frames.

    Args:
        frames:    (N, 3, H, W) float tensor, values in [0, 1]
        egomotion: Optional (N, 7) tensor [x, y, z, qw, qx, qy, qz] at each frame.
                   If None, zero motion is assumed (accuracy will be reduced).
        sampling_params: Override default generation params.

    Returns:
        dict with keys: "reasoning_trace", "trajectory", "raw_output"
    """
    from alpamayo_r1.helper import create_message, to_device

    if sampling_params is None:
        sampling_params = {"top_p": 0.98, "temperature": 0.6, "max_new_tokens": 2048}

    if egomotion is None:
        print("  WARNING: No egomotion provided. Using zero motion — trajectory accuracy will be reduced.")
        egomotion = torch.zeros(frames.shape[0], 7)
        egomotion[:, 3] = 1.0  # unit quaternion (w=1)

    device = next(model.parameters()).device

    messages = create_message(frames)
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(images=frames, text=text, return_tensors="pt")
    inputs = to_device(inputs, device, torch.bfloat16)

    with torch.inference_mode():
        output_ids = model.generate(**inputs, **sampling_params)

    raw = tokenizer.decode(output_ids[0], skip_special_tokens=True)

    # Parse reasoning trace and trajectory from model output
    # Alpamayo outputs a structured response with <cot>...</cot> and trajectory tokens
    result = {"raw_output": raw, "reasoning_trace": "", "trajectory": []}

    if "<cot>" in raw and "</cot>" in raw:
        start = raw.index("<cot>") + len("<cot>")
        end = raw.index("</cot>")
        result["reasoning_trace"] = raw[start:end].strip()

    return result


# ---------------------------------------------------------------------------
# Demo mode: uses alpamayo's own test clip from the Physical AI AV Dataset
# ---------------------------------------------------------------------------

def run_demo(output_dir: Path, sampling_params: dict):
    """Run alpamayo's built-in test_inference.py logic."""
    from alpamayo_r1.load_physical_aiavdataset import load_physical_aiavdataset
    from alpamayo_r1.test_inference import main as alpamayo_test_main

    print("Running demo mode with Physical AI AV Dataset test clip...")
    print("This requires HF_TOKEN and access to the gated dataset.")

    # Delegate to alpamayo's own test — it prints minADE and reasoning trace
    alpamayo_test_main()

    print(f"\nDemo complete. (Results printed above — saved to {output_dir}/demo_output.txt if redirected)")


# ---------------------------------------------------------------------------
# Video mode: run inference on a local dashcam video
# ---------------------------------------------------------------------------

def run_video(
    video_path: Path,
    output_dir: Path,
    egomotion_path: Path | None,
    sampling_params: dict,
    window_seconds: float = 2.0,
    stride_seconds: float = 1.0,
):
    """
    Run inference on a local video file.

    Splits the video into overlapping windows of `window_seconds` length,
    sliding by `stride_seconds`, and runs inference on each window.
    """
    from extract_frames import extract_frames_at_fps

    print(f"Input video: {video_path}")

    fps_target = 10.0  # alpamayo was trained at 10 Hz
    frames_all = extract_frames_at_fps(video_path, fps_target)
    print(f"Extracted {len(frames_all)} frames at {fps_target} Hz")

    egomotion_all = None
    if egomotion_path is not None:
        egomotion_all = load_egomotion_csv(egomotion_path)
        print(f"Loaded egomotion: {egomotion_all.shape}")

    model, tokenizer, processor = load_model()

    window_frames = int(window_seconds * fps_target)
    stride_frames = int(stride_seconds * fps_target)

    results = []
    total_windows = max(1, (len(frames_all) - window_frames) // stride_frames + 1)
    print(f"Running inference on {total_windows} windows ({window_seconds}s each, {stride_seconds}s stride)...")

    for i, start in enumerate(range(0, len(frames_all) - window_frames + 1, stride_frames)):
        end = start + window_frames
        window = frames_all[start:end]  # (W, 3, H, H)

        ego_window = None
        if egomotion_all is not None:
            ego_window = egomotion_all[start:end]

        t_start = start / fps_target
        t_end = end / fps_target
        print(f"  Window {i+1}/{total_windows}: t={t_start:.1f}s–{t_end:.1f}s", end=" ", flush=True)

        t0 = time.time()
        result = run_inference_on_frames(window, model, tokenizer, processor, ego_window, sampling_params)
        elapsed = time.time() - t0

        result["window_start_sec"] = t_start
        result["window_end_sec"] = t_end
        print(f"[{elapsed:.1f}s]")

        if result["reasoning_trace"]:
            print(f"    Reasoning: {result['reasoning_trace'][:120]}...")

        results.append(result)

    # Save results
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"{video_path.stem}_inference.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nDone. Results saved to {out_file}")
    return results


def load_egomotion_csv(path: Path) -> torch.Tensor:
    """
    Load egomotion from a CSV file.

    Expected columns: timestamp_us, x, y, z, qw, qx, qy, qz
    Returns: (N, 7) tensor [x, y, z, qw, qx, qy, qz]
    """
    import pandas as pd

    df = pd.read_csv(path)
    required = ["x", "y", "z", "qw", "qx", "qy", "qz"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Egomotion CSV missing columns: {missing}. Expected: timestamp_us, x, y, z, qw, qx, qy, qz")

    return torch.tensor(df[required].values, dtype=torch.float32)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Alpamayo-R1 dashcam inference")
    p.add_argument("--mode", choices=["demo", "video"], required=True,
                   help="demo: use alpamayo test clip | video: use local video file")
    p.add_argument("--input", type=Path, default=None,
                   help="Path to input video file (required for --mode video)")
    p.add_argument("--egomotion", type=Path, default=None,
                   help="Optional CSV with GPS/IMU egomotion (x, y, z, qw, qx, qy, qz)")
    p.add_argument("--output", type=Path, default=Path("/results"),
                   help="Directory to write results (default: /results)")
    p.add_argument("--window", type=float, default=2.0,
                   help="Inference window length in seconds (default: 2.0)")
    p.add_argument("--stride", type=float, default=1.0,
                   help="Stride between windows in seconds (default: 1.0)")
    p.add_argument("--top-p", type=float, default=0.98)
    p.add_argument("--temperature", type=float, default=0.6)
    p.add_argument("--max-new-tokens", type=int, default=2048)
    return p.parse_args()


def main():
    args = parse_args()

    sampling_params = {
        "top_p": args.top_p,
        "temperature": args.temperature,
        "max_new_tokens": args.max_new_tokens,
    }

    if args.mode == "demo":
        run_demo(args.output, sampling_params)

    elif args.mode == "video":
        if args.input is None:
            print("ERROR: --input is required for --mode video", file=sys.stderr)
            sys.exit(1)
        if not args.input.exists():
            print(f"ERROR: Input file not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        run_video(
            args.input,
            args.output,
            args.egomotion,
            sampling_params,
            args.window,
            args.stride,
        )


if __name__ == "__main__":
    main()
