from flask import Flask, request, jsonify, render_template, url_for
import json
import uuid
import os
import requests
import random
from dotenv import load_dotenv

# Import data from separate files
from data.subjects import SUBJECTS_DATA
from data.chapters import CHAPTERS_DATA
from data.topics import TOPICS_DATA

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Cache for generated questions
QUESTION_CACHE = {}

# Get Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/subjects', methods=['GET'])
def get_subjects():
    return jsonify({
        "subjects": [{"id": key, "name": value["name"], "course": value["course"]} for key, value in SUBJECTS_DATA.items()]
    })

@app.route('/api/chapters', methods=['POST'])
def get_chapters():
    data = request.json
    subject = data.get('subject')
    course = data.get('course', 'all')  # Default to 'all' if not specified
    
    # Determine which chapter data to use
    if subject not in SUBJECTS_DATA:
        return jsonify({"error": "Subject not found"}), 404
    
    # Get chapters from the appropriate subject and course
    chapter_key = f"{subject}_{course}" if course != 'all' else subject
    
    if chapter_key in CHAPTERS_DATA:
        chapters = CHAPTERS_DATA[chapter_key]
    else:
        # If specific course not found, return all chapters for the subject
        chapters = []
        for key, value in CHAPTERS_DATA.items():
            if key.startswith(subject):
                chapters.extend(value)
    
    return jsonify({
        "chapters": chapters
    })

@app.route('/api/topics', methods=['POST'])
def get_topics():
    data = request.json
    chapter_id = data.get('chapter')
    
    if chapter_id not in TOPICS_DATA:
        # Return empty list if no topics are defined for this chapter
        return jsonify({
            "topics": []
        })
    
    topics = TOPICS_DATA[chapter_id]
    
    return jsonify({
        "topics": topics
    })

@app.route('/api/questions', methods=['POST'])
def get_questions():
    data = request.json
    subject = data.get('subject')
    chapter = data.get('chapter')
    topic = data.get('topic')
    offset = data.get('offset', 0)
    limit = data.get('limit', 5)  # Default to 5 questions per request, but allow overriding
    history = set(data.get('history', []))
    
    # Check if we have cached questions for this topic
    cache_key = f"{subject}-{chapter}-{topic}"
    
    if cache_key not in QUESTION_CACHE:
        # Generate questions using Gemini API - no longer limited to a specific count
        # The API might have its own limits, but we're not enforcing a hard limit here
        questions = generate_questions_with_gemini(subject, chapter, topic, 20)  # Start with 20, can be extended
        QUESTION_CACHE[cache_key] = questions
    
    # Get cached questions
    all_questions = QUESTION_CACHE[cache_key]
    
    # Filter out questions that have already been shown
    available_questions = [q for q in all_questions if q["id"] not in history]
    
    # If we're running low on questions, generate more
    if len(available_questions) < limit + offset:
        new_questions = generate_questions_with_gemini(subject, chapter, topic, 10)
        # Add only new questions that aren't already in the cache
        new_question_ids = {q["id"] for q in all_questions}
        for q in new_questions:
            if q["id"] not in new_question_ids:
                all_questions.append(q)
                if q["id"] not in history:
                    available_questions.append(q)
        
        # Update the cache
        QUESTION_CACHE[cache_key] = all_questions
    
    # Get the requested batch
    start_idx = offset
    end_idx = min(start_idx + limit, len(available_questions))
    
    questions_batch = available_questions[start_idx:end_idx]
    
    return jsonify({
        "questions": questions_batch,
        "hasMore": end_idx < len(available_questions)
    })

