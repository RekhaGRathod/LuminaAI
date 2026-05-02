import os
import pandas as pd
import chromadb
import uuid
import re
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'chroma_db')

# Import curriculum to get topic list
import sys
sys.path.append(BASE_DIR)
from data.topics import TOPICS_DATA

# Extract all topic titles for AI reference
TOPIC_LISTS = {}
for chapter_id, topics in TOPICS_DATA.items():
    subject = chapter_id.split('-')[0]
    if subject not in TOPIC_LISTS:
        TOPIC_LISTS[subject] = []
    for t in topics:
        TOPIC_LISTS[subject].append(t['title'])

# Initialize ChromaDB client
client = chromadb.PersistentClient(path=DB_PATH)
try:
    client.delete_collection(name="neet_questions")
except:
    pass
collection = client.get_or_create_collection(name="neet_questions")

def call_gemini_for_topic(question_text, subject):
    """Use Gemini to map a question to a topic title from our curriculum"""
    possible_topics = TOPIC_LISTS.get(subject, [])
    if not possible_topics:
        return "General"
    
    prompt = f"""
    Map the following NEET {subject} question to the MOST relevant topic from this list:
    {", ".join(possible_topics)}
    
    Question: {question_text}
    
    Output ONLY the exact topic title from the list.
    """
    try:
        headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1}
        }
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        print(f"Gemini topic error: {e}")
    return possible_topics[0]

def clean_text(text):
    if not text or text == 'nan':
        return ""
    # Remove LaTeX and formatting
    text = re.sub(r'\\subsection\*\{.*?\}', '', text)
    text = re.sub(r'\\textbf\{(.*?)\}', r'\1', text)
    text = re.sub(r'\\textit\{(.*?)\}', r'\1', text)
    text = re.sub(r'\\begin\{itemize\}|\\end\{itemize\}|\\item', '', text)
    text = re.sub(r'\\begin\{align\*\}|\\end\{align\*\}|\\\[|\\\]|\\\(|\\\)', '', text)
    text = re.sub(r'\$', '', text)
    text = re.sub(r'\\quad', ' ', text)
    text = re.sub(r'\\text\{(.*?)\}', r'\1', text)
    text = re.sub(r'\\frac\{(.*?)\}\{(.*?)\}', r'\1/\2', text)
    text = re.sub(r'\\times', 'x', text)
    text = re.sub(r'\\rightarrow', '->', text)
    text = re.sub(r'\\{2,}', '\n', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def ingest_file(filepath, subject):
    print(f"Ingesting {filepath}...")
    try:
        df = pd.read_excel(filepath)
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return

    if 'Topic' in df.columns:
        df['Topic'] = df['Topic'].ffill()
    if 'Subtopic' in df.columns:
        df['Subtopic'] = df['Subtopic'].ffill()

    ids = []
    documents = []
    metadatas = []
    current_q = None

    for index, row in df.iterrows():
        q_text = str(row.get('Question/Prompt', ''))
        
        if q_text and q_text != 'nan' and q_text.strip():
            if current_q:
                add_question_to_batch(current_q, ids, documents, metadatas, subject)
            
            topic = str(row.get('Topic', '')).strip()
            # If topic is missing, use AI to map it
            if not topic or topic == 'nan':
                print(f"Mapping question {index} using AI...")
                topic = call_gemini_for_topic(q_text, subject)
            
            current_q = {
                "question": q_text.strip(),
                "topic": topic,
                "subtopic": str(row.get('Subtopic', '')).strip(),
                "correct_answer": str(row.get('Correct Answer', '')).strip(),
                "solution": str(row.get('Step-by-step Solution', '')).strip(),
                "difficulty": str(row.get('Difficulty Level', 'Medium')).strip()
            }
        else:
            if current_q:
                sol_part = str(row.get('Step-by-step Solution', ''))
                if sol_part and sol_part != 'nan' and sol_part.strip():
                    current_q["solution"] += "\n" + sol_part.strip()
    
    if current_q:
        add_question_to_batch(current_q, ids, documents, metadatas, subject)

    if ids:
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            collection.add(
                ids=ids[i:i+batch_size],
                documents=documents[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size]
            )
        print(f"Added {len(ids)} questions for {subject}.")

def add_question_to_batch(q, ids, documents, metadatas, subject):
    question_id = str(uuid.uuid4())
    q_clean = clean_text(q['question'])
    sol_clean = clean_text(q['solution'])
    ans_clean = clean_text(q['correct_answer'])
    
    doc_text = f"Subject: {subject}\nTopic: {q['topic']}\nQuestion: {q_clean}"
    
    ids.append(question_id)
    documents.append(doc_text)
    metadatas.append({
        "subject": subject,
        "topic": q["topic"],
        "subtopic": q["subtopic"],
        "question": q_clean,
        "correct_answer": ans_clean,
        "solution": sol_clean,
        "difficulty": q["difficulty"]
    })

if __name__ == "__main__":
    excel_dir = os.path.join(BASE_DIR, '..')
    files = [
        (os.path.join(excel_dir, "NEET-Biology.xlsx"), "biology"),
        (os.path.join(excel_dir, "NEET-Chemistry.xlsx"), "chemistry"),
        (os.path.join(excel_dir, "NEET-Physics.xlsx"), "physics")
    ]
    
    for f_path, subject in files:
        if os.path.exists(f_path):
            ingest_file(f_path, subject)
        else:
            print(f"File not found: {f_path}")
            
    print("Ingestion complete!")
