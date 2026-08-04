# Medical Chatbot and Diseases Prediction WebApp

A comprehensive healthcare web application that combines AI-powered medical chatbot functionality with machine learning-based disease prediction capabilities. The application helps users get preliminary health assessments, check symptoms, and book appointments with healthcare professionals.

## 🚀 Features

### Core Functionality
- **AI Medical Chatbot**: Interactive chatbot powered by Gemini, grounded in a trusted medical
  reference through Retrieval-Augmented Generation (RAG)
- **Persistent Chat History**: Conversations and messages are stored per user, with a sidebar for
  creating, reopening and deleting chats
- **Disease Prediction**: Machine learning models for predicting:
  - Heart Disease
  - Diabetes
  - Parkinson's Disease
- **Symptom Checker**: Symptom analysis using an external medical (Azure) API
- **Doctors & Hospitals**: Browse doctors with their specialty, availability and affiliated hospital
- **Appointments**: Book appointments with conflict detection (a doctor cannot be double-booked)
- **User Profiles**: Profile management including picture upload and medical information storage
- **Admin Dashboard**: Flask-Admin back office at `/admin` for managing users, doctors, hospitals
  and appointments

### Authentication & Security
- **Hybrid Authentication System**:
  - Custom email/password registration and login
  - Google Sign-In via Firebase Authentication
  - Secure password hashing with Werkzeug
- **Session Management**: Flask-Login for secure user sessions
- **Role-Based Authorization**: `user` (default) and `admin` roles; admins are granted either via
  the `ADMIN_EMAILS` env var or the `flask make-admin` CLI command
- **Profile Management**: Update personal and medical information

### User Interface
- Modern, responsive web design
- Intuitive navigation
- Real-time AI chat interface with conversation sidebar
- Interactive disease prediction forms
- Doctor profile browsing
- Installable as a PWA (`static/manifest.json`, app icons)

## 🛠️ Technologies Used

### Backend
- **Flask 2.3.3**: Web framework
- **Flask-SQLAlchemy 3.0.5**: Database ORM
- **Flask-Login 0.6.3**: User session management
- **Flask-Admin 1.6.1**: Admin dashboard (with `WTForms==3.0.1`, required for compatibility)
- **Flask-Migrate 4.0.5**: Schema migrations (`flask db migrate/upgrade`)
- **Flask-CORS 4.0.0**: Cross-origin resource sharing
- **Gunicorn 21.2.0**: Production WSGI server

### Machine Learning
- **scikit-learn >=1.3.2**: Required to unpickle the saved disease models
- **numpy >=1.26.0**: Numerical computations

### AI & NLP
- **Gemini API**: Medical chatbot using Google's generative models
- **fastembed 0.8.0**: ONNX MiniLM embeddings at query time (no torch, keeps the deploy small)
- **Pinecone**: Vector database holding the medical-book embeddings
- LangChain + sentence-transformers + pypdf are used **only offline** to build the index — see
  [requirements-rag.txt](requirements-rag.txt)

### Database
- **SQLite**: Default local database, stored under `instance/`
- **PostgreSQL**: Used automatically when `DATABASE_URL` is set (`psycopg2-binary`)

### Frontend
- HTML5, CSS3, JavaScript
- Font Awesome icons
- Responsive design

### External Services
- **Firebase**: Google authentication (verified via the Firebase REST API)
- **Gemini API**: AI chatbot service
- **Azure API**: Symptom diagnosis service (optional)
- **Pinecone**: RAG retrieval (optional)

## 📋 Prerequisites

