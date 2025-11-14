from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles  # Static files (jaise images) serve karne ke liye
import os  # Folder operations ke liye

# 'routes' folder se student_routes wali file import kar rahe hain
from routes.student_routes import router as student_router

# --- Upload Folder Setup ---
UPLOAD_DIR = "uploads"  # Files is folder mein save hongi
# Agar 'uploads' folder nahi hai, toh ye command use bana degi
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- FastAPI App Initialization ---
# Yahan se aapki main FastAPI app shuru hoti hai
app = FastAPI(title="College Management System API")

# --- Static Files (Uploads) Ko Serve Karna ---
# Isse 'uploads' folder mein padi files ko '/uploads/filename.jpg' jaise URL se access kar sakte hain
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# --- API Routes Ko Jodna ---
# 'student_routes.py' ke saare API endpoints (/api prefix ke saath) yahan jod rahe hain
app.include_router(student_router, prefix="/api")

# --- Root URL (Home Page) ---
# Ye Render ke health check ke liye zaroori hai.
# Isse 502 Bad Gateway error fix hota hai.
@app.get("/")
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