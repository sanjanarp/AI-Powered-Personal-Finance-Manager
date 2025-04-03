# AI-Powered Personal Finance Manager

This is a Streamlit-based web application that helps users manage their finances by analyzing bank statements and providing personalized financial insights using OpenAI's GPT API.

---

## ⚙️ Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/sanjanarp/AI-Powered-Personal-Finance-Manager
cd AI-Powered-Personal-Finance-Manager
```

### 2. Create Virtual Environment (optional but recommended)
```bash
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # macOS/Linux
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Backend
Navigate to the `backend` folder and start the Flask server:
```bash
cd backend
python app.py
```

### 5. Run the Frontend
In a new terminal, navigate to the `frontend` folder and start the Streamlit app:
```bash
cd frontend
streamlit run app.py
```

---

## 🛠️ Usage
1. Open the Streamlit app in your browser (usually at `http://localhost:8501`).
2. Upload your bank statement PDFs.
3. Enter your OpenAI API key.
4. Analyze your statements and view the financial insights.

---
