import os
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# Atom feed namespace
ATOM_NS = {'atom': 'http://www.w3.org/2005/Atom'}

def fetch_and_parse_feed():
    url = "https://docs.cloud.google.com/feeds/bigquery-release-notes.xml"
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    )
    
    try:
        # Create unverified context to bypass macOS missing SSL cert issues
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=10, context=context) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        entries = []
        
        for entry in root.findall('atom:entry', ATOM_NS):
            title_elem = entry.find('atom:title', ATOM_NS)
            updated_elem = entry.find('atom:updated', ATOM_NS)
            link_elem = entry.find("atom:link[@rel='alternate']", ATOM_NS)
            content_elem = entry.find('atom:content', ATOM_NS)
            
            title = title_elem.text if title_elem is not None else "Unknown Date"
            updated = updated_elem.text if updated_elem is not None else ""
            link = link_elem.get('href') if link_elem is not None else ""
            content = content_elem.text if content_elem is not None else ""
            
            entries.append({
                'date': title,
                'updated': updated,
                'link': link,
                'content': content
            })
            
        return entries, None
    except Exception as e:
        return [], str(e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/releases')
def get_releases():
    releases, error = fetch_and_parse_feed()
    if error:
        return jsonify({'status': 'error', 'message': error}), 500
    return jsonify({'status': 'success', 'releases': releases})

if __name__ == '__main__':
    # Bind to all interfaces to facilitate previewing
    app.run(host='0.0.0.0', port=5001, debug=True)
