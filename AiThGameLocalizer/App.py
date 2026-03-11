from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sys
import json
import tkinter as tk
from tkinter import filedialog
import threading
import webview
import logging

# ==========================================
# 🌟 1. ตั้งค่า Path สำหรับตอนเป็นโปรแกรม .exe
# ==========================================
def get_app_dir():
    """หาที่อยู่ของไฟล์ .exe เพื่อให้สร้าง Database หรือหาไฟล์ AI Model เจอ"""
    if getattr(sys, 'frozen', False): return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_resource_dir():
    """หาที่อยู่ของโฟลเดอร์ dist (หน้าเว็บ) ที่ถูกฝังมากับตัว .exe"""
    if getattr(sys, 'frozen', False): return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

# บังคับให้โปรแกรมทำงานและเซฟไฟล์ต่างๆ ไว้ในโฟลเดอร์เดียวกับ .exe เสมอ
os.chdir(get_app_dir())

from DBManager import (
    create_tables, get_project_tone, save_project_tone,
    get_all_glossary, add_glossary, delete_glossary,
    get_all_characters, add_character, delete_character
)
from MainModelRun import translate_text

CURRENT_FILE_CONTENT = None

# ==========================================
# 🌟 2. ตั้งค่า Flask ให้รันหน้าเว็บอัตโนมัติ
# ==========================================
# ให้ Python ไปดึงหน้าเว็บจากโฟลเดอร์ frontend/dist มาแสดงผล
dist_folder = os.path.join(get_resource_dir(), 'frontend', 'dist')
app = Flask(__name__, static_folder=dist_folder, static_url_path='/')
CORS(app)

@app.route('/')
def index():
    return app.send_static_file('index.html')

# ==========================================
# 📡 API ROUTES 
# ==========================================
@app.route('/api/projects', methods=['GET'])
def get_existing_projects():
    projects = [f[:-3] for f in os.listdir('.') if f.endswith('.db')]
    return jsonify(sorted(projects) if projects else ["Global_Glossary"])

@app.route('/api/projects/new', methods=['POST'])
def create_project():
    create_tables(f"{request.json.get('project_name')}.db")
    return jsonify({"success": True})

@app.route('/api/details/<project_name>', methods=['GET'])
def get_project_details(project_name):
    db = f"{project_name}.db"
    try: glossary_data = [{"en": en, "th": th} for en, th in get_all_glossary(db).items()]
    except: glossary_data = []
    try: character_data = get_all_characters(db)
    except: character_data = []
    return jsonify({"tone": get_project_tone(db) or "", "glossary": glossary_data, "characters": character_data})

@app.route('/api/tone/update', methods=['POST'])
def update_tone():
    save_project_tone(request.json.get('tone'), f"{request.json.get('project_name')}.db")
    return jsonify({"success": True})

@app.route('/api/glossary/add', methods=['POST'])
def add_term():
    data = request.json
    add_glossary(data.get('en'), data.get('th'), f"{data.get('project_name')}.db")
    return jsonify({"success": True})

@app.route('/api/glossary/delete', methods=['POST'])
def delete_term():
    delete_glossary(request.json.get('en'), f"{request.json.get('project_name')}.db")
    return jsonify({"success": True})

@app.route('/api/characters/add', methods=['POST'])
def add_char():
    data = request.json
    add_character(data.get('name'), data.get('pronoun'), data.get('status'), f"{data.get('project_name')}.db")
    return jsonify({"success": True})

@app.route('/api/characters/delete', methods=['POST'])
def delete_char():
    delete_character(request.json.get('name'), f"{request.json.get('project_name')}.db")
    return jsonify({"success": True})

def build_smart_context(db_name, input_text, speaker_name=None):
    tone = get_project_tone(db_name)
    characters = get_all_characters(db_name)
    glossary = get_all_glossary(db_name)
    context_parts = []
    if tone: context_parts.append(f"Tone: {tone}")
    if speaker_name:
        for char in characters:
            if char['name'].lower() == speaker_name.lower():
                if char['pronoun']: context_parts.append(f"Pronouns: '{char['pronoun']}'")
                break
    if glossary:
        used_terms = []
        for en, th in glossary.items():
            if en.lower() in input_text.lower():
                used_terms.append(f"{en}={th}")
        if used_terms: context_parts.append(f"Glossary: {', '.join(used_terms)}")
    return ". ".join(context_parts)

@app.route('/api/translate', methods=['POST'])
def translate_test():
    data = request.json
    result = translate_text(build_smart_context(f"{data.get('project_name')}.db", data.get('text', ''), data.get('speaker', '')), data.get('text', ''))
    return jsonify({"result": result})

@app.route('/api/file/dialog', methods=['GET'])
def open_dialog():
    root = tk.Tk(); root.attributes("-topmost", True); root.withdraw()
    path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
    root.destroy()
    return jsonify({"path": path or ""})

@app.route('/api/file/save_dialog', methods=['GET'])
def save_dialog():
    root = tk.Tk(); root.attributes("-topmost", True); root.withdraw()
    path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")], title="Save Translated File As...")
    root.destroy()
    return jsonify({"path": path or ""})

def extract_rows(content):
    rows = []
    if isinstance(content, list):
        for idx, item in enumerate(content):
            rows.append({"id": idx, "speaker": item.get("speaker", ""), "original": item.get("input", ""), "translated": ""})
    return rows

@app.route('/api/file/read', methods=['POST'])
def read_file():
    global CURRENT_FILE_CONTENT
    file_path = request.json.get('path')
    if not file_path or not os.path.exists(file_path): return jsonify({"error": "File not found"}), 400
    try:
        with open(file_path, 'r', encoding='utf-8') as f: CURRENT_FILE_CONTENT = json.load(f)
        return jsonify({"rows": extract_rows(CURRENT_FILE_CONTENT)})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/file/read_drop', methods=['POST'])
def read_dropped_file():
    global CURRENT_FILE_CONTENT
    try:
        content = json.loads(request.json.get('content'))
        CURRENT_FILE_CONTENT = content
        return jsonify({"rows": extract_rows(content)})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route('/api/file/save', methods=['POST'])
def save_file():
    global CURRENT_FILE_CONTENT
    data = request.json
    save_path = data.get('save_path')
    rows = data.get('data')
    if CURRENT_FILE_CONTENT is None: return jsonify({"error": "No file in memory"}), 400
    try:
        if isinstance(CURRENT_FILE_CONTENT, list):
            for row in rows:
                idx = row['id']
                if idx < len(CURRENT_FILE_CONTENT):
                    final_text = row['translated'] if row['translated'] else row['original']
                    if 'input' in CURRENT_FILE_CONTENT[idx]: del CURRENT_FILE_CONTENT[idx]['input']
                    CURRENT_FILE_CONTENT[idx]['output'] = final_text
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(CURRENT_FILE_CONTENT, f, ensure_ascii=False, indent=4)
        return jsonify({"success": True})
    except Exception as e: return jsonify({"error": str(e)}), 500

# ==========================================
# 🌟 3. START DESKTOP APP
# ==========================================
def start_flask():
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    import flask.cli
    flask.cli.show_server_banner = lambda *args, **kwargs: None
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    t = threading.Thread(target=start_flask)
    t.daemon = True
    t.start()
    
    # 🌟 เรียกหน้าเว็บจากที่ Flask เสิร์ฟไว้ (port 5000)
    webview.create_window('AiThLocalizer Desktop', 'http://127.0.0.1:5000', width=1300, height=850)
    webview.start()