import sqlite3
import os
import sys 

def get_base_path():
    """หาที่อยู่ของโฟลเดอร์หลักของโปรแกรม ไม่ว่าจะรันด้วย Python หรือ .exe"""
    if getattr(sys, 'frozen', False):
        # ถ้าเป็น .exe ให้หาโฟลเดอร์ที่ .exe ตัวนั้นวางอยู่
        return os.path.dirname(sys.executable)
    # ถ้าเป็น .py ปกติ ให้หาโฟลเดอร์ปัจจุบัน
    return os.path.dirname(os.path.abspath(__file__))

def connect_db(db_name="localization_data.db"):
    # แก้ให้ไปหาไฟล์ในโฟลเดอร์หลักของโปรแกรม
    base_dir = get_base_path()
    full_path = os.path.join(base_dir, db_name)
    conn = sqlite3.connect(full_path)
    return conn

def create_tables(db_name="localization_data.db"):
    """สร้างตารางสำหรับเก็บข้อมูลต่างๆ ทั้งหมด 3 ตาราง"""
    conn = connect_db(db_name)
    cursor = conn.cursor()
    
    # 1. ตารางเก็บคำศัพท์ (Glossary)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS glossary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            english_term TEXT UNIQUE NOT NULL,
            thai_translation TEXT NOT NULL
        )
    ''')
    
    # 2. ตารางเก็บ Tone ของโปรเจกต์ (เช่น "Fantasy", "Sci-Fi")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT NOT NULL
        )
    ''')
    
    # 3. ตารางเก็บข้อมูลตัวละคร (Character, Pronoun, Status)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS character_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            character_name TEXT UNIQUE NOT NULL,
            pronoun TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"[{db_name}] Connect/Create DB successfully")

# ==========================================
# 📘 หมวด: จัดการ Glossary (คำศัพท์)
# ==========================================
def add_glossary(en_term, th_term, db_name="localization_data.db"):
    conn = connect_db(db_name)
    cursor = conn.cursor()
    try:
        if en_term.strip() == th_term.strip():
            th_term += " (Keep English)"
        cursor.execute("INSERT INTO glossary (english_term, thai_translation) VALUES (?, ?)", (en_term, th_term))
        conn.commit()
    except sqlite3.IntegrityError:
        cursor.execute("UPDATE glossary SET thai_translation = ? WHERE english_term = ?", (th_term, en_term))
        conn.commit()
    finally:
        conn.close()

def get_all_glossary(db_name="localization_data.db"):
    conn = connect_db(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='glossary'")
    if not cursor.fetchone():
        create_tables(db_name)
        
    cursor.execute("SELECT english_term, thai_translation FROM glossary")
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

def delete_glossary(en_term, db_name="localization_data.db"):
    conn = connect_db(db_name)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM glossary WHERE english_term = ?", (en_term,))
    conn.commit()
    conn.close()

# ==========================================
# 🎭 หมวด: จัดการ Project Settings (Tone)
# ==========================================
def save_project_tone(tone_text, db_name="localization_data.db"):
    # 🌟 เพิ่มบรรทัดนี้เพื่อป้องกันกรณีตารางยังไม่ถูกสร้าง
    create_tables(db_name) 
    conn = connect_db(db_name)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO project_settings (setting_key, setting_value) VALUES ('tone', ?)", (tone_text,))
    except sqlite3.IntegrityError:
        cursor.execute("UPDATE project_settings SET setting_value = ? WHERE setting_key = 'tone'", (tone_text,))
    conn.commit()
    conn.close()

def get_project_tone(db_name="localization_data.db"):
    """ดึง Tone ของโปรเจกต์ออกมา (ถ้าไม่มีให้คืนค่าว่าง)"""
    conn = connect_db(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='project_settings'")
    if not cursor.fetchone():
        create_tables(db_name)
        
    cursor.execute("SELECT setting_value FROM project_settings WHERE setting_key = 'tone'")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else ""

# ==========================================
# 👥 หมวด: จัดการ Character Settings
# ==========================================
def add_character(name, pronoun, status, db_name="localization_data.db"):
    # 🌟 เพิ่มบรรทัดนี้
    create_tables(db_name)
    conn = connect_db(db_name)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO character_settings (character_name, pronoun, status) VALUES (?, ?, ?)", (name, pronoun, status))
    except sqlite3.IntegrityError:
        cursor.execute("UPDATE character_settings SET pronoun = ?, status = ? WHERE character_name = ?", (pronoun, status, name))
    conn.commit()
    conn.close()

def get_all_characters(db_name="localization_data.db"):
    """ดึงข้อมูลตัวละครทั้งหมดออกมาในรูปแบบ List of Dictionaries"""
    conn = connect_db(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='character_settings'")
    if not cursor.fetchone():
        create_tables(db_name)
        
    cursor.execute("SELECT character_name, pronoun, status FROM character_settings")
    rows = cursor.fetchall()
    conn.close()
    
    # ส่งกลับไปเป็น List ที่ข้างในเป็น Dict เช่น [{'name': 'Traveler', 'pronoun': 'ผม', 'status': 'Male'}]
    return [{"name": r[0], "pronoun": r[1], "status": r[2]} for r in rows]

def delete_character(name, db_name="localization_data.db"):
    """ลบตัวละคร"""
    conn = connect_db(db_name)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM character_settings WHERE character_name = ?", (name,))
    conn.commit()
    conn.close()

# ==========================================
# 🚀 โซนทดสอบระบบฐานข้อมูล
# ==========================================
if __name__ == "__main__":
    db = "Test_Project.db"
    create_tables(db)
    
    # ทดสอบ Tone
    save_project_tone("Fantasy", db)
    print(f"Tone: {get_project_tone(db)}")
    
    # ทดสอบ ตัวละคร
    add_character("Paimon", "ฉัน (Female)", "NPC", db)
    add_character("Venti", "ผม (Male)", "Archon", db)
    print(f"Characters: {get_all_characters(db)}")