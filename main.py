# main.py (simplified)
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes import router as students_router

app = FastAPI()

# ensure UPLOAD_DIR same as used in router (via env var)
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# mount static files so /uploads/<file> serves uploaded files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# include your router
app.include_router(students_router)






# Basic version without file upload
# from fastapi import FastAPI
# from routes.student_routes import router as student_router

# app = FastAPI(title="College Management System API")

# # Routes include
# app.include_router(student_router, prefix="/api")

# @app.get("/student")
# def home():
#     return {"message": "Welcome to College Management System API"}