# Hotel Management System

A modern hotel management system built with Flask.

## Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/locle27/RenderStreamlit.git
cd RenderStreamlit
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup Google Cloud Credentials
1. Copy the template file:
   ```bash
   cp gcp_credentials.json.template gcp_credentials.json
   ```
2. Fill in your actual Google Cloud Service Account credentials in `gcp_credentials.json`
3. Make sure `gcp_credentials.json` is never committed to git (it's in .gitignore)

### 4. Environment Variables
Create a `.env` file with your configuration:
```bash
GCP_CREDS_FILE_PATH=gcp_credentials.json
DEFAULT_SHEET_ID=your_google_sheet_id
WORKSHEET_NAME=your_worksheet_name
GOOGLE_API_KEY=your_google_api_key
FLASK_SECRET_KEY=your_secret_key
```

### 5. Run the application
```bash
python app.py
```

## Features

- **Dashboard**: Overview of bookings, revenue, and statistics
- **Booking Management**: Add, edit, delete bookings
- **Calendar View**: Visual calendar with booking information
- **Image Processing**: Extract booking info from images using AI
- **Message Templates**: Manage customer communication templates

## Development Toolbar

The development toolbar provides AI-powered editing capabilities through a browser interface. It allows you to:

1. Select and highlight elements in your web app
2. Leave comments and feedback about specific UI elements
3. Export comments for AI processing
4. Track UI/UX improvements

### How to Enable the Toolbar

1. Set Flask to development mode:
```bash
export FLASK_ENV=development
```

2. Run the Flask app:
```bash
flask run
```

3. The development toolbar will appear in the top-right corner of your browser

### Using the Toolbar

1. Click on any element in your web app to select it
2. The toolbar will show information about the selected element:
   - HTML tag
   - ID (if any)
   - CSS classes
   - Text content

3. Add comments about the selected element:
   - Enter your feedback in the comment box
   - Click "Save Comment" to store it
   - Comments are saved in your browser's local storage

4. Export comments:
   - Click "Export Comments" to download a JSON file
   - The JSON file contains all comments with element details
   - This file can be used by AI agents to make changes

### Security

The toolbar is only active in development mode. It will not appear in production.

## Deployment

When deploying to production:
1. Set environment variables on your hosting platform
2. Upload your `gcp_credentials.json` file securely (not through git)
3. Set `DEV_MODE = False` in `app.py`