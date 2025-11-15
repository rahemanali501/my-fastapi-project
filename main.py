from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles 
import os  


from routes.student_routes import router as student_router


UPLOAD_DIR = "uploads"  
# Ensure uploads directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

# FastAPI App Initialization
app = FastAPI(title="College Management System API")


app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


app.include_router(student_router, prefix="/api")

# --- Root URL (Home Page) ---

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