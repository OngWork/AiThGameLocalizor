import json
import os
from MainModelRun import translate_text
from DBManager import get_all_glossary

def process_json_file(input_filepath, output_filepath, context_tone):
    """ฟังก์ชันสำหรับอ่าน แปล และเซฟไฟล์ JSON"""
    print(f"Open file: {input_filepath}")
    
    # 1. อ่านไฟล์ JSON ต้นฉบับ
    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ อ่านไฟล์ไม่สำเร็จ: {e}")
        return

    # 2. ดึงข้อมูล Glossary มาผสมเป็น Context
    glossary_dict = get_all_glossary()
    glossary_str = ", ".join([f"{eng} = {thai}" for eng, thai in glossary_dict.items()])
    
    # สร้าง Context แบบเต็มที่รวม Tone และ Glossary
    full_context = f"Tone: {context_tone}. Glossary: {glossary_str}"
    print(f"Context ที่ใช้: {full_context}")
    print("-" * 40)

    translated_data = {}
    
    # 3. วนลูปแปลข้อความทีละบรรทัด (สมมติว่า JSON เป็นแบบ {"key": "text"})
    total_items = len(data)
    current_item = 1
    
    for key, text in data.items():
        print(f"แปลบรรทัดที่ {current_item}/{total_items}...")
        print(f"   [EN]: {text}")
        
        # ส่งไปให้ ai_engine แปล
        thai_text = translate_text(full_context, text)
        print(f"   [TH]: {thai_text}\n")
        
        # เก็บคำแปลลง Dictionary ใหม่
        translated_data[key] = thai_text
        current_item += 1

    # 4. เซฟกลับเป็นไฟล์ JSON อันใหม่
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            # ensure_ascii=False ทำให้เซฟภาษาไทยได้โดยไม่กลายเป็นรหัสเอเลี่ยน
            json.dump(translated_data, f, ensure_ascii=False, indent=4)
        print("-" * 40)
        print(f"✅ Translated and saved to: {output_filepath}")
    except Exception as e:
        print(f"❌ Save failed: {e}")

# ==========================================
# 🚀 โซนทดสอบระบบจัดการไฟล์
# ==========================================
if __name__ == "__main__":
    # 1. สร้างไฟล์ JSON จำลองขึ้นมาเพื่อทดสอบ
    dummy_json_path = "test_game_data.json"
    dummy_data = {
        "dialogue_01": "Welcome back! How was your journey to Mondstadt?",
        "dialogue_02": "The Astral Express looks so big and shiny!",
        "item_desc_01": "A rare drop from a giant Slime."
    }
    
    # เขียนไฟล์จำลองลงเครื่อง
    with open(dummy_json_path, 'w', encoding='utf-8') as f:
        json.dump(dummy_data, f, indent=4)
        
    print("✨ สร้างไฟล์ test_game_data.json สำหรับทดสอบแล้ว")
    print("=" * 40)
    
    # 2. เริ่มทดสอบการแปลไฟล์
    output_json_path = "translated_game_data.json"
    my_context = "Fantasy/Adventure. Pronouns: 'ฉัน' (Female) calls listener 'คุณ'."
    
    process_json_file(dummy_json_path, output_json_path, my_context)