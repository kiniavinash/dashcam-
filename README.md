# dashcam experiments

A web application to view and play dashcam videos stored in Google Drive.

## Features

- 🔐 Secure Google Drive authentication
- 📹 List all dashcam videos from your Google Drive
- ▶️ Click-to-play video playback in browser
- 🎨 Clean, modern user interface
- 📱 Responsive design

## Quick Start

### Option 1: Deploy to Cloud (Recommended)

Deploy to Google Cloud Run for **FREE** and access from anywhere:

```bash
gcloud run deploy dashcam-viewer --source . --region us-central1
```

See [DEPLOY.md](DEPLOY.md) for complete deployment instructions.

### Option 2: Run Locally

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Google Drive API credentials** (see [SETUP.md](SETUP.md) for detailed instructions)

3. **Run the application:**
   ```bash
   python app.py
   ```

4. **Open in browser:**
   ```
   http://localhost:5000
   ```

## How It Works

- The app connects to your Google Drive using OAuth 2.0
- It lists all video files stored in your Drive
- Click on any video to play it directly in your browser
- Videos are streamed securely from Google Drive

## Documentation

- [Deployment Guide](DEPLOY.md) - Deploy to Google Cloud Run (FREE hosting)
- [Setup Instructions](SETUP.md) - Local development setup with Google Drive API

## Requirements

- Python 3.8+
- Google account with dashcam videos in Google Drive

## Security

- Never commit `credentials.json` to version control
- The app uses OAuth 2.0 for secure authentication
- Credentials are stored in session only
