import sys
import os
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QPushButton, QLabel, 
                             QLineEdit, QComboBox, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMessageBox, QInputDialog, QFileDialog, 
                             QTextEdit, QProgressBar, QFrame) # 🌟 เพิ่ม QFrame ตรงนี้แล้ว
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from DBManager import (
    get_all_glossary, add_glossary, delete_glossary,
    save_project_tone, get_project_tone,
    get_all_characters, add_character, delete_character
)
from MainModelRun import translate_text

def get_base_path():
    """หาที่อยู่ของโฟลเดอร์หลักของโปรแกรม ไม่ว่าจะรันด้วย Python หรือ .exe"""
    if getattr(sys, 'frozen', False):
        # ถ้าเป็น .exe ให้หาโฟลเดอร์ที่ .exe ตัวนั้นวางอยู่
        return os.path.dirname(sys.executable)
    # ถ้าเป็น .py ปกติ ให้หาโฟลเดอร์ปัจจุบัน
    return os.path.dirname(os.path.abspath(__file__))

# ฟังก์ชันใหม่สำหรับสร้าง Context (วางไว้นอก Class หรือเป็น StaticMethod)
def build_smart_context(db_name, input_text, speaker_name=None):
    from DBManager import get_project_tone, get_all_characters, get_all_glossary
    
    # 1. ดึง Tone
    tone = get_project_tone(db_name) or "General"
    
    # 2. หาข้อมูลคนพูด (Pronouns)
    pronoun_str = "Unknown"
    if speaker_name:
        chars = get_all_characters(db_name)
        for c in chars:
            if c['name'].strip().lower() == speaker_name.strip().lower():
                pronoun_str = f"'{c['pronoun']}' ({c['status']})"
                break
    if pronoun_str == "Unknown":
        pronoun_str = ""
    else: pronoun_str = f"Pronouns: {pronoun_str}."
    
    # 3. กรอง Glossary (ใส่เฉพาะคำที่เจอใน input_text)
    full_glossary = get_all_glossary(db_name)
    matched_glossary = []
    for eng, thai in full_glossary.items():
        if eng.lower() in input_text.lower(): # เช็คว่ามีคำภาษาอังกฤษในประโยคไหม
            matched_glossary.append(f"{eng} = {thai}")
    
    glossary_final = ", ".join(matched_glossary) if matched_glossary else "None"
    
    # 4. ประกอบร่างตาม Format ที่คุณต้องการ
    # {Tone: Fantasy. Pronouns: 'ผม' (Male). Glossary: Mondstadt = Mondstadt (Keep English)}
    context = f"Tone: {tone}. {pronoun_str} Glossary: {glossary_final}"
    return context

