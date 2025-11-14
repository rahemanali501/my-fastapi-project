from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

from routes.student_routes import router as student_router

# directory where uploaded files will be saved
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)  # create folder if not exists

app = FastAPI(title="College Management System API")

# mount uploads folder so files are served at /uploads/{filename}
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# include your student router under /api
app.include_router(student_router, prefix="/api")

@app.get("/student")
def home():
    return {"message": "Welcome to College Management System API"}









# Basic version without file upload
# from fastapi import FastAPI
# from routes.student_routes import router as student_router

# app = FastAPI(title="College Management System API")

# # Routes include
# app.include_router(student_router, prefix="/api")

# @app.get("/student")
# def home():
#     return {"message": "Welcome to College Management System API"}