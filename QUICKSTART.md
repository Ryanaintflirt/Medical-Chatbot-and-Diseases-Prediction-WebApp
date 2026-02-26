# Quick Start Guide for Hosting

This guide will help you deploy your Medical Chatbot WebApp in just a few minutes!

## Prerequisites

You need to have your API keys ready:
1. **Firebase credentials** - Get from [Firebase Console](https://console.firebase.google.com/)
2. **DeepSeek API key** - Get from [DeepSeek Platform](https://platform.deepseek.com/)
3. **OpenRouter API key** - Get from [OpenRouter](https://openrouter.ai/)

## Option 1: Docker Deployment (Easiest - Recommended)

### Step 1: Install Docker
- **Windows/Mac**: Download [Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Linux**: `curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh`

### Step 2: Configure Environment
```bash
# Copy the example environment file
cp .env.example SECRET.env

# Edit SECRET.env and add your API keys
nano SECRET.env  # or use any text editor
```

### Step 3: Deploy with One Command
```bash
chmod +x deploy.sh
./deploy.sh
# Select option 1 (Docker Compose)
```

That's it! Your app will be running at `http://localhost:8080` 🎉

## Option 2: Heroku (Free Cloud Hosting)

### Step 1: Install Heroku CLI
```bash
# On macOS
brew tap heroku/brew && brew install heroku

# On Ubuntu/Debian
curl https://cli-assets.heroku.com/install.sh | sh

# On Windows
# Download from: https://devcenter.heroku.com/articles/heroku-cli
```

### Step 2: Login and Create App
```bash
heroku login
heroku create your-medical-chatbot-app
```

### Step 3: Set Your API Keys
```bash
# Set all environment variables
heroku config:set FIREBASE_API_KEY=your_firebase_api_key
heroku config:set FIREBASE_AUTH_DOMAIN=your_domain.firebaseapp.com
heroku config:set FIREBASE_PROJECT_ID=your_project_id
heroku config:set FIREBASE_STORAGE_BUCKET=your_bucket.appspot.com
heroku config:set FIREBASE_MESSAGING_SENDER_ID=your_sender_id
heroku config:set FIREBASE_APP_ID=your_app_id
heroku config:set FIREBASE_MEASUREMENT_ID=G-XXXXXXXXXX
heroku config:set FIREBASE_DATABASE_URL=https://your_project.firebaseio.com

heroku config:set DEEPSEEK_API_KEY=your_deepseek_key
heroku config:set AiApi_Key=your_openrouter_key
heroku config:set AI_Url=https://openrouter.ai/api/v1/chat/completions
```

### Step 4: Deploy
```bash
git push heroku main
heroku open
```

Visit the URLs to initialize:
- `https://your-app.herokuapp.com/init-db`
- `https://your-app.herokuapp.com/populate-doctors`

Done! 🚀

## Option 3: Railway (Modern Cloud Platform)

### Step 1: Install Railway CLI
```bash
npm i -g @railway/cli
```

### Step 2: Login and Initialize
```bash
railway login
railway init
```

### Step 3: Set Environment Variables
Go to your Railway project dashboard → Variables tab, and add all your API keys from `.env.example`

### Step 4: Deploy
```bash
railway up
```

Get your URL:
```bash
railway domain
```

## Option 4: Render (Free with Auto-Deploy)

### Step 1: Push to GitHub
Make sure your code is pushed to a GitHub repository.

### Step 2: Connect to Render
1. Go to [Render.com](https://render.com)
2. Sign up/login with GitHub
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Render will auto-detect the `render.yaml` config

### Step 3: Add Environment Variables
In the Render dashboard, go to Environment tab and add your API keys:
- FIREBASE_API_KEY
- FIREBASE_AUTH_DOMAIN
- FIREBASE_PROJECT_ID
- etc. (see `.env.example` for full list)

### Step 4: Deploy
Click "Create Web Service" and Render will automatically deploy!

## After Deployment Checklist

✅ Visit these URLs to initialize your database:
- `/init-db` - Creates database tables
- `/populate-doctors` - Adds sample doctors

✅ Test these features:
- User registration
- Login
- AI Chatbot
- Disease prediction
- Symptom checker

## Troubleshooting

### "Database not initialized"
→ Visit `/init-db` and `/populate-doctors` endpoints

### "AI Chatbot not responding"
→ Check your DEEPSEEK_API_KEY and AiApi_Key are correct

### "Google Sign-In not working"
→ Add your deployment URL to Firebase authorized domains:
1. Go to Firebase Console
2. Authentication → Settings → Authorized domains
3. Add your deployment URL

### "Port already in use" (local deployment)
→ Stop the existing process:
```bash
# Find process on port 8080
lsof -ti:8080 | xargs kill -9
```

## Need More Help?

- 📖 Read the full [DEPLOYMENT.md](DEPLOYMENT.md) guide
- 📧 Contact: khingkyawzaww@gmail.com
- 🐛 Check application logs for specific errors

## Security Reminder

⚠️ **Never commit your `SECRET.env` file to Git!**

The `.gitignore` file is configured to exclude it, but always double-check:
```bash
git status  # Make sure SECRET.env is not listed
```

---

**Happy Hosting! 🎉**

If you successfully deploy this project, consider giving it a ⭐ on GitHub!