# ==========================================
# 🚀 โซน Custom Widgets และ Workers
# ==========================================
class DragDropLabel(QLabel):
    file_dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__("Drag file!")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 3px dashed #8e44ad; 
                border-radius: 10px; 
                font-size: 20px; 
                font-weight: bold;
                color: #8e44ad;
            }
        """)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            self.setStyleSheet("border: 3px dashed #27ae60; border-radius: 10px; font-size: 20px; font-weight: bold; color: #27ae60;")
            event.accept()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("border: 3px dashed #8e44ad; border-radius: 10px; font-size: 20px; font-weight: bold; color: #8e44ad;")

    def dropEvent(self, event):
        self.setStyleSheet("border: 3px dashed #8e44ad; border-radius: 10px; font-size: 20px; font-weight: bold; color: #8e44ad;")
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            file_path = files[0]
            if file_path.endswith('.json'):
                self.setText(os.path.basename(file_path))
                self.file_dropped.emit(file_path)
            else:
                QMessageBox.warning(self, "Invalid File", "Please drop a .json file.")

class SingleTranslateWorker(QThread):
    result_signal = pyqtSignal(str)

    def __init__(self, text, speaker, db_name): # 🌟 ต้องมี 3 พารามิเตอร์ (ไม่นับ self)
        super().__init__()
        self.text = text
        self.speaker = speaker
        self.db_name = db_name

    def run(self):
        # เรียกใช้ฟังก์ชันประกอบ Context แบบฉลาดที่เราสร้างไว้
        context = build_smart_context(self.db_name, self.text, self.speaker)
        print(f"Context: {context}")
        result = translate_text(context, self.text)
        self.result_signal.emit(result)
    
class TranslationWorker(QThread):
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal(list) # ส่งค่ากลับเป็น List เพื่อไปทำตาราง Preview

    def __init__(self, input_path, db_name): # 🌟 รับแค่ 2 ค่า (ไม่รวม self)
        super().__init__()
        self.input_path = input_path
        self.db_name = db_name

    def run(self):
        try:
            with open(self.input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            translated_results = []
            total_items = len(data)
            
            for i, item in enumerate(data):
                speaker = item.get("speaker", "")
                original_text = item.get("input", "")
                
                # ใช้ Smart Context ที่กรอง Glossary เฉพาะในประโยค
                context = build_smart_context(self.db_name, original_text, speaker)
                translated_text = translate_text(context, original_text)
                
                translated_results.append({
                    "speaker": speaker,
                    "original": original_text,
                    "translated": translated_text
                })
                self.progress_signal.emit(i + 1, total_items)
            
            self.finished_signal.emit(translated_results)
        except Exception as e:
            print(f"Error: {e}")
            self.finished_signal.emit([])

# ==========================================
# 🚀 คลาสหลักของ UI
# ==========================================
class AILocalizerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Game Localizer")
        self.resize(850, 600)

        self.current_db = "Global_Glossary.db"
        self.is_loading = False

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        self.tab1 = QWidget()
        self.tab2 = QWidget() 
        
        self.tabs.addTab(self.tab1, "Translation Hub")
        self.tabs.addTab(self.tab2, "Glossary Manager")

        self.setup_translation_tab()
        self.setup_glossary_tab()
        
    def run_test_sentence(self):
        """เมื่อกด OK เพื่อแปลประโยคทดสอบ"""
        text = self.test_input.text().strip()
        speaker = self.test_speaker_in.text().strip() # 🌟 ดึงชื่อคนพูดจากช่องที่เพิ่มใหม่
        if not text:
            return
            
        selected_db = f"{self.test_combo.currentText()}.db"
        self.test_output.setText("Translating... ⏳")
        self.test_ok_btn.setEnabled(False)
        
        # 🌟 แก้ไข: ส่ง 'speaker' เพิ่มเข้าไปเป็นตัวที่สอง
        self.test_worker = SingleTranslateWorker(text, speaker, selected_db)
        self.test_worker.result_signal.connect(self.on_test_sentence_done)
        self.test_worker.start()

    def get_existing_projects(self):
        projects = []
        # เปลี่ยนจาก os.listdir('.') เป็นการสแกนใน base_path
        base_dir = get_base_path()
        for file in os.listdir(base_dir):
            if file.endswith('.db'):
                projects.append(file[:-3])
        if not projects:
            projects = ["Global_Glossary"]
        return sorted(projects)
    
    def resizeEvent(self, event):
        """คำนวณสัดส่วนตารางใหม่ทุกครั้งที่ขยายหน้าต่างโปรแกรม"""
        super().resizeEvent(event)
        width = self.review_table.width()
        if width > 0:
            self.review_table.setColumnWidth(0, int(width * 0.2)) # 1/5
            self.review_table.setColumnWidth(1, int(width * 0.4)) # 2/5
            self.review_table.setColumnWidth(2, int(width * 0.4)) # 2/5
    
    def on_translation_finished(self, results):
        self.begin_btn.setEnabled(True)
        if not results:
            QMessageBox.warning(self, "Error", "Translation failed.")
            return

        self.review_table.setRowCount(0)
        for row, item in enumerate(results):
            self.review_table.insertRow(row)
            
            # Speaker & Original (อ่านอย่างเดียว)
            spk = QTableWidgetItem(item['speaker'])
            spk.setFlags(spk.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.review_table.setItem(row, 0, spk)
            
            en = QTableWidgetItem(item['original'])
            en.setFlags(en.flags() ^ Qt.ItemFlag.ItemIsEditable)
            self.review_table.setItem(row, 1, en)
            
            # Translated (แก้ไขได้!)
            self.review_table.setItem(row, 2, QTableWidgetItem(item['translated']))

        self.export_btn.setEnabled(True)
        self.status_label.setText("✅ Translation Finished! You can edit and export now.")

    def export_final_json(self):
        if self.review_table.rowCount() == 0:
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Save Translated JSON", "", "JSON Files (*.json)")
        if file_path:
            final_data = []
            for row in range(self.review_table.rowCount()):
                final_data.append({
                    "speaker": self.review_table.item(row, 0).text(),
                    "input": self.review_table.item(row, 2).text() # เซฟคำแปลจากตารางที่อาจถูกแก้แล้ว
                })
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(final_data, f, ensure_ascii=False, indent=4)
                QMessageBox.information(self, "Saved", "File saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not save file: {e}")

    # ------------------------------------------
    # 🌟 โซนของ Tab 1: Translation Hub
    # ------------------------------------------
    def setup_translation_tab(self):
        # สร้าง Layout หลักสำหรับ Tab 1 (ไม่ใช้ Stacked Widget แล้ว)
        layout = QVBoxLayout(self.tab1)
        layout.setSpacing(15)
        self.selected_file_path = None 

        # --- ส่วนบน: แปลประโยคเดียว (Test Sentence) ---
        test_layout = QVBoxLayout()
        test_top_row = QHBoxLayout()
        
        test_label = QLabel("Translate\ntest sentence")
        test_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #6a1b9a;")
        
        self.test_input = QLineEdit()
        self.test_input.setPlaceholderText("input a sentence")
        self.test_input.setStyleSheet("border: 2px solid #6a1b9a; border-radius: 5px; padding: 5px; font-size: 14px;")
        
        self.test_speaker_in = QLineEdit()
        self.test_speaker_in.setPlaceholderText("Speaker name")
        self.test_speaker_in.setFixedWidth(120)
        self.test_speaker_in.setStyleSheet("border: 2px solid #6a1b9a; border-radius: 5px; padding: 5px; font-size: 14px;")
        
        self.test_combo = QComboBox()
        existing_projects = self.get_existing_projects()
        self.test_combo.addItems(existing_projects)
        if "Global_Glossary" in existing_projects:
            self.test_combo.setCurrentText("Global_Glossary")
        # ปรับสีพื้นหลัง Dropdown ให้เป็นสีขาวตามที่คุณต้องการ
        self.test_combo.setStyleSheet("background-color: white; color: black; border: 2px solid #6a1b9a; border-radius: 5px; padding: 5px; font-size: 14px;")
        
        self.test_ok_btn = QPushButton("OK")
        self.test_ok_btn.setStyleSheet("border: 2px solid #c0392b; color: #c0392b; font-weight: bold; padding: 5px 15px; border-radius: 5px; font-size: 14px;")
        self.test_ok_btn.clicked.connect(self.run_test_sentence)

        test_top_row.addWidget(test_label)
        test_top_row.addWidget(self.test_input)
        test_top_row.addWidget(self.test_speaker_in)
        test_top_row.addWidget(self.test_combo)
        test_top_row.addWidget(self.test_ok_btn)

        self.test_output = QLineEdit()
        self.test_output.setPlaceholderText("output a sentence")
        self.test_output.setReadOnly(True)
        self.test_output.setStyleSheet("border: 2px solid #6a1b9a; border-radius: 5px; padding: 5px; font-size: 14px; background-color: #f3e5f5;")

        test_layout.addLayout(test_top_row)
        test_layout.addWidget(self.test_output)
        layout.addLayout(test_layout)

        # --- เส้นคั่น (Separator) ---
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #6a1b9a; border-top: 3px solid #6a1b9a;")
        layout.addWidget(line)

        # --- ส่วนกลาง: ระบบไฟล์และปุ่ม Begin ---
        action_layout = QHBoxLayout()
        action_layout.setSpacing(15)

        self.drag_drop_box = DragDropLabel() #
        self.drag_drop_box.setFixedSize(180, 150)
        self.drag_drop_box.file_dropped.connect(self.on_file_selected)

        self.select_file_btn = QPushButton("Select\nexist file")
        self.select_file_btn.setFixedSize(180, 150)
        self.select_file_btn.setStyleSheet("border: 3px solid #8e44ad; font-size: 20px; font-weight: bold; color: #8e44ad; background-color: transparent; border-radius: 10px;")
        self.select_file_btn.clicked.connect(self.browse_input)

        glossary_container = QWidget()
        glossary_container.setFixedSize(180, 150)
        glossary_container.setStyleSheet("border: 3px solid #8e44ad; border-radius: 10px;")
        
        glossary_layout = QVBoxLayout(glossary_container)
        glossary_label = QLabel("Select\nGlossary")
        glossary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        glossary_label.setStyleSheet("border: none; font-size: 20px; font-weight: bold; color: #8e44ad;")
        
        self.tab1_glossary_combo = QComboBox()
        # ปรับสีพื้นหลัง Dropdown ให้เป็นสีขาว
        self.tab1_glossary_combo.setStyleSheet("background-color: white; color: black; border: 1px solid #8e44ad; padding: 5px;")
        self.tab1_glossary_combo.addItems(existing_projects)
        if "Global_Glossary" in existing_projects:
            self.tab1_glossary_combo.setCurrentText("Global_Glossary")
        
        glossary_layout.addWidget(glossary_label)
        glossary_layout.addWidget(self.tab1_glossary_combo)

        action_layout.addWidget(self.drag_drop_box)
        action_layout.addWidget(self.select_file_btn)
        action_layout.addWidget(glossary_container)
        
        action_wrapper = QHBoxLayout()
        action_wrapper.addStretch()
        action_wrapper.addLayout(action_layout)
        action_wrapper.addStretch()
        layout.addLayout(action_wrapper)

        # --- ปุ่ม Begin ---
        self.begin_btn = QPushButton("Begin")
        self.begin_btn.setStyleSheet("""
            QPushButton {
                border: 3px solid #c0392b; 
                color: #c0392b; 
                font-size: 28px; 
                font-weight: bold; 
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #f2d7d5; }
        """)
        self.begin_btn.clicked.connect(self.start_translation)
        
        begin_layout = QHBoxLayout()
        begin_layout.addStretch()
        begin_layout.addWidget(self.begin_btn, 1)
        begin_layout.addStretch()
        layout.addLayout(begin_layout)

        # --- ส่วนความคืบหน้า (Status & Loading) ---
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # 🌟 เพิ่ม Progress Bar ตรงนี้ถ้ายังไม่มีในโค้ดของคุณ
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # --- ส่วนล่าง: Review Table (ย้ายมาไว้ตรงนี้) ---
        layout.addWidget(QLabel("<b>Review Translation:</b> Double click to edit Thai text"))
        
        self.review_table = QTableWidget(0, 3)
        self.review_table.setHorizontalHeaderLabels(["Speaker", "Original (EN)", "Translated (TH)"])
        
        header = self.review_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.review_table.setMinimumHeight(350) 
        layout.addWidget(self.review_table, 1)
        # 🌟 ปรับสัดส่วนคอลัมน์ (Speaker=1/5, EN=2/5, TH=2/5)
        header = self.review_table.horizontalHeader()
        
        layout.addWidget(self.review_table)

        # --- ส่วนสุดท้าย: ปุ่ม Export ---
        self.export_btn = QPushButton("💾 Save & Export JSON")
        self.export_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 10px; font-size: 16px;")
        self.export_btn.clicked.connect(self.export_final_json)
        self.export_btn.setEnabled(False) # ปิดไว้จนกว่าจะแปลเสร็จ
        layout.addWidget(self.export_btn, 0)

        layout.addStretch()

    # ==========================================
    # 🌟 โซนของ Tab 2: Glossary Manager
    # ==========================================
    def setup_glossary_tab(self):
        layout = QVBoxLayout(self.tab2)
        layout.setSpacing(10)

        # 1. Header: Project Selection & Tone
        header_layout = QHBoxLayout()
        
        header_layout.addWidget(QLabel("Select Game Project:"))
        self.project_combo = QComboBox()
        existing_projects = self.get_existing_projects()
        self.project_combo.addItems(existing_projects)
        if "Global_Glossary" in existing_projects:
            self.project_combo.setCurrentText("Global_Glossary")
        # เชื่อมต่อ Signal หลังจากตั้งค่าเริ่มต้นเสร็จ เพื่อป้องกันการเปลี่ยน DB ไปมาตอนโหลด
        self.project_combo.currentTextChanged.connect(self.on_project_changed)
        # อัปเดต current_db ให้ตรงกับที่เลือกใน Dropdown ทันที
        self.current_db = f"{self.project_combo.currentText()}.db"
        header_layout.addWidget(self.project_combo, 1)

        header_layout.addWidget(QLabel("Tone:"))
        self.tone_input = QLineEdit()
        self.tone_input.setPlaceholderText("e.g. Fantasy, Sci-Fi")
        # บันทึก Tone อัตโนมัติเมื่อพิมพ์เสร็จ (EditingFinished) เพื่อไม่ให้รบกวนการพิมพ์
        self.tone_input.editingFinished.connect(self.save_tone_ui)
        header_layout.addWidget(self.tone_input, 1)

        self.new_project_btn = QPushButton("New Project")
        self.new_project_btn.clicked.connect(self.create_new_project)
        header_layout.addWidget(self.new_project_btn)
        
        layout.addLayout(header_layout)

        # 2. Search Bar (Full Width)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search in all tables...")
        self.search_input.textChanged.connect(self.filter_all_tables)
        layout.addWidget(self.search_input)

        # 3. Main Tables Area (Two Columns)
        tables_layout = QHBoxLayout()
        
        # --- Left Column: Glossary ---
        glossary_col = QVBoxLayout()
        glossary_col.addWidget(QLabel("<b>General Glossary</b>"))
        self.glossary_table = QTableWidget(0, 3)
        self.glossary_table.setHorizontalHeaderLabels(["Eng term", "Th term", "action"])
        self.glossary_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.glossary_table.setColumnWidth(2, 70)
        self.glossary_table.itemChanged.connect(self.on_glossary_item_changed)
        glossary_col.addWidget(self.glossary_table)
        
        # Glossary Input at Bottom
        glossary_in_layout = QHBoxLayout()
        self.en_in = QLineEdit(); self.en_in.setPlaceholderText("English")
        self.th_in = QLineEdit(); self.th_in.setPlaceholderText("Thai")
        self.add_glossary_btn = QPushButton("Add/Update")
        self.add_glossary_btn.clicked.connect(self.add_glossary_ui)
        glossary_in_layout.addWidget(self.en_in)
        glossary_in_layout.addWidget(self.th_in)
        glossary_in_layout.addWidget(self.add_glossary_btn)
        glossary_col.addLayout(glossary_in_layout)
        
        # --- Right Column: Character Settings ---
        char_col = QVBoxLayout()
        char_col.addWidget(QLabel("<b>Character Settings</b>"))
        self.char_table = QTableWidget(0, 4)
        self.char_table.setHorizontalHeaderLabels(["Character", "Pronoun", "Status", "action"])
        self.char_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.char_table.setColumnWidth(3, 70)
        self.char_table.itemChanged.connect(self.on_char_item_changed)
        char_col.addWidget(self.char_table)
        
        # Character Input at Bottom
        char_in_layout = QHBoxLayout()
        self.char_name_in = QLineEdit(); self.char_name_in.setPlaceholderText("Name")
        self.char_pro_in = QLineEdit(); self.char_pro_in.setPlaceholderText("Pronoun")
        self.char_stat_in = QLineEdit(); self.char_stat_in.setPlaceholderText("Status")
        self.add_char_btn = QPushButton("Add/Update")
        self.add_char_btn.clicked.connect(self.add_character_ui)
        char_in_layout.addWidget(self.char_name_in)
        char_in_layout.addWidget(self.char_pro_in)
        char_in_layout.addWidget(self.char_stat_in)
        char_in_layout.addWidget(self.add_char_btn)
        char_col.addLayout(char_in_layout)

        tables_layout.addLayout(glossary_col)
        tables_layout.addLayout(char_col)
        layout.addLayout(tables_layout)

        self.load_all_data()
        
    # --- ฟังก์ชันจัดการข้อมูล ---
    
    def save_tone_ui(self):
        save_project_tone(self.tone_input.text(), self.current_db)

    def load_all_data(self):
        self.is_loading = True
        # โหลด Tone
        self.tone_input.setText(get_project_tone(self.current_db))
        
        # โหลด Glossary
        self.load_glossary_table()
        
        # โหลด Characters
        self.load_char_table()
        self.is_loading = False

    def load_char_table(self):
        self.char_table.setRowCount(0)
        chars = get_all_characters(self.current_db)
        for row, c in enumerate(chars):
            self.char_table.insertRow(row)
            name_item = QTableWidgetItem(c['name'])
            name_item.setData(Qt.ItemDataRole.UserRole, c['name'])
            self.char_table.setItem(row, 0, name_item)
            self.char_table.setItem(row, 1, QTableWidgetItem(c['pronoun']))
            self.char_table.setItem(row, 2, QTableWidgetItem(c['status']))
            
            del_btn = QPushButton("delete")
            del_btn.setStyleSheet("color: red;")
            del_btn.clicked.connect(lambda ch, n=c['name']: self.delete_char_ui(n))
            self.char_table.setCellWidget(row, 3, del_btn)

    def add_character_ui(self):
        name = self.char_name_in.text().strip()
        pronoun = self.char_pro_in.text().strip()
        status = self.char_stat_in.text().strip()
        if name:
            add_character(name, pronoun, status, self.current_db)
            self.load_char_table()
            self.char_name_in.clear(); self.char_pro_in.clear(); self.char_stat_in.clear()

    def delete_char_ui(self, name):
        if QMessageBox.question(self, "Delete", f"Delete character '{name}'?") == QMessageBox.StandardButton.Yes:
            delete_character(name, self.current_db)
            self.load_char_table()

    def filter_all_tables(self, text):
        # ค้นหาพร้อมกันทั้ง 2 ตาราง
        self.filter_table(self.glossary_table, text)
        self.filter_table(self.char_table, text)

    def filter_table(self, table, text):
        text = text.lower()
        for r in range(table.rowCount()):
            match = False
            for c in range(table.columnCount() - 1): # ไม่ค้นในคอลัมน์ action
                item = table.item(r, c)
                if item and text in item.text().lower():
                    match = True; break
            table.setRowHidden(r, not match)


    def on_test_sentence_done(self, result):
        self.test_output.setText(result)
        self.test_ok_btn.setEnabled(True)

    def browse_input(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open JSON File", "", "JSON Files (*.json);;All Files (*)")
        if file_name: self.on_file_selected(file_name)

    def on_file_selected(self, file_path):
        self.selected_file_path = file_path
        file_basename = os.path.basename(file_path)
        self.select_file_btn.setText(f"Selected:\n{file_basename}")
        self.status_label.setText(f"Ready to translate: {file_basename}")

    def start_translation(self):
        """แก้ไข: ล้างตารางเดิมทิ้งทันทีที่กด Begin"""
        if not self.selected_file_path:
            QMessageBox.warning(self, "No File", "Please select or drag a JSON file first!")
            return

        # 🌟 เพิ่มบรรทัดนี้เพื่อ Reset ตารางและปุ่ม Export ทุกครั้งที่เริ่มรอบใหม่
        self.review_table.setRowCount(0)
        self.export_btn.setEnabled(False)
        
        input_file = self.selected_file_path
        selected_db = f"{self.tab1_glossary_combo.currentText()}.db"

        self.begin_btn.setEnabled(False)
        self.status_label.setText("Translating... Please wait ⏳")

        self.worker = TranslationWorker(input_file, selected_db)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.finished_signal.connect(self.on_translation_finished) 
        self.worker.start()

    def update_progress(self, current, total):
        self.status_label.setText(f"Translating: {current} / {total} items ⏳")

    def translation_finished(self, success):
        self.begin_btn.setEnabled(True)
        if success:
            self.status_label.setText("✅ Translation Complete! (Saved as _TH.json)")
            QMessageBox.information(self, "Success", "Translation completed successfully!")
        else:
            self.status_label.setText("❌ Translation Failed!")

    # --- ฟังก์ชันของ Tab 2 ---
    def on_glossary_item_changed(self, item):
        """บันทึก Glossary อัตโนมัติเมื่อมีการแก้ไขในตาราง"""
        if self.is_loading: return
        row = item.row()
        en_item = self.glossary_table.item(row, 0)
        th_item = self.glossary_table.item(row, 1)
        if not en_item or not th_item: return
            
        old_en = en_item.data(Qt.ItemDataRole.UserRole)
        new_en = en_item.text().strip()
        new_th = th_item.text().strip()
        
        if not new_en or not new_th: return
            
        if old_en and old_en != new_en:
            delete_glossary(old_en, self.current_db)
        
        add_glossary(new_en, new_th, self.current_db)
        en_item.setData(Qt.ItemDataRole.UserRole, new_en) # อัปเดตค่าที่จำไว้
        print(f"📝 Auto-saved Glossary: {new_en}")

    def on_char_item_changed(self, item):
        """บันทึก Character Settings อัตโนมัติเมื่อมีการแก้ไขในตาราง"""
        if self.is_loading: return
        row = item.row()
        name_item = self.char_table.item(row, 0)
        pro_item = self.char_table.item(row, 1)
        stat_item = self.char_table.item(row, 2)
        if not name_item or not pro_item or not stat_item: return
            
        old_name = name_item.data(Qt.ItemDataRole.UserRole)
        new_name = name_item.text().strip()
        new_pro = pro_item.text().strip()
        new_stat = stat_item.text().strip()
        
        if not new_name: return
            
        if old_name and old_name != new_name:
            delete_character(old_name, self.current_db)
        
        add_character(new_name, new_pro, new_stat, self.current_db)
        name_item.setData(Qt.ItemDataRole.UserRole, new_name)
        print(f"📝 Auto-saved Character: {new_name}")
        
    def on_project_changed(self, project_name):
        self.current_db = f"{project_name}.db"
        self.search_input.clear() 
        self.load_all_data()

    def create_new_project(self):
        text, ok = QInputDialog.getText(self, 'New Project', 'Enter new game project name:')
        if ok and text:
            text = text.replace(" ", "_")
            self.project_combo.addItem(text)
            self.project_combo.setCurrentText(text)
            self.tab1_glossary_combo.addItem(text)
            self.test_combo.addItem(text)

    def load_glossary_table(self):
        """โหลดข้อมูล Glossary ลงตารางซ้าย"""
        self.is_loading = True
        self.glossary_table.setRowCount(0)
        glossary_dict = get_all_glossary(self.current_db)
        
        for row, (en, th) in enumerate(glossary_dict.items()):
            self.glossary_table.insertRow(row)
            
            # เก็บคำอังกฤษต้นฉบับไว้ใน UserRole เพื่อใช้เช็คตอน User แก้ไขคำ
            en_item = QTableWidgetItem(en)
            en_item.setData(Qt.ItemDataRole.UserRole, en) 
            self.glossary_table.setItem(row, 0, en_item)
            self.glossary_table.setItem(row, 1, QTableWidgetItem(th))
            
            del_btn = QPushButton("delete")
            del_btn.setStyleSheet("color: red;")
            del_btn.clicked.connect(lambda checked, term=en: self.delete_term_inline(term))
            self.glossary_table.setCellWidget(row, 2, del_btn)
        self.is_loading = False

    def add_glossary_ui(self):
        """ปุ่ม Add สำหรับ Glossary"""
        en = self.en_in.text().strip()
        th = self.th_in.text().strip()
        if en and th:
            add_glossary(en, th, self.current_db)
            self.load_glossary_table()
            self.en_in.clear()
            self.th_in.clear()
            self.en_in.setFocus()

    def delete_term_inline(self, en_term):
        """ลบคำศัพท์จากการกดปุ่มในแถว"""
        reply = QMessageBox.question(self, 'Confirm Delete', 
                                     f"Are you sure you want to delete '{en_term}'\nfrom {self.current_db}?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            delete_glossary(en_term, self.current_db)
            self.load_all_data() # โหลดใหม่ทั้งหมด
            # ถ้ามีคำค้นหาค้างอยู่ ให้กรองตารางใหม่
            if self.search_input.text():
                self.filter_all_tables(self.search_input.text())

# บรรทัดสุดท้ายของไฟล์ยังคงเป็น:
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AILocalizerUI()
    window.show()
    sys.exit(app.exec())
