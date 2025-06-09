# Project Structure Overview

## Current File Organization

```
hotel_flask_app/
├── app.py                          # Main Flask application - DO NOT MODIFY
├── logic.py                        # Business logic - DO NOT MODIFY  
├── requirements.txt                # Dependencies - DO NOT MODIFY
├── .env                           # Environment variables - DO NOT MODIFY
├── gcp_credentials.json           # Google Cloud credentials - DO NOT MODIFY
├── message_templates.json         # Template data - DO NOT MODIFY
│
├── templates/                     # HTML Templates - MODIFY THESE
│   ├── base.html                 # Base template (if exists)
│   ├── dashboard.html            # Main dashboard page
│   ├── bookings.html             # Bookings management page
│   ├── calendar.html             # Calendar view page
│   ├── calendar_details.html     # Calendar day details
│   ├── templates.html            # Message templates page
│   ├── add_from_image.html       # Image processing page
│   └── edit_booking.html         # Booking edit form
│
├── static/                       # Static assets - MODIFY/ADD TO THESE
│   ├── css/                      # CSS files
│   │   └── (currently empty - ADD NEW CSS FILES HERE)
│   ├── js/                       # JavaScript files  
│   │   └── (currently empty - ADD NEW JS FILES HERE)
│   └── images/                   # Images and icons
│       └── (currently empty)
│
└── Documentation/                # Project documentation
    ├── UI_OPTIMIZATION_PROJECT_PLAN.md
    ├── CLAUDE_CODE_INSTRUCTIONS.md
    ├── TEMPLATE_FIX_INSTRUCTIONS.md
    └── README.md
```

## Key Files to Focus On

### 🎯 PRIMARY TARGETS (Modify these extensively)

#### HTML Templates (`templates/`)
1. **`dashboard.html`** - Main dashboard with charts and metrics
2. **`bookings.html`** - Booking list and management interface  
3. **`calendar.html`** - Monthly calendar view
4. **`templates.html`** - Message template management
5. **`add_from_image.html`** - Image upload and processing
6. **`edit_booking.html`** - Booking edit form
7. **`calendar_details.html`** - Calendar day details modal

#### CSS Files (`static/css/`) - CREATE THESE
1. **`main.css`** - Main stylesheet with design system
2. **`components.css`** - Reusable UI components
3. **`dashboard.css`** - Dashboard-specific styles
4. **`responsive.css`** - Mobile optimization
5. **`utilities.css`** - Utility classes

#### JavaScript Files (`static/js/`) - ENHANCE THESE
1. **`main.js`** - Global functionality and interactions
2. **`dashboard.js`** - Dashboard-specific enhancements
3. **`components.js`** - Reusable UI components

### 🚫 DO NOT MODIFY

#### Backend Files
- `app.py` - Flask routes and logic
- `logic.py` - Business logic functions
- `requirements.txt` - Python dependencies
- `.env` - Environment configuration
- `gcp_credentials.json` - Google Cloud authentication
- `message_templates.json` - Template data

## Current Technology Stack

### Frontend (What you'll be working with)
- **HTML5** with Jinja2 templating
- **Bootstrap 5.1.3** (currently used, but can be replaced/enhanced)
- **Font Awesome 6.0.0** for icons
- **Plotly.js** for charts and graphs
- **Vanilla JavaScript** for interactions

### Backend (Don't touch)
- **Flask** (Python web framework)
- **Google Sheets API** for data storage
- **Google Gemini AI** for image processing
- **Pandas** for data manipulation

## Current Pages and Their Functions

### 1. Dashboard (`/`)
- **Purpose**: Main overview with revenue analytics and guest statistics
- **Key Elements**: Metric cards, charts (Plotly), data tables
- **Current Issues**: Basic Bootstrap styling, poor mobile experience

### 2. Bookings (`/bookings`)  
- **Purpose**: Manage all hotel bookings
- **Key Elements**: Data table, search, edit/delete actions, bulk operations
- **Current Issues**: Dense table layout, poor mobile responsiveness

### 3. Calendar (`/calendar`)
- **Purpose**: Visual calendar view of bookings
- **Key Elements**: Month grid, day details, navigation
- **Current Issues**: Basic calendar styling, limited mobile optimization

### 4. Message Templates (`/templates`)
- **Purpose**: Manage predefined message templates
- **Key Elements**: Template list, categories, copy functionality
- **Current Issues**: Basic list layout, poor visual hierarchy

### 5. Add from Image (`/bookings/add_from_image`)
- **Purpose**: Extract booking info from images using AI
- **Key Elements**: Image upload, processing results, save functionality
- **Current Issues**: Basic form styling, poor feedback design

## Design Goals Summary

### Visual Transformation
- Replace Bootstrap's default look with modern, custom design
- Implement professional hotel industry aesthetics
- Create consistent visual language across all pages
- Improve information density without clutter

### User Experience Enhancement  
- Perfect mobile and tablet responsiveness
- Intuitive navigation and workflows
- Clear visual hierarchy and content organization
- Smooth animations and micro-interactions

### Technical Improvements
- Modern CSS (Grid, Flexbox, Custom Properties)
- Component-based architecture
- Performance optimization
- Accessibility compliance

## Getting Started Checklist

### Step 1: Analyze Current Templates
- [ ] Review each HTML template to understand structure
- [ ] Identify common elements that can be componentized
- [ ] Note current Bootstrap classes being used

### Step 2: Create Design System
- [ ] Establish color palette and typography
- [ ] Create base CSS with custom properties
- [ ] Define spacing and layout systems

### Step 3: Modernize Templates
- [ ] Start with dashboard as main showcase
- [ ] Implement component library
- [ ] Enhance responsive behavior

### Step 4: Polish and Optimize
- [ ] Add animations and micro-interactions
- [ ] Optimize for performance
- [ ] Test across devices and browsers

This structure should give you everything you need to transform the hotel management system into a beautiful, modern application while maintaining all existing functionality.