- Python 3.9 (see [runtime.txt](runtime.txt); 3.8+ generally works)
- pip (Python package manager)
- Git (for cloning the repository)

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Medical-Chatbot-and-Diseases-Prediction-WebApp
   ```

2. **Create a virtual environment** (recommended)
   ```bash
   python -m venv venv

   # On Windows
   venv\Scripts\activate

   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   Create a `.env` file in the root directory (this is the file the app loads at startup):
   ```env
   # Flask
   SECRET_KEY=generate_with_python_-c_import_secrets_print_secrets.token_hex_32
   FLASK_ENV=development          # set to "production" when deploying
   PORT=8080

   # Firebase Configuration (Google Sign-In)
   FIREBASE_API_KEY=your_firebase_api_key
   FIREBASE_AUTH_DOMAIN=your_firebase_auth_domain
   FIREBASE_PROJECT_ID=your_firebase_project_id
   FIREBASE_STORAGE_BUCKET=your_firebase_storage_bucket
   FIREBASE_MESSAGING_SENDER_ID=your_firebase_messaging_sender_id
   FIREBASE_APP_ID=your_firebase_app_id
   FIREBASE_MEASUREMENT_ID=your_firebase_measurement_id
   FIREBASE_DATABASE_URL=your_firebase_database_url

   # Gemini API (Required for the chatbot)
   GEMINI_API_KEY=your_gemini_api_key
   GEMINI_MODEL=gemini-3-flash-preview      # optional override

   # Admin access
   ADMIN_EMAILS=you@example.com              # comma-separated; auto-promoted on login
   ADMIN_TOKEN=some_long_random_token        # required to call /init-db

   # Optional: PostgreSQL instead of SQLite
   DATABASE_URL=postgresql://user:pass@host/dbname

   # Optional: RAG retrieval
   PINECONE_API_KEY=your_pinecone_api_key
   PINECONE_INDEX=medicalbot
   EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2

   # Optional: Azure Symptom Checker
   DUrl=https://your-azure-endpoint/api/diagnose
   DapiKey=your_azure_subscription_key
   ```

   `SECRET_KEY` is **mandatory** when `FLASK_ENV=production` — the app refuses to start without it.

5. **Database initialization**

   Tables are created automatically on startup, and missing columns on an existing SQLite file are
   patched in. To create the tables explicitly:
   ```
   GET http://localhost:8080/init-db?token=<ADMIN_TOKEN>
   ```
   The token can also be sent as an `X-Admin-Token` header. If `ADMIN_TOKEN` is unset the route is
   disabled (403).

6. **Create an admin user and seed data**

   Register normally, then promote the account:
   ```bash
   flask make-admin you@example.com
   ```
   (or list the email in `ADMIN_EMAILS` before logging in). Doctors, hospitals and appointments are
   then managed through the admin dashboard at `/admin`.

## 🚀 Running the Application

1. **Start the Flask server**
   ```bash
   python app.py
   ```

2. **Access the application**

   Open your browser and navigate to:
   ```
   http://localhost:8080
   ```

3. **Default Configuration**
   - Host: `0.0.0.0`
   - Port: `PORT` env var, default `8080`
   - Debug Mode: on unless `FLASK_ENV=production` or `FLASK_DEBUG=false`

## 📁 Project Structure

```
Medical-Chatbot-and-Diseases-Prediction-WebApp/
│
├── app.py                      # Main Flask application (routes, admin, auth, ML endpoints)
├── models.py                   # Database models
├── loadModels.py               # ML model loading utility
├── requirements.txt            # Runtime dependencies
├── requirements-rag.txt        # Offline index-building dependencies only
├── pytest.ini                  # Test configuration
├── .env                        # Environment variables (create this)
│
├── data/                       # Training datasets + RAG source document
│   ├── diabetes.csv
│   ├── heart.csv
│   ├── parkinsons.csv
│   └── Medical_book.pdf
│
├── saved_models/               # Pre-trained ML models
│   ├── diabetes_model.pkl
│   ├── heart_disease_model.pkl
│   └── parkinsons_model.pkl
│
├── instance/                   # SQLite database files
│   └── healthcare_users.db
│
├── src/                        # Source code modules
│   ├── __init__.py
│   └── rag.py                  # Runtime RAG retrieval (fastembed + Pinecone)
│
├── tests/                      # Automated test suite
│   ├── conftest.py
│   ├── test_app.py             # Pages, auth, authorization, domain logic
│   └── test_rag.py             # Retrieval and context-building
│
├── static/                     # Static files
│   ├── style.css
│   ├── custom.js
│   ├── manifest.json           # PWA manifest
│   ├── image/                  # Images, logo and icons
│   └── uploads/                # Uploaded profile pictures
│
├── templates/                  # HTML templates
│   ├── index.html              # Landing page
│   ├── terms.html              # Terms page
│   ├── login.html              # Login page
│   ├── register.html           # Registration page
│   ├── home.html               # Dashboard / chat interface
│   ├── predit.html             # Disease prediction hub
│   ├── preditHeart.html        # Heart disease prediction
│   ├── preditDiabetes.html     # Diabetes prediction
│   ├── preditParkinsons.html   # Parkinson's prediction
│   ├── symptomsCheck.html      # Symptom checker
│   ├── Doctors.html            # Doctor listings
│   ├── appointment.html        # Appointment booking
│   ├── viewProfile.html        # User profile
│   └── admin/                  # Admin dashboard templates
│       ├── master.html
│       └── dashboard.html
│
├── research/                   # Jupyter notebooks (model training + RAG indexing)
│   ├── predit-diabetes.ipynb
│   ├── predit-heart.ipynb
│   ├── predit-Parkinsons.ipynb
│   └── trials.ipynb
│
├── Dockerfile                  # Container configuration
├── docker-compose.yml          # Multi-container orchestration
├── Procfile                    # Heroku deployment
├── runtime.txt                 # Python version specification
├── render.yaml                 # Render.com deployment
├── deploy.sh                   # Interactive deployment helper
├── DEPLOYMENT.md               # Detailed deployment guide
└── QUICKSTART.md               # Short setup guide
```

