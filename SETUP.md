# Setup Instructions

## Prerequisites

- Python 3.8 or higher
- Google account with dashcam videos in Google Drive

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Set Up Google Drive API Credentials

### 2.1 Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name (e.g., "Dashcam Viewer") and click "Create"

### 2.2 Enable Google Drive API

1. In your project, go to "APIs & Services" → "Library"
2. Search for "Google Drive API"
3. Click on it and press "Enable"

### 2.3 Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - User Type: Select "External" (unless you have a Google Workspace)
   - Click "Create"
   - Fill in:
     - App name: "Dashcam Viewer" (or any name)
     - User support email: Your email
     - Developer contact: Your email
   - Click "Save and Continue"
   - Scopes: Click "Save and Continue" (we'll set this in code)
   - Test users: Add your email address
   - Click "Save and Continue"

4. Back to "Credentials" → "Create Credentials" → "OAuth client ID"
   - Application type: "Web application"
   - Name: "Dashcam Web Client"
   - Authorized redirect URIs: Add `http://localhost:5000/oauth2callback`
   - Click "Create"

5. Download the credentials:
   - Click the download icon (⬇) next to your newly created OAuth 2.0 Client ID
   - Save the file as `credentials.json` in the project root directory

## Step 3: Run the Application

```bash
python app.py
```

## Step 4: Access the Web Interface

1. Open your browser and go to: `http://localhost:5000`
2. You'll be redirected to Google for authorization
3. Sign in with your Google account
4. Grant permissions to access your Google Drive
5. You'll be redirected back to the app with your video list

## Usage

- **View Videos**: All videos from your Google Drive will be displayed as cards
- **Play Video**: Click on any video card to play it in the browser
- **Close Video**: Click the X button, press Escape, or click outside the video player
- **Logout**: Click the "Logout" button in the header

## Troubleshooting

### "credentials.json not found"
Make sure you downloaded the OAuth credentials and saved them as `credentials.json` in the project root.

### "Access blocked: This app's request is invalid"
Make sure you added `http://localhost:5000/oauth2callback` to the authorized redirect URIs in Google Cloud Console.

### No videos showing up
The app searches for all video files in your Google Drive. Make sure:
- Your dashcam videos are uploaded to Google Drive
- The files have video MIME types (mp4, avi, mov, etc.)

### Videos won't play
Some video formats may not be supported by all browsers. MP4 (H.264) has the best compatibility.

## Security Notes

- The `credentials.json` file contains sensitive information. **Never commit it to version control.**
- A `.gitignore` file has been created to prevent accidental commits
- The app runs in local development mode. For production use, proper security measures should be implemented.
