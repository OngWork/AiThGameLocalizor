from llama_cpp import Llama
import sys
import os

def get_base_path():
    """หาที่อยู่ของโฟลเดอร์หลักของโปรแกรม ไม่ว่าจะรันด้วย Python หรือ .exe"""
    if getattr(sys, 'frozen', False):
        # ถ้าเป็น .exe ให้หาโฟลเดอร์ที่ .exe ตัวนั้นวางอยู่
        return os.path.dirname(sys.executable)
    # ถ้าเป็น .py ปกติ ให้หาโฟลเดอร์ปัจจุบัน
    return os.path.dirname(os.path.abspath(__file__))

base_dir = get_base_path()
MODEL_PATH = os.path.join(base_dir, "models", "Translator_v9_Typhoon_Q4_K_M.gguf")

print("Connect to AI model...")
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=2048,          
    n_gpu_layers=-1,     
    verbose=False        
)
print("Connect to AI model successfully")

def translate_text(context, input_text):
    # ลบ <|begin_of_text|> ออกไปแล้ว เพื่อไม่ให้ซ้ำซ้อน
    prompt_template = f"""<|start_header_id|>user<|end_header_id|>

Translate this game text from English to Thai. Keep variables like {{v0}}, {{v1}}, {{name}} unchanged.
CRITICAL RULE: If a Glossary term says "(Keep English)", you MUST output that exact English word without translating or transliterating it.
Context: {context}
Input: {input_text}<|eot_id|><|start_header_id|>assistant<|end_header_id|>

"""
    output = llm(
        prompt_template,
        max_tokens=256,
        temperature=0.1,    
        top_p=0.9,
        stop=["<|eot_id|>"] 
    )
    
    return output['choices'][0]['text'].strip()

# ==========================================
if __name__ == "__main__":
    test_context = "Tone: Fantasy. Pronouns: 'ผม' (Male). Glossary: Mondstadt = Mondstadt (Keep English)"
    test_input = "Welcome back! How was your journey to Mondstadt?"
    
    print("-" * 40)
    print(f"Context: {test_context}")
    print(f"Input:   {test_input}")
    print("กำลังแปลผล...")
    
    result = translate_text(test_context, test_input)
    
    print(f"Output:  {result}")
    print("-" * 40)
    
    # วิธีแก้บั๊ก Error สีแดงตอนจบโปรแกรม
    del llm