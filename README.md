# AI-Based Contract Intelligence System

Production-oriented Flask foundation for an AI contract analysis platform.

## Module 1: Authentication

Included:

- Login, registration, logout
- Flask-Login session management
- Password hashing with Werkzeug
- Route protection for `/dashboard`
- SQLAlchemy `User` model
- CSRF token checks for auth forms
- Flash messages and validation
- Responsive Bootstrap 5 UI
- Clean folders ready for upload, AI, RAG, compliance, timeline, and negotiation modules

## Folder Structure

```text
Contract-Intelligence-System/
app.py
config.py
requirements.txt
README.md
database/
database/schema.sql
logs/
models/
    __init__.py
    contract.py
    user.py
routes/
    __init__.py
    auth.py
    modules.py
services/
    __init__.py
    auth_service.py
    contract_analysis_service.py
    document_service.py
    gemini_contract_service.py
ai/
    __init__.py
utils/
    __init__.py
    security.py
    validators.py
static/
    css/styles.css
    js/main.js
    images/
    uploads/
templates/
    app_shell.html
    base.html
    index.html
    login.html
    register.html
    dashboard.html
    upload.html
    summary.html
    risk.html
    alerts.html
    timeline.html
    compliance.html
    negotiation.html
    chatbot.html
```

## Database Schema

The Module 1 schema is documented in `database/schema.sql`. At runtime, Flask-SQLAlchemy creates the SQLite database at `database/contracts.db`.

## Installation Steps

1. Create and activate a virtual environment.

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. Set a secure secret key for production.

```powershell
$env:SECRET_KEY="replace-with-a-long-random-secret"
```

4. Set your Gemini API key.

```powershell
$env:GEMINI_API_KEY="your-google-gemini-api-key"
```

Optional model override:

```powershell
$env:GEMINI_MODEL="gemini-3.5-flash"
```

5. Run the application.

```powershell
python app.py
```

6. Open `http://127.0.0.1:5000`.

## Contract Upload Analysis

After a PDF upload, the app now:

- stores the uploaded PDF under `static/uploads`
- extracts text with `pdfplumber`, falling back to `PyPDF2`
- sends the extracted text to Gemini
- saves the structured analysis in the `contracts` table
- displays executive summary, agreement type, key parties, business purpose, effective date, expiry date, and contract value on `/summary`

## Future Module Integration

Future modules should add protected route blueprints and service classes without modifying the authentication flow. Use `@login_required` on user-only views and attach uploaded contracts to `current_user.id`.

## Navigation Routes

The authenticated sidebar is defined once in `templates/app_shell.html`. All module pages extend that layout and are served by `routes/modules.py`:

- `/dashboard`
- `/upload`
- `/summary`
- `/risk`
- `/alerts`
- `/timeline`
- `/compliance`
- `/negotiation`
- `/chatbot`