## 🔌 API Endpoints

Everything except the landing page, terms page and auth routes requires a logged-in session.

### Public
- `GET /` - Landing page
- `GET /terms` - Terms and conditions

### Authentication
- `GET /login` - Login page
- `POST /login` - User authentication (Firebase or custom)
- `GET /register` - Registration page
- `POST /register` - User registration
- `GET /logout` - User logout

### Main Features
- `GET /home` - User dashboard / chat interface
- `GET /dashboard` - Alternative dashboard route

### AI Chatbot
- `POST /ask` - Send message to AI chatbot
- `GET /test-ai` - Test AI API connection
- `GET /conversations` - List the current user's conversations
- `POST /conversations` - Create a new conversation
- `GET /conversations/<id>` - Fetch a conversation with its messages
- `DELETE /conversations/<id>` - Delete a conversation

### Disease Prediction
- `GET /predict-diseases` - Disease prediction hub
- `GET /predict-heart` - Heart disease prediction page
- `POST /predict-heart-disease` - Heart disease prediction API
- `GET /predict-diabetes` - Diabetes prediction page
- `POST /predict-diabetes-disease` - Diabetes prediction API
- `GET /predict-parkinsons` - Parkinson's prediction page
- `POST /predict-parkinsons-disease` - Parkinson's prediction API

### Symptom Checker
- `GET /symptoms-check` - Symptom checker page
- `POST /check-symptoms` - Symptom analysis API

### Doctors & Appointments
- `GET /doctors` - Browse available doctors
- `GET /appointment` - Appointment booking page
- `POST /appointments` - Book an appointment (rejects double-booked slots)

### Profile Management
- `GET /view-profile` - View user profile
- `POST /update-profile` - Update user profile
- `POST /upload-profile-picture` - Upload a profile picture (png/jpg/jpeg/gif/webp, max 5 MB)
- `POST /update-medical-info` - Update medical information
- `DELETE /delete-profile` - Delete user account

### Admin (admin role required)
- `GET /admin` - Admin dashboard with summary counts
- `/admin/user`, `/admin/doctor`, `/admin/hospital`, `/admin/appointment` - CRUD views

### Database Setup
- `GET /init-db` - Initialize database tables (requires `ADMIN_TOKEN`)

## 🤖 Machine Learning Models

The application uses pre-trained machine learning models for disease prediction:

### Heart Disease Model
- **Input Features**: Age, Sex, Chest Pain Type, Resting Blood Pressure, Cholesterol, Fasting Blood Sugar, Resting ECG, Max Heart Rate, Exercise Induced Angina, ST Depression, Slope, Number of Major Vessels, Thalassemia
- **Output**: Binary classification (0 = Low risk, 1 = High risk)

