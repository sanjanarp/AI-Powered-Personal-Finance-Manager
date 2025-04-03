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

> **Note:** This project uses `openai` version `0.27.8`. Ensure that this version is installed to avoid compatibility issues.

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

## 🧪 Running Tests

### 1. Set the `PYTHONPATH`
Before running the tests, ensure the `PYTHONPATH` is set to the project root directory. On Windows, run:
```bash
set PYTHONPATH=.
```

### 2. Run All Tests
To run all tests, use the following command:
```bash
python run_tests.py
```

### 3. Run Tests with Coverage
To run the tests and measure code coverage, use the following command:
```bash
coverage run --source=backend,frontend run_tests.py
```

### 4. View Coverage Report
To view the coverage report in the terminal:
```bash
coverage report
```

To generate an HTML coverage report:
```bash
coverage html
```
Open the `htmlcov/index.html` file in your browser to view a detailed coverage report.

---

## 🛠️ Usage
1. Open the Streamlit app in your browser (usually at `http://localhost:8501`).
2. Upload your bank statement PDFs.
3. Enter your OpenAI API key.
4. Analyze your statements and view the financial insights.

---

## 🧪 Current Test Coverage
- **Backend**:
  - `app.py`: 88%
  - `routes/advice.py`: 66%
  - `routes/analyze.py`: 83%
  - `utils/openai_utils.py`: 56%
  - `utils/pdf_utils.py`: 53%
  - `utils/token_utils.py`: 100%
- **Frontend**:
  - `app.py`: 0%

> **Note:** Some tests are failing due to issues with mocked dependencies or invalid test data. Refer to the test logs for details.
