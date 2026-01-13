# Google Cloud Run Deployment Guide

This guide will walk you through deploying your dashcam video viewer to Google Cloud Run for **FREE**.

## Free Tier Limits

Google Cloud Run free tier includes:
- 2 million requests per month
- 360,000 GB-seconds of memory
- 180,000 vCPU-seconds
- **This is MORE than enough for personal use!**

## Prerequisites

- Google Cloud account ([create one here](https://cloud.google.com/))
- Docker installed locally (optional, for testing)
- `gcloud` CLI installed ([install here](https://cloud.google.com/sdk/docs/install))

## Step 1: Set Up Google Cloud Project

### 1.1 Create a new project or select existing one

```bash
# Login to Google Cloud
gcloud auth login

# Create a new project (or skip if using existing)
gcloud projects create dashcam-viewer-PROJECT_ID --name="Dashcam Viewer"

# Set the project
gcloud config set project dashcam-viewer-PROJECT_ID
```

Replace `PROJECT_ID` with a unique identifier (e.g., your name + random numbers).

### 1.2 Enable required APIs

```bash
# Enable Cloud Run API
gcloud services enable run.googleapis.com

# Enable Container Registry API
gcloud services enable containerregistry.googleapis.com

# Enable Cloud Build API (for building Docker images)
gcloud services enable cloudbuild.googleapis.com
```

## Step 2: Set Up Google Drive OAuth Credentials

### 2.1 Go to Google Cloud Console

1. Navigate to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project

### 2.2 Enable Google Drive API

1. Go to "APIs & Services" → "Library"
2. Search for "Google Drive API"
3. Click "Enable"

### 2.3 Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Select "External" user type (unless you have Google Workspace)
3. Fill in required fields:
   - **App name**: Dashcam Viewer
   - **User support email**: Your email
   - **Developer contact**: Your email
4. Click "Save and Continue"
5. Skip "Scopes" → Click "Save and Continue"
6. Add test users: Add your Gmail address
7. Click "Save and Continue"

### 2.4 Create OAuth Client ID

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Application type: **Web application**
4. Name: **Dashcam Cloud Client**
5. **Authorized redirect URIs**:
   - We'll add this AFTER deployment, so note this for later
   - Format will be: `https://YOUR-APP-URL/oauth2callback`
6. Click "Create"
7. **IMPORTANT**: Download the JSON file (click the download icon)

### 2.5 Save credentials content

Open the downloaded JSON file. You'll need its content in the next step.

## Step 3: Deploy to Cloud Run

### 3.1 Set environment variables

First, we need to set up the credentials as an environment variable.

Open your `credentials.json` file and copy its entire content. Then run:

```bash
# Generate a random secret key
SECRET_KEY=$(python3 -c 'import os; print(os.urandom(24).hex())')

# Set the Google credentials (replace with your actual credentials.json content)
# This should be the entire JSON content as a single line
GOOGLE_CREDS='{"web":{"client_id":"YOUR_CLIENT_ID",...}}'
```

### 3.2 Deploy the application

```bash
# Deploy to Cloud Run
gcloud run deploy dashcam-viewer \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars SECRET_KEY="$SECRET_KEY" \
  --set-env-vars GOOGLE_CREDENTIALS="$GOOGLE_CREDS" \
  --max-instances 1 \
  --memory 512Mi \
  --timeout 300
```

**What this does:**
- Builds a Docker container from your code
- Deploys it to Cloud Run in us-central1 region
- Makes it publicly accessible
- Sets environment variables for credentials
- Limits to 1 instance to stay in free tier
- Uses 512MB memory (enough for video streaming)
- 5 minute timeout for large video downloads

### 3.3 Note your application URL

After deployment completes, you'll see output like:

```
Service [dashcam-viewer] revision [dashcam-viewer-00001-abc] has been deployed and is serving 100 percent of traffic.
Service URL: https://dashcam-viewer-XXXX-uc.a.run.app
```

**Copy this Service URL!** You'll need it in the next step.

## Step 4: Update OAuth Redirect URI

1. Go back to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to "APIs & Services" → "Credentials"
3. Click on your OAuth 2.0 Client ID
4. Under "Authorized redirect URIs", click "Add URI"
5. Add: `https://YOUR-SERVICE-URL/oauth2callback`
   - Replace `YOUR-SERVICE-URL` with the actual URL from Step 3.3
   - Example: `https://dashcam-viewer-abc123-uc.a.run.app/oauth2callback`
6. Click "Save"

## Step 5: Access Your Application

1. Open your Service URL in a browser: `https://dashcam-viewer-XXXX-uc.a.run.app`
2. You'll be redirected to Google for authorization
3. Sign in and grant permissions
4. You should now see your dashcam videos!

## Cost Optimization Tips

To stay within the free tier:

1. **Set max instances to 1**:
   ```bash
   gcloud run services update dashcam-viewer \
     --max-instances 1 \
     --region us-central1
   ```

2. **Set minimum instances to 0** (default):
   - The app will "sleep" when not in use
   - First request after sleep takes 2-3 seconds (cold start)
   - This is normal and saves you money!

3. **Monitor usage**:
   ```bash
   gcloud run services describe dashcam-viewer --region us-central1
   ```

## Updating Your Application

When you make code changes:

```bash
# Simply redeploy
gcloud run deploy dashcam-viewer \
  --source . \
  --region us-central1
```

Cloud Run will automatically:
- Rebuild the Docker image
- Deploy the new version
- Keep your environment variables

## Troubleshooting

### "Access blocked: This app's request is invalid"

- Make sure you added the correct redirect URI in Google Cloud Console
- Format: `https://YOUR-EXACT-URL/oauth2callback`

### "Error accessing Google Drive"

- Verify the `GOOGLE_CREDENTIALS` environment variable is set correctly
- Check that Google Drive API is enabled
- Make sure you're signed in with the test user you added

### Videos not loading

- Check Cloud Run logs: `gcloud run services logs read dashcam-viewer --region us-central1`
- Increase memory if needed: `--memory 1Gi`
- Increase timeout: `--timeout 600`

### "Quota exceeded" errors

- Check your Cloud Run quotas in the Google Cloud Console
- You might have exceeded the free tier limits
- Consider upgrading to paid tier (still very cheap!)

## Viewing Logs

```bash
# Real-time logs
gcloud run services logs tail dashcam-viewer --region us-central1

# Recent logs
gcloud run services logs read dashcam-viewer --region us-central1 --limit 50
```

## Deleting the Deployment

If you want to remove the application:

```bash
gcloud run services delete dashcam-viewer --region us-central1
```

## Security Notes

- OAuth credentials are stored as environment variables (secure)
- User sessions are encrypted with SECRET_KEY
- App runs on HTTPS automatically (Cloud Run provides SSL)
- No credentials are committed to git (thanks to .gitignore)

---

## Quick Reference Commands

```bash
# View service details
gcloud run services describe dashcam-viewer --region us-central1

# View logs
gcloud run services logs tail dashcam-viewer --region us-central1

# Update environment variable
gcloud run services update dashcam-viewer \
  --update-env-vars NEW_VAR=value \
  --region us-central1

# Redeploy from source
gcloud run deploy dashcam-viewer --source . --region us-central1
```

---

Enjoy your dashcam video viewer! 🎥
