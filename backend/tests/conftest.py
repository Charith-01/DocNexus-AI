"""Safe test configuration that never targets a real MongoDB database."""

import os


os.environ["APP_NAME"] = "DocNexus AI"
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "false"
os.environ["MONGODB_URI"] = "mongodb://127.0.0.1:27017/?connect=false"
os.environ["MONGODB_DB_NAME"] = "docnexus_test"
os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-not-for-production"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "5"
os.environ["MAX_UPLOAD_SIZE_MB"] = "1"
os.environ["FRONTEND_ORIGIN"] = "http://localhost:5173"
