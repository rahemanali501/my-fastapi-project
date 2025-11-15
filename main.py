import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from db.database import Base, engine 
# Make sure to import your student router
from routes import student_routes 

# Create all database tables (if not already created)
# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Student API",
    description="API for managing students",
    version="1.0.0"
)

# === YAHAN HAI FIX (HERE IS THE FIX) ===

# 1. Define the uploads directory path
UPLOAD_DIR = "uploads"
# Create the directory if it doesn't exist on the server
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 2. "Mount" the directory
# This tells FastAPI: "Any URL that starts with '/uploads' 
# should be served as a static file from the directory named 'uploads'."
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# === FIX ENDS HERE ===


# Include your student router
# Make sure the prefix is correct
app.include_router(student_routes.router, prefix="/api")


@app.get("/")
def read_root():
    return {"message": "Welcome to the Student API!"}







# Basic version without file upload
# from fastapi import FastAPI
# from routes.student_routes import router as student_router

# app = FastAPI(title="College Management System API")

# # Routes include
# app.include_router(student_router, prefix="/api")

# @app.get("/student")
# def home():
#     return {"message": "Welcome to College Management System API"}