### Diabetes Model
- **Input Features**: Pregnancies, Glucose, Blood Pressure, Skin Thickness, Insulin, BMI, Diabetes Pedigree Function, Age
- **Output**: Binary classification (0 = Low risk, 1 = High risk)

### Parkinson's Disease Model
- **Input Features**: 22 voice measurement parameters (fo, fhi, flo, Jitter, Shimmer, etc.)
- **Output**: Binary classification (0 = Low risk, 1 = High risk)

## 🗄️ Database Schema

### `users`
- Authentication and profile information; supports custom, Google and Firebase auth
- `role` column (`user` / `admin`) drives admin access
- Stores profile picture, phone number, date of birth, timestamps and linked accounts

### `medical_Infofuser`
- Per-user medical information: symptoms, start time, current medication, allergies

### `conversation`
- A chat thread owned by a user (title, timestamps); deleted with the user

### `message`
- A single message in a conversation (`role` = `user` or `ai`, content, timestamp); deleted with
  its conversation

### `hospital`
- Hospitals/clinics doctors are affiliated with (name, address, city, contact, website)

### `doctor`
- Doctor profiles: specialty, availability, qualification, experience, bio, photo, hospital link

### `appointment`
- Links a user and a doctor with a date, time and status (`Scheduled` / `Cancelled` / …)

## 🔒 Security Features

- Password hashing using Werkzeug security
- Session management with Flask-Login; unauthenticated requests are redirected to the login page
  (`DELETE` requests get a 401 JSON response instead)
- Firebase token verification for Google authentication
- Role-based access control on the admin dashboard
- `/init-db` gated behind `ADMIN_TOKEN`
- Production start-up fails fast if `SECRET_KEY` is missing
- Profile-picture uploads restricted by extension and size
- SQL injection protection via SQLAlchemy ORM
- CORS configuration for API security

## 📝 Usage Examples

