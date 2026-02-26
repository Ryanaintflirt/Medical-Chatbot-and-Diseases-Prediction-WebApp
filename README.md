# Medical Chatbot and Diseases Prediction WebApp

A comprehensive healthcare web application that combines AI-powered medical chatbot functionality with machine learning-based disease prediction capabilities. The application helps users get preliminary health assessments, check symptoms, and book appointments with healthcare professionals.

## 🚀 Features

### Core Functionality
- **AI Medical Chatbot**: Interactive chatbot powered by DeepSeek AI that provides health-related information and advice
- **Disease Prediction**: Machine learning models for predicting:
  - Heart Disease
  - Diabetes
  - Parkinson's Disease
- **Symptom Checker**: Advanced symptom analysis using external medical API
- **Doctor Management**: Browse available doctors and book appointments
- **User Profiles**: Comprehensive user profile management with medical information storage

### Authentication & Security
- **Hybrid Authentication System**:
  - Custom email/password registration and login
  - Google Sign-In via Firebase Authentication
  - Secure password hashing with Werkzeug
- **Session Management**: Flask-Login for secure user sessions
- **Profile Management**: Update personal and medical information

### User Interface
- Modern, responsive web design
- Intuitive navigation
- Real-time AI chat interface
- Interactive disease prediction forms
- Doctor profile browsing

## 🛠️ Technologies Used

### Backend
- **Flask 2.3.3**: Web framework
- **Flask-SQLAlchemy 3.0.5**: Database ORM
- **Flask-Login 0.6.3**: User session management
- **Flask-CORS 4.0.0**: Cross-origin resource sharing

### Machine Learning
- **scikit-learn 1.3.0**: ML model training and prediction
- **numpy 1.24.3**: Numerical computations
- **pandas 2.0.3**: Data manipulation

### AI & NLP
- **DeepSeek AI API**: Medical chatbot via OpenRouter
- **LangChain 0.0.350**: PDF document processing
- **sentence-transformers 2.2.2**: Text embeddings

### Database
- **SQLite**: Lightweight database for user data, medical records, and appointments

### Frontend
- HTML5, CSS3, JavaScript
- Font Awesome icons
- Responsive design

### External Services
- **Firebase**: Google authentication
- **OpenRouter API**: AI chatbot service
- **Azure API**: Symptom diagnosis service

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Git (for cloning the repository)

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Medical-Chatbot-and-Diseases-Prediction-WebApp-main
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
   
   Create a `SECRET.env` file in the root directory with the following variables:
   ```env
   # Firebase Configuration
   FIREBASE_API_KEY=your_firebase_api_key
   FIREBASE_AUTH_DOMAIN=your_firebase_auth_domain
   FIREBASE_PROJECT_ID=your_firebase_project_id
   FIREBASE_STORAGE_BUCKET=your_firebase_storage_bucket
   FIREBASE_MESSAGING_SENDER_ID=your_firebase_messaging_sender_id
   FIREBASE_APP_ID=your_firebase_app_id
   FIREBASE_MEASUREMENT_ID=your_firebase_measurement_id
   FIREBASE_DATABASE_URL=your_firebase_database_url
   
   # DeepSeek AI API Key
   DEEPSEEK_API_KEY=your_deepseek_api_key
   ```

5. **Initialize the database**
   
   Start the Flask application and visit:
   ```
   http://localhost:8080/init-db
   ```
   
   Then populate doctors data:
   ```
   http://localhost:8080/populate-doctors
   ```

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
   - Port: `8080`
   - Debug Mode: Enabled

## 📁 Project Structure

```
Medical-Chatbot-and-Diseases-Prediction-WebApp-main/
│
├── app.py                      # Main Flask application
├── models.py                   # Database models (User, Doctor, Appointment, MedicalInfo)
├── loadModels.py              # ML model loading utility
├── setup.py                   # Package setup configuration
├── requirements.txt           # Python dependencies
├── SECRET.env                 # Environment variables (create this)
│
├── data/                      # Training datasets
│   ├── diabetes.csv
│   ├── heart.csv
│   ├── parkinsons.csv
│   └── Medical_book.pdf
│
├── saved_models/              # Pre-trained ML models
│   ├── diabetes_model.pkl
│   ├── heart_disease_model.pkl
│   └── parkinsons_model.pkl
│
├── instance/                  # Database files
│   └── healthcare_users.db
│
├── src/                       # Source code modules
│   ├── __init__.py
│   ├── helper.py             # PDF processing utilities
│   └── prompt.py             # AI prompt templates
│
├── static/                    # Static files
│   ├── style.css             # Stylesheet
│   ├── custom.js             # JavaScript
│   └── image/                # Images
│       └── BackGround.jpg
│
├── templates/                 # HTML templates
│   ├── index.html            # Home page
│   ├── login.html            # Login page
│   ├── register.html         # Registration page
│   ├── home.html             # Dashboard
│   ├── predit.html           # Disease prediction hub
│   ├── preditHeart.html      # Heart disease prediction
│   ├── preditDiabetes.html   # Diabetes prediction
│   ├── preditParkinsons.html # Parkinson's prediction
│   ├── symptomsCheck.html    # Symptom checker
│   ├── Doctors.html          # Doctor listings
│   ├── appointment.html      # Appointment booking
│   └── viewProfile.html      # User profile
│
└── research/                  # Jupyter notebooks for model development
    ├── predit-diabetes.ipynb
    ├── predit-heart.ipynb
    ├── predit-Parkinsons.ipynb
    └── trials.ipynb
```

