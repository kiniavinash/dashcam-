#!/usr/bin/env python3
"""
Download videos from Google Drive to /data.

Supports:
  - Single file by ID or shareable URL
  - Entire folder by ID or shareable URL

Usage:
  uv run python scripts/download_gdrive.py --url "https://drive.google.com/drive/folders/FOLDER_ID"
  uv run python scripts/download_gdrive.py --url "https://drive.google.com/file/d/FILE_ID/view"
  uv run python scripts/download_gdrive.py --id FILE_ID
  uv run python scripts/download_gdrive.py --id FOLDER_ID --folder

Requirements:
  gdown is installed in the inference container (see Dockerfile.inference).
  For large files / shared drives you may need to authenticate:
    uv run python scripts/download_gdrive.py --id ID --use-cookies
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def extract_id_from_url(url: str) -> tuple[str, bool]:
    """
    Parse a Google Drive URL and return (id, is_folder).
    Handles both /file/d/ID and /folders/ID formats.
    """
    folder_match = re.search(r"/folders/([a-zA-Z0-9_-]+)", url)
    if folder_match:
        return folder_match.group(1), True

    file_match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if file_match:
        return file_match.group(1), False

    # Might be a direct ID with no path hints
    return url.strip(), False


def download(
    drive_id: str,
    is_folder: bool,
    output_dir: Path,
    use_cookies: bool = False,
    quiet: bool = False,
):
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["gdown", drive_id, "--output", str(output_dir) + "/"]

    if is_folder:
        cmd += ["--folder", "--remaining-ok"]

    if use_cookies:
        cmd += ["--use-cookies"]

    if quiet:
        cmd += ["--quiet"]

    print(f"Downloading {'folder' if is_folder else 'file'} {drive_id} → {output_dir}")
    print(f"Running: {' '.join(cmd)}")

    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(
            "\nDownload failed. Common causes:",
            "  1. File/folder is not publicly shared — check Drive permissions",
            "  2. Large files may require --use-cookies flag with your browser cookies",
            "  3. Folder downloads require gdown >= 4.6.0",
            sep="\n",
            file=sys.stderr,
        )
        sys.exit(result.returncode)

    print(f"Done. Files saved to {output_dir}")


def parse_args():
    p = argparse.ArgumentParser(description="Download files from Google Drive")

    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", type=str, help="Google Drive shareable URL (file or folder)")
    src.add_argument("--id", type=str, help="Google Drive file or folder ID")

    p.add_argument("--folder", action="store_true",
                   help="Treat --id as a folder ID (auto-detected from --url)")
    p.add_argument("--output", type=Path, default=Path("/data"),
                   help="Local destination directory (default: /data)")
    p.add_argument("--use-cookies", action="store_true",
                   help="Use browser cookies for authenticated downloads (for large/restricted files)")
    p.add_argument("--quiet", action="store_true", help="Suppress progress output")
    return p.parse_args()


def main():
    args = parse_args()

    if args.url:
        drive_id, is_folder = extract_id_from_url(args.url)
    else:
        drive_id = args.id
        is_folder = args.folder

    download(drive_id, is_folder, args.output, args.use_cookies, args.quiet)


if __name__ == "__main__":
    main()
