# Render Deployment Guide for VulnEats

This guide will walk you through deploying your VulnEats application on Render.

## Prerequisites

1. A GitHub repository with your code
2. A Render account (free tier available)
3. Environment variables ready (see below)

## Project Structure

Your project has been configured with the following structure for Render deployment:

```
Vuln_FoodOrder/
├── backend/
│   ├── Dockerfile          # Backend container configuration
│   ├── app.py             # Main Flask application
│   ├── config.py          # Production configuration
│   ├── start.sh           # Production startup script
│   └── requirements.txt   # Python dependencies
├── frontend/
│   ├── Dockerfile         # Frontend container configuration
│   └── package.json       # Node.js dependencies
├── render.yaml            # Render deployment configuration
├── env.example            # Environment variables template
└── Dockerfile             # Root Dockerfile for backend
```

## Deployment Steps

### Step 1: Prepare Your Repository

1. **Push your code to GitHub** (if not already done):
   ```bash
   git add .
   git commit -m "Configure for Render deployment"
   git push origin main
   ```

### Step 2: Set Up Database

1. **Create a PostgreSQL database on Render**:
   - Go to your Render dashboard
   - Click "New +" → "PostgreSQL"
   - Name it `vulneats-db`
   - Choose the free plan
   - Note down the database credentials

### Step 3: Deploy Backend Service

1. **Create a new Web Service**:
   - Go to your Render dashboard
   - Click "New +" → "Web Service"
   - Connect your GitHub repository

2. **Configure the backend service**:
   - **Name**: `vulneats-backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `python backend/app.py`
   - **Python Version**: `3.11`

3. **Set Environment Variables**:
   ```
   FLASK_ENV=production
   FLASK_APP=app.py
   DATABASE_URL=postgresql://username:password@hostname:port/database_name
   SECRET_KEY=your-super-secret-key-here
   JWT_SECRET_KEY=your-jwt-secret-key-here
   UPLOAD_FOLDER=/opt/render/project/src/uploads
   FRONTEND_BASE_URL=https://your-frontend-url.onrender.com
   BACKEND_BASE_URL=https://your-backend-url.onrender.com
   CHAPA_SECRET_KEY=your-chapa-secret-key
   CHAPA_PUBLIC_KEY=your-chapa-public-key
   CLOUDINARY_CLOUD_NAME=your-cloudinary-cloud-name
   CLOUDINARY_API_KEY=your-cloudinary-api-key
   CLOUDINARY_API_SECRET=your-cloudinary-api-secret
   ```

4. **Deploy the backend**

### Step 4: Deploy Frontend Service

1. **Create a new Static Site**:
   - Go to your Render dashboard
   - Click "New +" → "Static Site"
   - Connect your GitHub repository

2. **Configure the frontend service**:
   - **Name**: `vulneats-frontend`
   - **Build Command**: `cd frontend && npm ci && npm run build`
   - **Publish Directory**: `frontend/.next`

3. **Set Environment Variables**:
   ```
   NEXT_PUBLIC_API_BASE=https://your-backend-url.onrender.com
   NODE_ENV=production
   ```

4. **Deploy the frontend**

### Step 5: Update URLs

After both services are deployed:

1. **Update backend environment variables**:
   - Go to your backend service settings
   - Update `FRONTEND_BASE_URL` with your actual frontend URL
   - Update `BACKEND_BASE_URL` with your actual backend URL

2. **Update frontend environment variables**:
   - Go to your frontend service settings
   - Update `NEXT_PUBLIC_API_BASE` with your actual backend URL

3. **Redeploy both services** to pick up the new URLs

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `SECRET_KEY` | Flask secret key | `your-super-secret-key-here` |
| `JWT_SECRET_KEY` | JWT signing key | `your-jwt-secret-key-here` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Flask environment | `production` |
| `FLASK_DEBUG` | Debug mode | `0` |
| `UPLOAD_FOLDER` | File upload directory | `/opt/render/project/src/uploads` |
| `CHAPA_SECRET_KEY` | Payment gateway secret | - |
| `CHAPA_PUBLIC_KEY` | Payment gateway public key | - |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name | - |
| `CLOUDINARY_API_KEY` | Cloudinary API key | - |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret | - |

## Database Setup

The application will automatically create the database schema on first run. If you need to manually initialize:

1. **SSH into your backend service** (if needed)
2. **Run the initialization script**:
   ```bash
   python backend/init_db.py
   ```

## Health Check

Your backend includes a health check endpoint at `/api/health` that Render can use to monitor service health.

## Troubleshooting

### Common Issues

1. **Build Failures**:
   - Check that all dependencies are in `requirements.txt`
   - Ensure Python version matches (3.11)

2. **Database Connection Issues**:
   - Verify `DATABASE_URL` is correct
   - Check database credentials
   - Ensure database is accessible from Render

3. **CORS Issues**:
   - Verify `FRONTEND_BASE_URL` and `BACKEND_BASE_URL` are set correctly
   - Check that URLs match exactly (including https://)

4. **File Upload Issues**:
   - Ensure `UPLOAD_FOLDER` directory exists
   - Check file permissions

### Logs

- **Backend logs**: Available in Render dashboard under your backend service
- **Frontend logs**: Available in Render dashboard under your frontend service

## Security Considerations

⚠️ **Important**: This is a vulnerable application for educational purposes. Do NOT use in production without fixing security issues.

### Production Security Checklist

- [ ] Change all default secret keys
- [ ] Use HTTPS only
- [ ] Fix SQL injection vulnerabilities
- [ ] Implement proper authentication
- [ ] Add input validation
- [ ] Configure proper CORS policies
- [ ] Use secure session cookies

## Cost Estimation

### Free Tier Limits

- **Web Services**: 750 hours/month per service
- **PostgreSQL**: 1GB storage, 1GB bandwidth
- **Static Sites**: 100GB bandwidth/month

### Paid Plans

- **Starter**: $7/month per service
- **Standard**: $25/month per service
- **Pro**: $85/month per service

## Monitoring

1. **Health Checks**: Automatic via `/api/health` endpoint
2. **Logs**: Available in Render dashboard
3. **Metrics**: Basic metrics available in paid plans

## Support

- **Render Documentation**: https://render.com/docs
- **Render Support**: Available in dashboard
- **Community**: Render Discord/Forums

---

## Quick Deploy Commands

If you prefer using Render CLI:

```bash
# Install Render CLI
npm install -g @render/cli

# Login to Render
render auth login

# Deploy backend
render services create web \
  --name vulneats-backend \
  --repo https://github.com/your-username/your-repo \
  --build-command "pip install -r backend/requirements.txt" \
  --start-command "python backend/app.py"

# Deploy frontend
render services create static \
  --name vulneats-frontend \
  --repo https://github.com/your-username/your-repo \
  --build-command "cd frontend && npm ci && npm run build" \
  --publish-dir "frontend/.next"
```

---

**Note**: Remember to update the URLs in your environment variables after deployment, and always use strong, unique secret keys in production!
