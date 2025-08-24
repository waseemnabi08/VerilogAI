# VerilogAI

VerilogAI is a web-based, AI-powered chat application designed to assist hardware designers and students with Verilog and SystemVerilog development. It provides a user-friendly interface to generate, debug, and understand HDL code, leveraging the power of Google's Gemini API.

## Features

- **AI-Powered Chat**: Engage in a conversation with an AI assistant that understands the nuances of hardware design.
- **Code Generation**: Describe a module in natural language, and VerilogAI will generate synthesizable Verilog-2001 code.
- **Debugging**: Paste your Verilog code to get a detailed analysis of potential issues, including syntax errors, latch inference, and non-synthesizable constructs, along with a corrected version of the code.
- **Code Explanation**: Get a clear, step-by-step explanation of your Verilog code, perfect for learners.
- **Chat History**: Your conversation is saved in your browser's local storage, so you can pick up where you left off.
- **Responsive Design**: The user interface is designed to work on both desktop and mobile devices.

## Features

- **AI-Powered Chat**: Chat with an AI assistant knowledgeable in hardware design.
- **Code Generation**: Generate synthesizable Verilog-2001 code from natural language descriptions.
- **Debugging**: Analyze and correct Verilog code for syntax errors, latch inference, and non-synthesizable constructs.
- **Code Explanation**: Get step-by-step explanations of your Verilog code.
- **Chat History**: Conversations are saved in your browser's local storage.
- **Responsive Design**: Works on desktop and mobile devices.

## Technologies Used

### Backend

- **Python**: The core language for the backend server.
- **FastAPI**: A modern, fast (high-performance) web framework for building APIs with Python.
- **Uvicorn**: An ASGI server for running the FastAPI application.
- **Gemini API**: The AI model from Google that powers the chat, generation, debugging, and explanation features.
- **python-dotenv**: For managing environment variables.

### Backend
- **Python**: Backend language.
- **FastAPI**: Web framework for APIs.
- **Uvicorn**: ASGI server for FastAPI.
- **Gemini API**: Google's AI model for chat, generation, debugging, and explanation.
- **python-dotenv**: For environment variable management.

### Frontend

- **HTML, CSS, JavaScript**: The standard trio for building the web interface.
- **Vite**: A fast build tool for modern web development, used for serving the frontend.
- **Marked.js**: A library for parsing and rendering Markdown in the chat messages.
- **Font Awesome**: For icons used throughout the user interface.

### Frontend
- **HTML, CSS, JavaScript**: Web interface.
- **Vite**: Modern frontend build tool.
- **Marked.js**: Markdown rendering in chat.
- **Font Awesome**: UI icons.

## Setup and Installation

### Prerequisites

- Python 3.7+
- Node.js and npm (or a compatible package manager)

### Prerequisites
- Python 3.7+
- Node.js and npm

### 1. Clone the Repository

```bash
git clone https://github.com/waseemnabi08/VerilogAI.git
cd VerilogAI
```

### 1. Clone the Repository
```bash
git clone https://github.com/waseemnabi08/VerilogAI.git
cd VerilogAI
```

### 2. Backend Setup

1.  **Create and activate a virtual environment:**

    ```bash
    # For Windows
    python -m venv .venv
    .venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install Python dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up your Gemini API key:**

    Create a `.env` file in the root of the project and add your Gemini API key:

    ```
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    ```

### 2. Backend Setup
1. **Create and activate a virtual environment:**
    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate
    # macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```
2. **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3. **Set up your Gemini API key:**
    Create a `.env` file in the root of the project and add:
    ```env
    GEMINI_API_KEY=your_gemini_api_key_here
    ```

### 3. Frontend Setup

1.  **Navigate to the frontend directory:**

    ```bash
    cd frontend
    ```

### 3. Frontend Setup
1. **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```
2. **Install Node.js dependencies:**
    ```bash
    npm install
    ```

2.  **Install Node.js dependencies:**

    ```bash
    npm install
    ```

## Usage

1.  **Start the backend server:**

    Make sure you are in the root directory of the project (`VerilogAI/`) and your virtual environment is activated.

    ```bash
    uvicorn main:app --reload
    ```

    The backend server will be running at `http://127.0.0.1:8000`.

2.  **Start the frontend development server:**

    In a new terminal, navigate to the `frontend` directory.

    ```bash
    cd frontend
    npm run dev
    ```

    The frontend will be accessible at `http://localhost:5173` (or another port if 5173 is in use).

3.  **Open your browser and navigate to the frontend URL.**

    You can now start chatting with VerilogAI!

## Usage
1. **Start the backend server:**
    In the root directory (`VerilogAI/`), with your virtual environment activated:
    ```bash
    uvicorn main:app --reload
    ```
    The backend server runs at `http://127.0.0.1:8000`.
2. **Start the frontend development server:**
    In a new terminal, navigate to the `frontend` directory:
    ```bash
    cd frontend
    npm run dev
    ```
    The frontend will be accessible at `http://localhost:5173`.
3. **Open your browser and navigate to the frontend URL.**
    You can now start chatting with VerilogAI!

## Project Structure

```
VerilogAI/
├── .gitignore
├── main.py             # FastAPI backend server
├── README.md
├── requirements.txt    # Python dependencies
├── frontend/
│   ├── index.html      # Main HTML file
│   ├── script.js       # Frontend JavaScript logic
│   ├── style.css       # Frontend styles
│   ├── package.json    # Frontend dependencies and scripts
│   └── vite.config.js  # Vite configuration
└── .venv/              # Python virtual environment
```

## Project Structure
```
VerilogAI/
├── .gitignore
├── main.py             # FastAPI backend server
├── README.md
├── requirements.txt    # Python dependencies
├── frontend/
│   ├── index.html      # Main HTML file
│   ├── script.js       # Frontend JavaScript logic
│   ├── style.css       # Frontend styles
│   ├── package.json    # Frontend dependencies and scripts
│   └── vite.config.js  # Vite configuration
└── .venv/              # Python virtual environment
```