## 🔌 API Endpoints

### Authentication
- `GET /login` - Login page
- `POST /login` - User authentication (Firebase or custom)
- `GET /register` - Registration page
- `POST /register` - User registration
- `GET /logout` - User logout

### Main Features
- `GET /` - Home page
- `GET /home` - User dashboard (requires login)
- `GET /dashboard` - Alternative dashboard route

### AI Chatbot
- `POST /ask` - Send message to AI chatbot (requires login)
- `GET /test-ai` - Test AI API connection

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

### Profile Management
- `GET /view-profile` - View user profile
- `POST /update-profile` - Update user profile
- `POST /update-medical-info` - Update medical information
- `DELETE /delete-profile` - Delete user account

### Database Setup
- `GET /init-db` - Initialize database tables
- `GET /populate-doctors` - Populate doctor data

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

### Users Table
- User authentication and profile information
- Supports both custom and Google authentication
- Stores profile picture, phone number, date of birth

### Medical_Infofuser Table
- Stores user medical information
- Includes symptoms, medications, allergies, and medical history

### Doctor Table
- Doctor profiles with specialties, availability, and contact information
- Includes qualifications, experience, and bio

### Appointment Table
- Links users with doctors for appointments
- Stores appointment date, time, and status

## 🔒 Security Features

- Password hashing using Werkzeug security
- Session management with Flask-Login
- Firebase token verification for Google authentication
- SQL injection protection via SQLAlchemy ORM
- CORS configuration for API security

## 📝 Usage Examples

### Disease Prediction
1. Navigate to "Predict Diseases" from the main menu
2. Select the disease type (Heart, Diabetes, or Parkinson's)
3. Fill in the required medical parameters
4. Submit to get prediction results with confidence scores

### AI Chatbot
1. Go to the home page
2. Use the chat interface to ask health-related questions
3. Receive AI-powered responses with medical information

### Symptom Checker
1. Navigate to "Symptom Check"
2. Enter your symptoms, age, gender, and other relevant information
3. Get preliminary diagnosis suggestions

## 🧪 Development

### Running Tests
```bash
pytest
```

### Model Training
The Jupyter notebooks in the `research/` directory contain the model training code:
- `predit-diabetes.ipynb`
- `predit-heart.ipynb`
- `predit-Parkinsons.ipynb`

### Adding New Models
1. Train your model using scikit-learn
2. Save the model as a `.pkl` file in `saved_models/`
3. Update `loadModels.py` to load the new model
4. Create prediction routes in `app.py`
5. Add corresponding HTML templates

## ⚠️ Important Notes

- **Medical Disclaimer**: This application is for informational purposes only and should not replace professional medical advice, diagnosis, or treatment. Always consult with qualified healthcare providers for medical concerns.

- **API Keys**: Ensure all API keys in `SECRET.env` are kept secure and never committed to version control.

- **Database**: The SQLite database is created automatically on first run. Make sure to back up the database regularly.

## 🐛 Troubleshooting

### Models Not Loading
- Ensure all `.pkl` files exist in `saved_models/` directory
- Check file paths in `loadModels.py`

### Database Errors
- Run `/init-db` endpoint to initialize tables
- Check database file permissions in `instance/` directory

### API Connection Issues
- Verify API keys in `SECRET.env`
- Check internet connectivity
- Review API rate limits

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

For detailed deployment instructions on various platforms (Heroku, Railway, Render, DigitalOcean, AWS, etc.), see **[DEPLOYMENT.md](DEPLOYMENT.md)**.

### Configuration Files Included

- `Dockerfile` - Container configuration
- `docker-compose.yml` - Multi-container orchestration
- `.dockerignore` - Optimized Docker builds
- `Procfile` - Heroku deployment
- `runtime.txt` - Python version specification
- `render.yaml` - Render.com deployment
- `.env.example` - Environment variable template
- `deploy.sh` - Interactive deployment helper

### Required API Keys

Before deploying, you'll need:
- **Firebase** credentials (for authentication)
- **DeepSeek API** key (for AI chatbot)
- **OpenRouter API** key (for chatbot routing)
- Optional: Azure API (for symptom checker)
- Optional: Pinecone API (for vector database)

See `.env.example` for the complete list and instructions on where to obtain these keys.

## 📄 License

This project is part of a Diploma HDITC COS209 Project.

## 👤 Author

**Khaing Kyaw Zaww**
- Email: khingkyawzaww@gmail.com

## 🙏 Acknowledgments

- DeepSeek AI for chatbot capabilities
- OpenRouter for API access
- Azure API for symptom diagnosis
- Firebase for authentication services
- scikit-learn community for ML tools

---

**Note**: This is an educational project. For production use, additional security measures, error handling, and compliance with healthcare regulations (such as HIPAA) should be implemented.#  M e d i c a l - C h a t b o t - a n d - D i s e a s e s - P r e d i c t i o n - W e b A p p 
 
 #   M e d i c a l - C h a t b o t - a n d - D i s e a s e s - P r e d i c t i o n - W e b A p p 
 
 #   M e d i c a l - C h a t b o t - a n d - D i s e a s e s - P r e d i c t i o n - W e b A p p 
 
 