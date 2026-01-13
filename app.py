import os
import io
import json
from flask import Flask, render_template, redirect, url_for, session, request, send_file
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

app = Flask(__name__)

# Use environment variable for secret key in production, random for local dev
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Google Drive API scopes
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# OAuth 2.0 configuration
# In production (Cloud Run), credentials come from environment variable
# In local dev, use credentials.json file
GOOGLE_CREDENTIALS = os.environ.get('GOOGLE_CREDENTIALS')
CLIENT_SECRETS_FILE = "credentials.json"

def get_drive_service():
    """Create and return Google Drive service instance."""
    if 'credentials' not in session:
        return None

    credentials = Credentials(**session['credentials'])
    return build('drive', 'v3', credentials=credentials)

@app.route('/')
def index():
    """Main page - show list of videos."""
    if 'credentials' not in session:
        return redirect(url_for('authorize'))

    service = get_drive_service()

    # Search for video files in Google Drive
    # Adjust the query to match your specific folder or file patterns
    query = "mimeType contains 'video/' and trashed=false"

    try:
        results = service.files().list(
            q=query,
            pageSize=100,
            fields="files(id, name, mimeType, size, createdTime, webViewLink)"
        ).execute()

        videos = results.get('files', [])

        # Sort by creation time (newest first)
        videos.sort(key=lambda x: x.get('createdTime', ''), reverse=True)

        return render_template('index.html', videos=videos)
    except Exception as e:
        return f"Error accessing Google Drive: {str(e)}"

@app.route('/authorize')
def authorize():
    """Start OAuth 2.0 authorization flow."""
    # Use credentials from environment variable if available (production)
    # Otherwise use credentials.json file (local development)
    if GOOGLE_CREDENTIALS:
        client_config = json.loads(GOOGLE_CREDENTIALS)
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=url_for('oauth2callback', _external=True)
        )
    else:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=url_for('oauth2callback', _external=True)
        )

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )

    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    """Handle OAuth 2.0 callback."""
    state = session['state']

    # Use credentials from environment variable if available (production)
    # Otherwise use credentials.json file (local development)
    if GOOGLE_CREDENTIALS:
        client_config = json.loads(GOOGLE_CREDENTIALS)
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            state=state,
            redirect_uri=url_for('oauth2callback', _external=True)
        )
    else:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            state=state,
            redirect_uri=url_for('oauth2callback', _external=True)
        )

    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

    return redirect(url_for('index'))

@app.route('/video/<file_id>')
def stream_video(file_id):
    """Stream video from Google Drive."""
    service = get_drive_service()

    try:
        # Get file metadata
        file_metadata = service.files().get(fileId=file_id, fields='mimeType').execute()
        mime_type = file_metadata.get('mimeType', 'video/mp4')

        # Download the file
        request_file = service.files().get_media(fileId=file_id)
        file_buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(file_buffer, request_file)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        file_buffer.seek(0)
        return send_file(file_buffer, mimetype=mime_type)

    except Exception as e:
        return f"Error streaming video: {str(e)}", 500

@app.route('/logout')
def logout():
    """Clear credentials and logout."""
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Disable HTTPS requirement for local development only
    if not GOOGLE_CREDENTIALS:
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    # Use PORT environment variable for Cloud Run, default to 5000 for local
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=not GOOGLE_CREDENTIALS)
