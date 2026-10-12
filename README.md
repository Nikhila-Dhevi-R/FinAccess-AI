# FinAccess AI

FinAccess AI is a ## voice first financial inclusion platform for people in India who may face difficulty reading, typing, completing official forms, understanding government schemes, or identifying financial fraud. The application combines a multilingual browser experience with a FastAPI service for form processing, scheme discovery, financial guidance, and fraud analysis.

The primary experience supports English, Hindi, and Tamil. Users can speak to the application through the browser microphone or enter text when speech input is unavailable.

## Problem statement

Many banking, pension, ration card, and welfare services require users to read complex forms, understand unfamiliar terminology, and navigate several steps without assistance. Elderly users, people with low literacy, and users who are more comfortable in regional languages can be excluded by these interfaces.

Financial scams create a related problem. A suspicious message, image, link, or request for sensitive information can be difficult to evaluate quickly. Users also need a simple way to discover government schemes that match their needs and understand how to apply.

## Objective

1. Let users complete supported forms by speaking or typing answers.
2. Provide a clear experience in English, Hindi, and Tamil.
3. Extract fields from uploaded PDF documents and scanned images.
4. Use a randomized four digit challenge during form completion as an anti spoofing check.
5. Show the challenge after every third answered question and before final form submission.
6. Help users discover welfare schemes using eligibility information.
7. Answer banking and financial questions through a conversational guidance page.
8. Check message text and uploaded message images for common fraud patterns.
9. Generate a completed PDF that the user can download after review.

## System architecture

<img width="11769" height="9935" alt="diagram (1)" src="https://github.com/user-attachments/assets/5999fc55-0b01-4974-a2c6-abe0ee9f47a7" />


The system is organized into the following layers.

| Layer | Responsibility | Main implementation |
| --- | --- | --- |
| Browser experience | Provides navigation, multilingual text, voice controls, form review, scheme cards, guidance, and fraud results | React, React Router, browser SpeechRecognition, browser speech synthesis |
| API layer | Receives sessions, form files, answers, challenge responses, scheme queries, guidance questions, and fraud checks | FastAPI with versioned routes under `/api/v1` |
| Domain services | Handles form field extraction, language mapping, scheme matching, guidance responses, fraud classification, OCR, PDF generation, and randomized challenges | Python modules in `backend/services` |
| Persistence | Stores sessions, uploaded form metadata, fields, answers, challenge state, and fraud checks | SQLAlchemy with SQLite |
| File processing | Reads PDF and image forms, extracts text and layout information, and writes completed PDFs | PyMuPDF, pypdf, Pillow, pytesseract, ReportLab |
| Configuration adapters | Allows speech, text to speech, translation, OCR, and language model providers to be selected through settings | `backend/config.py` with stub, Whisper, Bhashini, Google, OpenAI, and Gemini options |

### Request flow

1. The browser creates a session and records the selected language.
2. The user selects a feature such as form filling, schemes, guidance, or fraud checking.
3. The browser sends a request to the FastAPI service through Axios.
4. The matching router validates the request and calls a domain service.
5. The service reads or updates SQLite records and uses local processing utilities when needed.
6. The API returns structured data that the browser presents with voice and text support.

## Main workflows

### Voice form filling

1. The user opens Form Fill and uploads a bank, pension, ration card, or government form as a PDF or image.
2. The backend extracts likely field labels and layout coordinates.
3. The user answers each question by voice or by typing.
4. The user can repeat a question, go back, update an answer, or skip a field.
5. After every third answered question, the application presents a randomized four digit phrase challenge.
6. The user repeats the four digits by voice or by typing within 30 seconds.
7. After review, a final randomized challenge is required before the completed PDF is generated.
8. The completed document is available through the form download endpoint.

The current flow does not use Twilio, OTP delivery, or mobile number verification. Form filling begins directly after the user selects the feature and uploads a document.

### Government schemes

The Schemes page provides grouped scheme information, filters, search, scheme details, and profile based matching. Results include benefit summaries, eligibility explanations, application steps, and a status that indicates when more information is needed.

### Financial guidance

The Guidance page accepts spoken or typed questions. Conversation history and context are sent with each request so that short follow up answers can be understood in context.

### Fraud checking

The Fraud Check page accepts message text or a photo of a message. The backend can run OCR on an uploaded image and checks for patterns such as fake KYC requests, phishing links, lottery claims, impersonation, and requests for sensitive information.

## Technology stack

| Area | Technologies |
| --- | --- |
| Frontend | React 19, Vite 8, React Router 7, Axios, Framer Motion, Lucide React |
| Frontend quality | Vitest, React Testing Library, jest dom, Oxlint |
| Backend | Python, FastAPI, Uvicorn, Pydantic, SQLAlchemy, Alembic |
| Database | SQLite |
| Document processing | PyMuPDF, pypdf, Pillow, pytesseract, ReportLab, NumPy |
| Language and matching utilities | Levenshtein, python dotenv, configurable speech and translation adapters |
| Browser capabilities | SpeechRecognition, webkitSpeechRecognition, speechSynthesis, microphone permission APIs |

