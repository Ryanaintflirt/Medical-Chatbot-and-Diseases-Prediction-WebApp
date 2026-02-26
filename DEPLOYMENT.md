# Deployment Guide for Medical Chatbot WebApp

This guide provides instructions for deploying the Medical Chatbot and Diseases Prediction WebApp on various hosting platforms.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Deployment Options](#deployment-options)
  - [Docker Deployment (Recommended)](#docker-deployment-recommended)
  - [Heroku Deployment](#heroku-deployment)
  - [Railway Deployment](#railway-deployment)
  - [Render Deployment](#render-deployment)
  - [DigitalOcean App Platform](#digitalocean-app-platform)
  - [AWS Elastic Beanstalk](#aws-elastic-beanstalk)
- [Post-Deployment Steps](#post-deployment-steps)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before deploying, ensure you have:

1. **API Keys Ready:**
   - Firebase project credentials
   - DeepSeek API key
   - OpenRouter API key
   - (Optional) Azure Symptom API credentials
   - (Optional) Pinecone API key

2. **Tools Installed:**
   - Docker and Docker Compose (for Docker deployment)
   - Git
   - Python 3.8+ (for local testing)

## Environment Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Medical-Chatbot-and-Diseases-Prediction-WebApp
```

### 2. Configure Environment Variables

Copy the example environment file:
```bash
cp .env.example SECRET.env
```

Edit `SECRET.env` and fill in your API keys:
```env
# Firebase Configuration (Required)
FIREBASE_API_KEY=your_firebase_api_key
FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_STORAGE_BUCKET=your_project.appspot.com
FIREBASE_MESSAGING_SENDER_ID=your_sender_id
FIREBASE_APP_ID=your_app_id
FIREBASE_MEASUREMENT_ID=G-XXXXXXXXXX
FIREBASE_DATABASE_URL=https://your_project.firebaseio.com

# AI API Keys (Required)
DEEPSEEK_API_KEY=your_deepseek_key
AiApi_Key=your_openrouter_key
AI_Url=https://openrouter.ai/api/v1/chat/completions

# Optional APIs
PINECONE_API_KEY=your_pinecone_key
url=your_azure_symptom_api_url
DapiKey=your_azure_symptom_key
```

## Deployment Options

### Docker Deployment (Recommended)

Docker provides the easiest and most consistent deployment experience.

#### Using Docker Compose

1. **Build and start the application:**
   ```bash
   docker-compose up -d
   ```

2. **Initialize the database:**
   ```bash
   curl http://localhost:8080/init-db
   curl http://localhost:8080/populate-doctors
   ```

3. **Access the application:**
   Open your browser to `http://localhost:8080`

4. **View logs:**
   ```bash
   docker-compose logs -f
   ```

5. **Stop the application:**
   ```bash
   docker-compose down
   ```

#### Using Docker Only

1. **Build the Docker image:**
   ```bash
   docker build -t medical-chatbot .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     -p 8080:8080 \
     --name medical-chatbot \
     -e FIREBASE_API_KEY=your_key \
     -e DEEPSEEK_API_KEY=your_key \
     -e AiApi_Key=your_key \
     -v $(pwd)/instance:/app/instance \
     -v $(pwd)/saved_models:/app/saved_models \
     medical-chatbot
   ```

3. **Initialize database and access:**
   Same as Docker Compose steps above.

### Heroku Deployment

1. **Install Heroku CLI:**
   ```bash
   curl https://cli-assets.heroku.com/install.sh | sh
   ```

2. **Login to Heroku:**
   ```bash
   heroku login
   ```

3. **Create a Heroku app:**
   ```bash
   heroku create your-medical-chatbot-app
   ```

4. **Set environment variables:**
   ```bash
   heroku config:set FIREBASE_API_KEY=your_key
   heroku config:set FIREBASE_AUTH_DOMAIN=your_domain
   heroku config:set FIREBASE_PROJECT_ID=your_project_id
   heroku config:set FIREBASE_STORAGE_BUCKET=your_bucket
   heroku config:set FIREBASE_MESSAGING_SENDER_ID=your_sender_id
   heroku config:set FIREBASE_APP_ID=your_app_id
   heroku config:set FIREBASE_MEASUREMENT_ID=your_measurement_id
   heroku config:set FIREBASE_DATABASE_URL=your_database_url
   heroku config:set DEEPSEEK_API_KEY=your_deepseek_key
   heroku config:set AiApi_Key=your_openrouter_key
   heroku config:set AI_Url=https://openrouter.ai/api/v1/chat/completions
   ```

5. **Create Procfile:**
   ```bash
   echo "web: gunicorn --bind 0.0.0.0:\$PORT --workers 2 --timeout 120 app:app" > Procfile
   ```

6. **Deploy:**
   ```bash
   git add .
   git commit -m "Deploy to Heroku"
   git push heroku main
   ```

7. **Initialize database:**
   ```bash
   heroku run python -c "from app import app, db; app.app_context().push(); db.create_all()"
   ```

8. **Open your app:**
   ```bash
   heroku open
   ```

### Railway Deployment

1. **Install Railway CLI:**
   ```bash
   npm i -g @railway/cli
   ```

2. **Login to Railway:**
   ```bash
   railway login
   ```

3. **Initialize project:**
   ```bash
   railway init
   ```

4. **Set environment variables:**
   Go to Railway Dashboard > Your Project > Variables
   Add all required environment variables from your SECRET.env

5. **Deploy:**
   ```bash
   railway up
   ```

6. **Get deployment URL:**
   ```bash
   railway domain
   ```

### Render Deployment

1. **Create `render.yaml`** in your project root:
   ```yaml
   services:
     - type: web
       name: medical-chatbot
       env: python
       buildCommand: pip install -r requirements.txt
       startCommand: gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app
       envVars:
         - key: PYTHON_VERSION
           value: 3.9.0
         - key: FIREBASE_API_KEY
           sync: false
         - key: DEEPSEEK_API_KEY
           sync: false
         - key: AiApi_Key
           sync: false
   ```

2. **Connect to Render:**
   - Go to https://render.com
   - Create a new Web Service
   - Connect your GitHub repository
   - Set environment variables in the dashboard
   - Deploy

### DigitalOcean App Platform

1. **Create `app.yaml`:**
   ```yaml
   name: medical-chatbot
   services:
   - name: web
     github:
       repo: your-username/your-repo
       branch: main
       deploy_on_push: true
     run_command: gunicorn --bind 0.0.0.0:8080 --workers 2 --timeout 120 app:app
     http_port: 8080
     instance_count: 1
     instance_size_slug: basic-xxs
     envs:
     - key: FIREBASE_API_KEY
       value: ${FIREBASE_API_KEY}
     - key: DEEPSEEK_API_KEY
       value: ${DEEPSEEK_API_KEY}
     - key: AiApi_Key
       value: ${AiApi_Key}
   ```

2. **Deploy via DigitalOcean Dashboard:**
   - Go to Apps
   - Create App
   - Connect GitHub repository
   - Configure environment variables
   - Deploy

### AWS Elastic Beanstalk

1. **Install EB CLI:**
   ```bash
   pip install awsebcli
   ```

2. **Initialize EB application:**
   ```bash
   eb init -p python-3.9 medical-chatbot
   ```

3. **Create environment:**
   ```bash
   eb create medical-chatbot-env
   ```

4. **Set environment variables:**
   ```bash
   eb setenv FIREBASE_API_KEY=your_key DEEPSEEK_API_KEY=your_key AiApi_Key=your_key
   ```

5. **Deploy:**
   ```bash
   eb deploy
   ```

6. **Open application:**
   ```bash
   eb open
   ```

## Post-Deployment Steps

After deploying to any platform:

1. **Initialize Database:**
   Visit these URLs to set up your database:
   - `https://your-app-url.com/init-db`
   - `https://your-app-url.com/populate-doctors`

2. **Test Features:**
   - Register a new user
   - Test login functionality
   - Try the AI chatbot
   - Test disease prediction models
   - Verify symptom checker

3. **Monitor Logs:**
   Check application logs for any errors or warnings.

4. **Set Up Monitoring:**
   Consider setting up monitoring and alerts for:
   - Application uptime
   - Error rates
   - API usage
   - Database size

## Troubleshooting

### Common Issues

#### 1. Database Not Initialized
**Error:** Tables don't exist or database errors
**Solution:** Visit `/init-db` and `/populate-doctors` endpoints

#### 2. Model Files Missing
**Error:** Cannot load ML models
**Solution:** Ensure `saved_models/` directory is included in deployment with `.pkl` files

#### 3. API Connection Errors
**Error:** AI chatbot or symptom checker not working
**Solution:** 
- Verify API keys are correctly set
- Check API rate limits
- Ensure environment variables are properly configured

#### 4. Firebase Authentication Issues
**Error:** Google sign-in not working
**Solution:**
- Add your deployment URL to Firebase authorized domains
- Verify all Firebase config variables are set

#### 5. Port Binding Issues
**Error:** Application not accessible
**Solution:**
- Ensure the app binds to `0.0.0.0` not `localhost`
- Use the correct PORT environment variable for your platform

### Performance Optimization

For production deployments:

1. **Use a Production Database:**
   Consider PostgreSQL instead of SQLite for better concurrent access

2. **Enable Caching:**
   Implement Redis or Memcached for session and data caching

3. **Scale Workers:**
   Increase gunicorn workers based on your server's CPU cores:
   ```
   workers = (2 * CPU_cores) + 1
   ```

4. **Enable HTTPS:**
   Use your platform's SSL/TLS certificate management

5. **Set Up CDN:**
   Use a CDN for static files (CSS, JS, images)

## Security Considerations

- Never commit `SECRET.env` or `.env` files to version control
- Use strong, randomly generated secret keys
- Enable HTTPS for production
- Regularly update dependencies: `pip install -r requirements.txt --upgrade`
- Monitor for security vulnerabilities
- Implement rate limiting for API endpoints
- Set up proper CORS policies

## Support

For issues or questions:
- Check the main README.md
- Review application logs
- Contact: khingkyawzaww@gmail.com

---

**Medical Disclaimer:** This application is for educational and informational purposes only. It should not replace professional medical advice, diagnosis, or treatment.
