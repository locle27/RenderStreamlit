# Hotel Management System

A modern hotel management system built with Flask.

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