## Repository structure

| Path | Purpose |
| --- | --- |
| `frontend/src` | React application, pages, components, hooks, API client, and browser speech handling |
| `frontend/public` | Public assets including the application favicon |
| `backend/routers` | FastAPI route modules for sessions, forms, confirmations, schemes, guidance, and fraud checks |
| `backend/services` | Business logic for OCR, form processing, schemes, guidance, fraud analysis, PDF output, and voice configuration |
| `backend/models.py` | SQLAlchemy data models |
| `backend/schemas.py` | Pydantic request and response schemas |
| `backend/config.py` | Environment driven application settings |
| `backend/test_*.py` | Backend regression and feature tests |
| `docs/superpowers` | Design notes and implementation plans for the project phases |

## Local setup

### Requirements

1. Node.js 20 or newer
2. Python 3.11 or newer
3. A modern browser with microphone support for voice input
4. Tesseract only when the OCR backend is configured as `tesseract`

### Backend

From the repository root, create and activate a virtual environment.

```text
cd backend
python -m venv .venv
```

On Windows:

```text
.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```text
source .venv/bin/activate
```

Install the backend dependencies and start the API.

```text
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn main:app
```

The API is available at `http://localhost:8000`. The health endpoint is `http://localhost:8000/health` and the interactive API documentation is available at `http://localhost:8000/docs`.

### Frontend

Open another terminal at the repository root.

```text
cd frontend
npm install
npm run dev
```

The development application is available at `http://localhost:5173`.

The frontend uses `http://localhost:8000` by default. To use another backend address, create `frontend/.env` with the following value.

```text
VITE_API_URL=http://localhost:8000
```

### Backend environment

Copy `backend/.env.example` to `backend/.env` when deploying outside local development. A production deployment should provide a long random value for `SECRET_KEY` and set `DEBUG=false`.

The main settings are listed below.

| Setting | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | SQLAlchemy database connection | SQLite file in `backend` |
| `SECRET_KEY` | Signs and protects randomized challenge state | Development value |
| `NONCE_EXPIRY_SECONDS` | Challenge validity period | `30` |
| `OCR_BACKEND` | Selects the OCR implementation | `stub` |
| `TESSERACT_CMD` | Tesseract executable path | `tesseract` |
| `STT_BACKEND` | Selects speech to text integration | `stub` |
| `TTS_BACKEND` | Selects text to speech integration | `stub` |
| `TRANSLATION_BACKEND` | Selects translation integration | `stub` |
| `LLM_BACKEND` | Selects the guidance language model integration | `stub` |
| `OPENAI_API_KEY` | Optional OpenAI provider credential | Empty |
| `GEMINI_API_KEY` | Optional Gemini provider credential | Empty |
| `UPLOAD_DIR` | Directory for uploaded forms and generated files | `backend/uploads` |
| `MAX_UPLOAD_SIZE_MB` | Maximum accepted upload size | `10` |

Provider credentials must be kept in local environment files or a deployment secret store. They must never be committed to the repository.

## API areas

The backend exposes versioned routes under `/api/v1` and keeps compatible root routes for existing clients.

| Area | Representative routes |
| --- | --- |
| Sessions | `POST /api/v1/sessions`, `GET /api/v1/sessions/{session_id}`, `PATCH /api/v1/sessions/{session_id}/language` |
| Forms | `POST /api/v1/forms/upload`, `GET /api/v1/forms/{form_id}/next-field`, `POST /api/v1/forms/{form_id}/finalize`, `GET /api/v1/forms/{form_id}/download` |
| Challenges | `POST /api/v1/confirmations`, `POST /api/v1/confirmations/{nonce_id}/respond` |
| Schemes | `GET /api/v1/schemes`, `GET /api/v1/schemes/{scheme_id}`, `POST /api/v1/schemes/match` |
| Guidance | `POST /api/v1/guidance/ask` |
| Fraud | `POST /api/v1/fraud/check`, `POST /api/v1/fraud/check-image` |

## Testing and validation

Run frontend checks from the `frontend` directory.

```text
npm test
npm run build
npm run lint
```

Run backend tests from the `backend` directory after installing development dependencies.

```text
pip install -r requirements-dev.txt
python -m pytest
```

The browser speech tests use mocked SpeechRecognition and speech synthesis objects. They do not require a physical microphone. Manual voice testing should be performed in a browser that supports SpeechRecognition and should include microphone permission approval.

## Security and privacy considerations

1. The randomized challenge is bound to a session and expires after 30 seconds by default.
2. The final form generation step requires a separate challenge response.
3. Uploads and generated files are stored in the configured upload directory and should be protected by the deployment environment.
4. Sensitive provider credentials belong in environment configuration and are excluded from version control.
5. The application does not currently use Twilio or mobile OTP verification.
6. Production deployments should use a strong secret key, restricted CORS origins, HTTPS, access controlled storage, and a managed database where appropriate.