@app.route('/api/custom-questions', methods=['POST'])
def get_custom_questions():
    data = request.json
    topic = data.get('topic')
    offset = data.get('offset', 0)
    limit = data.get('limit', 5)  # Default to 5 questions per request
    history = set(data.get('history', []))
    
    # Check if we have cached questions for this custom topic
    cache_key = f"custom-{topic}"
    
    if cache_key not in QUESTION_CACHE:
        # Generate questions using Gemini API
        questions = generate_custom_questions_with_gemini(topic, 20)  # Start with 20
        QUESTION_CACHE[cache_key] = questions
    
    # Get cached questions
    all_questions = QUESTION_CACHE[cache_key]
    
    # Filter out questions that have already been shown
    available_questions = [q for q in all_questions if q["id"] not in history]
    
    # If we're running low on questions, generate more
    if len(available_questions) < limit + offset:
        new_questions = generate_custom_questions_with_gemini(topic, 10)
        # Add only new questions that aren't already in the cache
        new_question_ids = {q["id"] for q in all_questions}
        for q in new_questions:
            if q["id"] not in new_question_ids:
                all_questions.append(q)
                if q["id"] not in history:
                    available_questions.append(q)
        
        # Update the cache
        QUESTION_CACHE[cache_key] = all_questions
    
    # Get the requested batch
    start_idx = offset
    end_idx = min(start_idx + limit, len(available_questions))
    
    questions_batch = available_questions[start_idx:end_idx]
    
    return jsonify({
        "questions": questions_batch,
        "hasMore": end_idx < len(available_questions)
    })

@app.route('/api/solution', methods=['POST'])
def get_solution():
    data = request.json
    question_id = data.get('questionId')
    
    # Find the question across all caches
    question = None
    for questions in QUESTION_CACHE.values():
        for q in questions:
            if q["id"] == question_id:
                question = q
                break
        if question:
            break
    
    if not question:
        return jsonify({"error": "Question not found"}), 404
    
    # Generate solution with Gemini if not already included
    if "solution" not in question:
        question["solution"] = generate_solution_with_gemini(question)
    
    return jsonify({
        "question": question,
        "solution": question["solution"]
    })

@app.route('/api/ask-doubt', methods=['POST'])
def ask_doubt():
    data = request.json
    question_text = data.get('question')
    doubt_text = data.get('doubt')
    
    # Generate response with Gemini
    response = generate_doubt_response_with_gemini(question_text, doubt_text)
    
    return jsonify({
        "response": response
    })

# Gemini API Integration
def generate_questions_with_gemini(subject, chapter, topic, count=20):
    # Find the topic name from our data structure
    topic_name = ""
    chapter_name = ""
    
    # Find the chapter name
    for subject_key, chapters_list in CHAPTERS_DATA.items():
        if subject_key.startswith(subject):
            for ch in chapters_list:
                if ch["id"] == chapter:
                    chapter_name = ch["title"]
                    break
            if chapter_name:
                break
    
    # Find the topic name
    if chapter in TOPICS_DATA:
        for t in TOPICS_DATA[chapter]:
            if t["id"] == topic:
                topic_name = t["title"]
                break
    
    # Fallback if not found
    if not topic_name:
        topic_name = topic
    
    prompt = f"""
    Generate {count} multiple-choice questions for NEET exam preparation on the topic "{topic_name}" 
    from the chapter "{chapter_name}" in {subject.capitalize()}.
    
    Each question should:
    1. Be challenging but appropriate for NEET level
    2. Have 4 options (A, B, C, D)
    3. One correct answer
    4. Be formatted in JSON as shown in the example below
    
    Example format:
    [
      {{
        "id": "unique-id-1",
        "text": "Question text here?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correctIndex": 2,
        "explanation": "Brief explanation of why option C is correct"
      }}
    ]
    
    Return only the JSON array with {count} questions, no other text.
    """
    
    try:
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        }
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.8,
                "topK": 40
            }
        }
        
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()  # Raise an error for bad responses
        
        response_json = response.json()
        generated_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
        
        # Extract JSON from the response (in case there's any extra text)
        import re
        json_match = re.search(r'\[.*\]', generated_text, re.DOTALL)
        if json_match:
            generated_text = json_match.group(0)
            
        questions = json.loads(generated_text)
        
        # Ensure each question has a unique ID
        for i, question in enumerate(questions):
            if "id" not in question or not question["id"]:
                question["id"] = str(uuid.uuid4())
                
        return questions
        
    except Exception as e:
        print(f"Error generating questions with Gemini: {e}")
        # Fallback to dummy questions in case of API failure
        return generate_dummy_questions(subject, chapter, topic, count)