### Disease Prediction
1. Navigate to "Predict Diseases" from the main menu
2. Select the disease type (Heart, Diabetes, or Parkinson's)
3. Fill in the required medical parameters
4. Submit to get prediction results with confidence scores

### AI Chatbot
1. Go to the dashboard
2. Start a new chat or reopen an existing conversation from the sidebar
3. Ask health-related questions and receive answers grounded in the medical reference

### Symptom Checker
1. Navigate to "Symptom Check"
2. Enter your symptoms, age, gender, and other relevant information
3. Get preliminary diagnosis suggestions

## 🧪 Development

### Running Tests
An automated test suite (in [tests/](tests/)) covers public pages, authentication and
authorisation, the registration/login flow, admin-role promotion, model loading, and the RAG
retrieval helpers. It runs against a throwaway SQLite database, so no configuration is required:
```bash
pytest
```

### Database
By default the app uses a local SQLite file under `instance/`. In production,
set the `DATABASE_URL` environment variable to a PostgreSQL connection string
and the app will use it automatically (the legacy `postgres://` scheme is normalised), so data
persists across deploys. On Render this is wired up by [render.yaml](render.yaml) (managed
Postgres). Schema changes can be managed with Flask-Migrate (`flask db migrate` / `flask db
upgrade`).

### Retrieval-Augmented Generation (RAG)
The chatbot grounds its answers in a trusted medical reference
(`data/Medical_book.pdf`) using RAG backed by a **Pinecone** vector database:

1. **Offline indexing** ([research/trials.ipynb](research/trials.ipynb)): LangChain loads and
   chunks the PDF, embeds each chunk with a MiniLM sentence-transformer, and upserts the vectors
   into a Pinecone index (`medicalbot`). This is a one-off step; the index persists in Pinecone.
   Install the extra dependencies with `pip install -r requirements-rag.txt` first — they are not
   needed to run the web app.
2. **Runtime retrieval** ([src/rag.py](src/rag.py)): at query time the user's question is
   embedded with the same MiniLM model — served via **fastembed** (ONNX, no
   torch) so it stays deployable — Pinecone's REST API returns the most similar passages, and they
   are injected into the model prompt as grounding context. Low-scoring matches are filtered out
   and the context is capped by a character budget. If Pinecone or the embedding model is
   unavailable, the chatbot degrades gracefully to a normal (non-grounded) answer.

Environment variables: `PINECONE_API_KEY` (required for RAG), and optionally `PINECONE_INDEX`
(defaults to `medicalbot`), `PINECONE_HOST` (skips host resolution) and `EMBED_MODEL`
(defaults to `sentence-transformers/all-MiniLM-L6-v2`).

### Model Training
The Jupyter notebooks in the [research/](research/) directory contain the model training code:
- `predit-diabetes.ipynb`
- `predit-heart.ipynb`
- `predit-Parkinsons.ipynb`

### Adding New Models
1. Train your model using scikit-learn
2. Save the model as a `.pkl` file in `saved_models/`
3. Update [loadModels.py](loadModels.py) to load the new model
4. Create prediction routes in [app.py](app.py)
5. Add corresponding HTML templates

## ⚠️ Important Notes

- **Medical Disclaimer**: This application is for informational purposes only and should not replace professional medical advice, diagnosis, or treatment. Always consult with qualified healthcare providers for medical concerns.

- **API Keys**: Ensure all values in `.env` are kept secure and never committed to version control.

- **Database**: The SQLite database is created automatically on first run. Make sure to back it up
  regularly, and prefer `DATABASE_URL`/Postgres in production since container filesystems are
  ephemeral.

## 🐛 Troubleshooting

### Models Not Loading
- Ensure all `.pkl` files exist in `saved_models/` directory
- Check that the installed scikit-learn version can unpickle them (`scikit-learn>=1.3.2`)
- Check file paths in [loadModels.py](loadModels.py)

### Database Errors
- Call `/init-db?token=<ADMIN_TOKEN>` to initialize tables
- Check database file permissions in `instance/` directory

### Admin Dashboard Returns 403
- Confirm the logged-in account has the `admin` role (`flask make-admin <email>` or `ADMIN_EMAILS`)

### API Connection Issues
- Verify API keys in `.env`
- Check internet connectivity
- Review API rate limits

### Chatbot Answers Are Not Grounded
- Check that `PINECONE_API_KEY` is set and the `medicalbot` index exists
- RAG failures are logged as warnings and fall back to ungrounded answers by design

## 🌐 Deployment & Hosting

This application is ready to be hosted on various platforms!

### Quick Start Deployment

Use the provided deployment script for easy setup:

```bash
chmod +x deploy.sh
./deploy.sh
```

The script supports:
- **Docker Compose** (Recommended) - Easiest option with one command
- **Docker** - Container deployment
- **Local Development** - Test locally before deploying
- **Heroku** - Cloud platform deployment

### Deployment Documentation

For detailed deployment instructions on various platforms (Heroku, Railway, Render, DigitalOcean, AWS, etc.), see **[DEPLOYMENT.md](DEPLOYMENT.md)**. A condensed guide lives in
**[QUICKSTART.md](QUICKSTART.md)**.

### Configuration Files Included

- `Dockerfile` - Container configuration
- `docker-compose.yml` - Multi-container orchestration
- `.dockerignore` - Optimized Docker builds
- `Procfile` - Heroku deployment (gunicorn, 2 workers)
- `runtime.txt` - Python version specification
- `render.yaml` - Render.com deployment (web service + managed Postgres)
- `deploy.sh` - Interactive deployment helper

### Required API Keys

Before deploying, you'll need:
- **Gemini API** key (for the AI chatbot)
- **Firebase** credentials (for Google authentication)
- `SECRET_KEY` and `ADMIN_TOKEN` (generate long random values)
- Optional: Pinecone API key (for RAG grounding)
- Optional: Azure API (for the symptom checker)

## 📄 License

This project is part of a Diploma HDITC COS209 Project.

## 👤 Author

**Khaing Kyaw Zaww**
- Email: khingkyawzaww@gmail.com

## 🙏 Acknowledgments

- Google AI Studio / Gemini API for generative responses
- Pinecone and fastembed for vector retrieval
- Azure API for symptom diagnosis
- Firebase for authentication services
- scikit-learn community for ML tools

---

**Note**: This is an educational project. For production use, additional security measures, error handling, and compliance with healthcare regulations (such as HIPAA) should be implemented.
