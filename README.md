# HTML Uploader Application

Full-stack application for uploading and viewing HTML files with user authentication and file locking features.

## Features

- **User Authentication**: Register and login functionality
- **HTML File Upload**: Upload HTML files to MinIO S3 storage
- **File Locking**: Lock files to prevent deletion
- **View Files**: Open uploaded HTML files in browser
- **Modern Stack**: React frontend, FastAPI backend, PostgreSQL database, MinIO storage

## Technology Stack

- **Frontend**: React.js
- **Backend**: Python FastAPI
- **Database**: PostgreSQL with Flyway migrations
- **Storage**: MinIO (S3-compatible)
- **Reverse Proxy**: Nginx
- **Orchestration**: Docker Compose

## Prerequisites

- Docker
- Docker Compose

## Getting Started

1. Clone the repository
2. Navigate to the project directory
3. Start the application:

```bash
docker-compose up --build
```

4. Access the application:
   - Main Application: http://localhost
   - Backend API: http://localhost:8000
   - MinIO Console: http://localhost:9001

## Default Credentials

### MinIO
- Username: `minioadmin`
- Password: `minioadmin`

### Database
- User: `postgres`
- Password: `postgres`
- Database: `htmluploader`

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/me` - Get current user

### Files
- `POST /api/files/upload` - Upload HTML file
- `GET /api/files` - List user's files
- `GET /api/files/{file_id}` - View/download file
- `PATCH /api/files/{file_id}/lock` - Lock/unlock file
- `DELETE /api/files/{file_id}` - Delete file (only if unlocked)

## Project Structure

```
html-uploader/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── main.py         # Main application
│   │   ├── models.py       # Database models
│   │   ├── schemas.py      # Pydantic schemas
│   │   ├── auth.py         # Authentication logic
│   │   ├── config.py       # Configuration
│   │   ├── database.py     # Database connection
│   │   └── s3_client.py    # MinIO client
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── services/       # API services
│   │   ├── App.js
│   │   └── index.js
│   ├── Dockerfile
│   └── package.json
├── flyway/                 # Database migrations
│   ├── sql/
│   │   ├── V1__create_users_table.sql
│   │   └── V2__create_html_files_table.sql
│   └── conf/
│       └── flyway.conf
├── nginx/                  # Nginx configuration
│   └── nginx.conf
└── docker-compose.yml
```

## Development

### Backend Development

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development

```bash
cd frontend
npm install
npm start
```

## Environment Variables

Backend environment variables (set in docker-compose.yml):
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT secret key
- `MINIO_ENDPOINT` - MinIO endpoint
- `MINIO_ACCESS_KEY` - MinIO access key
- `MINIO_SECRET_KEY` - MinIO secret key
- `MINIO_BUCKET` - MinIO bucket name

## License

MIT
