from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
from typing import List, Optional
import uuid
import io
import secrets
import bcrypt

from app.config import settings
from app.database import get_db
from app import models, schemas, auth
from app.s3_client import get_s3_client, ensure_bucket_exists

app = FastAPI(title="File Uploader API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    ensure_bucket_exists()

@app.post("/api/auth/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(
        (models.User.username == user.username) | (models.User.email == user.email)
    ).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/api/auth/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@app.post("/api/files/upload", response_model=schemas.HtmlFileResponse)
async def upload_file(
    file: UploadFile = File(...),
    is_locked: bool = False,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.html'):
        raise HTTPException(status_code=400, detail="Only HTML files are allowed")
    
    # Generate unique S3 key
    file_extension = ".html"
    s3_key = f"{current_user.id}/{uuid.uuid4()}{file_extension}"
    
    # Upload to MinIO
    s3_client = get_s3_client()
    file_content = await file.read()
    s3_client.put_object(
        Bucket=settings.MINIO_BUCKET,
        Key=s3_key,
        Body=file_content,
        ContentType='text/html'
    )
    
    # Save to database
    db_file = models.HtmlFile(
        filename=file.filename,
        original_filename=file.filename,
        s3_key=s3_key,
        is_locked=is_locked,
        owner_id=current_user.id
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)
    
    return db_file

@app.get("/api/files", response_model=List[schemas.HtmlFileResponse])
def list_files(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    files = db.query(models.HtmlFile).filter(models.HtmlFile.owner_id == current_user.id).all()
    return files

@app.get("/api/files/{file_id}")
def get_file(
    file_id: int,
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"GET /api/files/{file_id} - Token received: {token[:20] if token else 'None'}...")
    
    # Try to get user from token parameter
    if token:
        current_user = auth.verify_token(token, db)
        logger.info(f"User from token: {current_user.username if current_user else 'None'}")
    else:
        logger.warning("No token provided")
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    if not current_user:
        logger.warning("Invalid or expired token")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    db_file = db.query(models.HtmlFile).filter(
        models.HtmlFile.id == file_id,
        models.HtmlFile.owner_id == current_user.id
    ).first()
    
    if not db_file:
        logger.warning(f"File {file_id} not found for user {current_user.id}")
        raise HTTPException(status_code=404, detail="File not found")
    
    logger.info(f"Retrieving file {db_file.filename} from MinIO")
    
    # Get file from MinIO
    s3_client = get_s3_client()
    try:
        response = s3_client.get_object(Bucket=settings.MINIO_BUCKET, Key=db_file.s3_key)
        file_content = response['Body'].read()
        
        logger.info(f"File retrieved successfully, size: {len(file_content)} bytes")
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type='text/html',
            headers={"Content-Disposition": f"inline; filename={db_file.filename}"}
        )
    except Exception as e:
        logger.error(f"Error retrieving file from MinIO: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/files/{file_id}/lock", response_model=schemas.HtmlFileResponse)
def update_file_lock(
    file_id: int,
    lock_update: schemas.HtmlFileLockUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    db_file = db.query(models.HtmlFile).filter(
        models.HtmlFile.id == file_id,
        models.HtmlFile.owner_id == current_user.id
    ).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    db_file.is_locked = lock_update.is_locked
    db.commit()
    db.refresh(db_file)
    
    return db_file

@app.delete("/api/files/{file_id}")
def delete_file(
    file_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    db_file = db.query(models.HtmlFile).filter(
        models.HtmlFile.id == file_id,
        models.HtmlFile.owner_id == current_user.id
    ).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    if db_file.is_locked:
        raise HTTPException(status_code=400, detail="Cannot delete a locked file")
    
    # Delete from MinIO
    s3_client = get_s3_client()
    try:
        s3_client.delete_object(Bucket=settings.MINIO_BUCKET, Key=db_file.s3_key)
    except:
        pass
    
    # Delete from database
    db.delete(db_file)
    db.commit()
    
    return {"message": "File deleted successfully"}

@app.post("/api/files/{file_id}/share", response_model=schemas.PublicShareResponse)
def create_public_share(
    file_id: int,
    share_data: schemas.PublicShareCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Check if file exists and belongs to user
    db_file = db.query(models.HtmlFile).filter(
        models.HtmlFile.id == file_id,
        models.HtmlFile.owner_id == current_user.id
    ).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Generate unique share token
    share_token = secrets.token_urlsafe(32)
    
    # Hash password if provided
    password_hash = None
    if share_data.password:
        password_hash = bcrypt.hashpw(share_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Calculate expiration
    expires_at = None
    if share_data.expires_in_hours:
        expires_at = datetime.utcnow() + timedelta(hours=share_data.expires_in_hours)
    
    # Create share
    public_share = models.PublicShare(
        file_id=file_id,
        share_token=share_token,
        password_hash=password_hash,
        expires_at=expires_at,
        created_by=current_user.id
    )
    db.add(public_share)
    db.commit()
    db.refresh(public_share)
    
    # Build share URL
    share_url = f"{settings.BASE_URL}/share/{share_token}"
    
    return {
        "id": public_share.id,
        "file_id": public_share.file_id,
        "share_token": public_share.share_token,
        "share_url": share_url,
        "has_password": bool(password_hash),
        "expires_at": public_share.expires_at,
        "created_at": public_share.created_at
    }

@app.get("/api/files/{file_id}/shares", response_model=List[schemas.PublicShareResponse])
def list_file_shares(
    file_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Check if file belongs to user
    db_file = db.query(models.HtmlFile).filter(
        models.HtmlFile.id == file_id,
        models.HtmlFile.owner_id == current_user.id
    ).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    shares = db.query(models.PublicShare).filter(
        models.PublicShare.file_id == file_id
    ).all()
    
    result = []
    for share in shares:
        result.append({
            "id": share.id,
            "file_id": share.file_id,
            "share_token": share.share_token,
            "share_url": f"{settings.BASE_URL}/share/{share.share_token}",
            "has_password": bool(share.password_hash),
            "expires_at": share.expires_at,
            "created_at": share.created_at
        })
    
    return result

@app.delete("/api/shares/{share_id}")
def delete_share(
    share_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    share = db.query(models.PublicShare).filter(
        models.PublicShare.id == share_id,
        models.PublicShare.created_by == current_user.id
    ).first()
    
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")
    
    db.delete(share)
    db.commit()
    
    return {"message": "Share deleted successfully"}

@app.get("/share/{share_token}")
def access_shared_file(
    share_token: str,
    password: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # Find the share
    share = db.query(models.PublicShare).filter(
        models.PublicShare.share_token == share_token
    ).first()
    
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")
    
    # Check expiration
    if share.expires_at and share.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Share has expired")
    
    # Check password
    if share.password_hash:
        if not password:
            return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
<head>
    <title>Password Required</title>
    <style>
        body {{ font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; background: #f5f5f5; }}
        .container {{ background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 400px; width: 100%; }}
        h2 {{ margin-top: 0; color: #333; }}
        input {{ width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }}
        button {{ width: 100%; padding: 12px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }}
        button:hover {{ background: #45a049; }}
        .error {{ color: #c62828; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>🔒 Password Required</h2>
        <p>This shared file is protected with a password.</p>
        <form method="GET" action="/share/{share_token}">
            <input type="password" name="password" placeholder="Enter password" required autofocus>
            <button type="submit">Access File</button>
        </form>
        <div class="error" id="error"></div>
    </div>
    <script>
        const params = new URLSearchParams(window.location.search);
        if (params.get('error')) {{
            document.getElementById('error').textContent = 'Incorrect password';
        }}
    </script>
</body>
</html>
            """, status_code=200)
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), share.password_hash.encode('utf-8')):
            return HTMLResponse(content=f"""
<!DOCTYPE html>
<html>
<head><meta http-equiv="refresh" content="0;url=/share/{share_token}?error=1"></head>
</html>
            """, status_code=401)
    
    # Get the file
    db_file = db.query(models.HtmlFile).filter(
        models.HtmlFile.id == share.file_id
    ).first()
    
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Retrieve from MinIO
    s3_client = get_s3_client()
    try:
        response = s3_client.get_object(Bucket=settings.MINIO_BUCKET, Key=db_file.s3_key)
        file_content = response['Body'].read()
        
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type='text/html',
            headers={"Content-Disposition": f"inline; filename={db_file.filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy"}
