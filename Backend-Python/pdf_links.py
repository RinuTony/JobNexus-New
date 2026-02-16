import os
import re
import fitz  # PyMuPDF package
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)

MAX_TEXT_LENGTH = 10000
UPLOADS_DIR = os.getenv("PHP_UPLOADS_DIR", r"C:\xampp\htdocs\JobNexus\Backend-PHP\uploads")

URL_PATTERN = re.compile(r'(https?://[^\s<>"\]\)]+|www\.[^\s<>"\]\)]+)', re.IGNORECASE)


def extract_text_from_pdf_path(file_path):
    try:
        doc = fitz.open(file_path)
        text = "".join(page.get_text() for page in doc)
        doc.close()
        return text[:MAX_TEXT_LENGTH] if len(text) > MAX_TEXT_LENGTH else text
    except Exception:
        return ""

def extract_links_from_annotations(file_path):
    try:
        doc = fitz.open(file_path)
        links = []
        seen = set()
        for page in doc:
            for link in page.get_links():
                uri = link.get("uri")
                if not uri:
                    continue
                if uri in seen:
                    continue
                seen.add(uri)
                label = "Website"
                lower = uri.lower()
                if "linkedin.com" in lower:
                    label = "LinkedIn"
                elif "github.com" in lower:
                    label = "GitHub"
                links.append({"label": label, "url": uri})
        doc.close()
        return links
    except Exception:
        return []

def extract_links_from_text(text):
    if not text:
        return []

    matches = URL_PATTERN.findall(text)
    if not matches:
        return []

    seen = set()
    links = []

    for raw in matches:
        url = raw.strip().rstrip(".,;)")
        if url.lower().startswith("www."):
            url = "https://" + url

        if url in seen:
            continue
        seen.add(url)

        label = "Website"
        lower = url.lower()
        if "linkedin.com" in lower:
            label = "LinkedIn"
        elif "github.com" in lower:
            label = "GitHub"

        links.append({"label": label, "url": url})

    return links


@app.route("/extract-links", methods=["POST"])
def extract_links():
    data = request.get_json() or {}
    filename = data.get("filename")

    if not filename:
        return jsonify({"success": False, "message": "filename is required"}), 400

    safe_name = os.path.basename(filename)
    file_path = os.path.join(UPLOADS_DIR, safe_name)

    if not os.path.exists(file_path):
        return jsonify({"success": False, "message": "file not found"}), 404

    links = extract_links_from_annotations(file_path)
    if not links:
        text = extract_text_from_pdf_path(file_path)
        links = extract_links_from_text(text)
    return jsonify({"success": True, "links": links})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
