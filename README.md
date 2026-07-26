# BigQuery Release Notes Dashboard

A beautiful, light/dark responsive web dashboard built with **Python Flask** and **Vanilla Javascript/CSS** that fetches, parses, and displays Google Cloud BigQuery release updates.

## Features
- **Live XML Feed Fetching:** Pulls updates directly from the official Google Cloud feeds.
- **Granular Splitting:** Splits multi-part daily entries into individual, clean update cards.
- **Categorization Badges:** Automatically classifies updates (Features, Changes, Issues, Announcements, Security).
- **Search & Filters:** Real-time client-side keyword search and category filtering.
- **X/Twitter Composer Integration:** Select any update to compose, format, and publish a tweet directly via X Web Intent.
- **macOS SSL Cert Workaround:** Pre-configured SSL context handler to resolve local verify failure errors.

## Project Structure
```
bq-releases-notes/
├── app.py              # Flask server backend
├── templates/
│   └── index.html      # Dashboard layout
├── static/
│   ├── app.js          # Main frontend logic (XML parsing, tweeting)
│   └── style.css       # Premium dark theme stylesheet
├── README.md           # Documentation
└── .gitignore          # Git exclusion rules
```

## Getting Started

### Prerequisites
- Python 3.x
- Flask (`pip install flask`)

### Running the Application

1. **Install dependencies:**
   ```bash
   pip install flask
   ```

2. **Start the Flask server:**
   ```bash
   python3 app.py
   ```

3. **Open the browser:**
   Go to [http://127.0.0.1:5001](http://127.0.0.1:5001)
