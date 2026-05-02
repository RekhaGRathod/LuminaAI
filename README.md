# ConceptCracker: AI-Powered NEET Preparation Platform

![Banner](assets/banner.png)

ConceptCracker is a state-of-the-art educational platform designed to help NEET (National Eligibility cum Entrance Test) aspirants master Physics, Chemistry, and Biology. By combining a curated textbook dataset with cutting-edge AI (Groq & Gemini), it provides instant solutions, smart question retrieval, and personalized doubt resolution.

## 🚀 Key Features

- **RAG-Powered Question Bank:** Retrieves 1,800+ real textbook questions using ChromaDB Vector Search.
- **Ultra-Fast AI Tutor:** Integrated with **Groq (Llama 3)** for nearly instant step-by-step solutions and doubt clearing.
- **Smart Ingestion:** Automatically categorizes messy Excel data into the correct curriculum topics using AI-powered mapping.
- **Premium UI:** A modern, glassmorphic dashboard with dark mode, interactive quizzes, and pedagogical feedback.
- **Latex-Free Clarity:** Sophisticated text cleaning ensures all scientific formulas are presented clearly and professionally.

## 🛠️ Technology Stack

- **Backend:** Flask (Python)
- **Database:** ChromaDB (Vector Store)
- **AI Engines:** Groq API (Primary), Google Gemini 1.5 Flash (Fallback)
- **Data Processing:** Pandas, OpenPyXL
- **Frontend:** Vanilla JS, CSS3 (Glassmorphism), HTML5

## 📋 Installation & Setup

### 1. Prerequisites
- Python 3.8+
- Groq API Key & Gemini API Key

### 2. Clone the Repository
```bash
git clone https://github.com/yourusername/conceptcracker.git
cd conceptcracker
```

### 3. Setup Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configuration
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
```

### 5. Data Ingestion
Run the smart ingestion script to populate the vector database:
```bash
python smart_ingest.py
```

### 6. Run the Application
```bash
python app.py
```
Open `http://127.0.0.1:5000` in your browser.

## 📁 Repository Structure

- `app.py`: Main Flask application logic and AI integration.
- `smart_ingest.py`: AI-powered script to clean and index Excel datasets.
- `data/`: Contains the curriculum structure (subjects, chapters, topics).
- `static/`: Frontend assets (CSS, JS, Images).
- `templates/`: HTML templates.
- `requirements.txt`: Python dependencies.

## 📄 License
This project is for educational purposes. All textbook data is owned by their respective publishers.