def generate_custom_questions_with_gemini(topic, count=20):
    prompt = f"""
    Generate {count} multiple-choice questions for NEET exam preparation on the topic "{topic}".
    
    Each question should:
    1. Be challenging but appropriate for NEET level
    2. Have 4 options (A, B, C, D)
    3. One correct answer
    4. Be formatted in JSON as shown in the example below
    
    Example format:
    [
      {{
        "id": "unique-id-1",
        "text": "Question text here?",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correctIndex": 2,
        "explanation": "Brief explanation of why option C is correct"
      }}
    ]
    
    Return only the JSON array with {count} questions, no other text.
    """
    
    try:
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        }
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.8,
                "topK": 40
            }
        }
        
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        response_json = response.json()
        generated_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
        
        # Extract JSON from the response
        import re
        json_match = re.search(r'\[.*\]', generated_text, re.DOTALL)
        if json_match:
            generated_text = json_match.group(0)
            
        questions = json.loads(generated_text)
        
        # Ensure each question has a unique ID
        for i, question in enumerate(questions):
            if "id" not in question or not question["id"]:
                question["id"] = str(uuid.uuid4())
                
        return questions
        
    except Exception as e:
        print(f"Error generating custom questions with Gemini: {e}")
        # Fallback to dummy questions
        return generate_dummy_questions("custom", "custom", topic, count)

def generate_solution_with_gemini(question):
    prompt = f"""
    Generate a detailed step-by-step solution for the following NEET exam question:
    
    Question: {question['text']}
    Options:
    A. {question['options'][0]}
    B. {question['options'][1]}
    C. {question['options'][2]}
    D. {question['options'][3]}
    
    Correct Answer: {chr(65 + question['correctIndex'])}. {question['options'][question['correctIndex']]}
    
    Explanation: {question.get('explanation', '')}
    
    Please provide a detailed solution in the following JSON format:
    
    {{
      "steps": [
        {{
          "title": "Understanding the Question",
          "content": "Explanation of the question and what it's asking for..."
        }},
        {{
          "title": "Key Concept",
          "content": "Explanation of the relevant concept or formula..."
        }},
        {{
          "title": "Application",
          "content": "How to apply the concept to this specific problem..."
        }},
        {{
          "title": "Calculation",
          "content": "Any calculations or logical steps to arrive at the answer..."
        }},
        {{
          "title": "Verification",
          "content": "Verify the answer and why the other options are incorrect..."
        }}
      ]
    }}
    
    Return only the JSON, no other text.
    """
    
    try:
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        }
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "topP": 0.8,
                "topK": 40
            }
        }
        
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        response_json = response.json()
        generated_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
        
        # Extract JSON from the response
        import re
        json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
        if json_match:
            generated_text = json_match.group(0)
            
        solution = json.loads(generated_text)
        return solution
        
    except Exception as e:
        print(f"Error generating solution with Gemini: {e}")
        # Fallback to dummy solution
        return {
            "steps": [
                {
                    "title": "Understanding the Question",
                    "content": "The question is asking about " + question['text']
                },
                {
                    "title": "Key Concept",
                    "content": "This involves understanding basic principles."
                },
                {
                    "title": "Solution",
                    "content": "The correct answer is " + question['options'][question['correctIndex']] + " because " + (question.get('explanation', 'it follows from the principles described above.'))
                }
            ]
        }

def generate_doubt_response_with_gemini(question_text, doubt_text):
    prompt = f"""
    I need help clarifying a doubt about a NEET exam question.
    
    Original Question: {question_text}
    
    My Doubt: {doubt_text}
    
    Please provide a detailed, helpful explanation that clarifies this doubt. Explain any underlying concepts, principles, or formulae that are necessary to understand the solution. Use clear language appropriate for a NEET student.
    """
    
    try:
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        }
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.8,
                "topK": 40
            }
        }
        
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        response_json = response.json()
        generated_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
        
        return generated_text
        
    except Exception as e:
        print(f"Error generating doubt response with Gemini: {e}")
        return f"I apologize, but I couldn't process your doubt at the moment. Your doubt was: {doubt_text}. Please try rephrasing or asking again later."

# Fallback function for generating dummy questions
def generate_dummy_questions(subject, chapter, topic, count=20):
    questions = []
    for i in range(count):
        questions.append({
            "id": str(uuid.uuid4()),
            "text": f"Sample question {i+1} about {topic} in {chapter} for {subject}?",
            "options": [
                f"Option A for question {i+1}",
                f"Option B for question {i+1}",
                f"Option C for question {i+1}",
                f"Option D for question {i+1}"
            ],
            "correctIndex": random.randint(0, 3),
            "explanation": f"This is an explanation for sample question {i+1}"
        })
    return questions

if __name__ == '__main__':
    app.run(debug=True)