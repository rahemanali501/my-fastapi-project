import os, shutil
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from db.database import get_connection

router = APIRouter()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# 1. POST (YE CODE AAPKA PEHLE SE SAHI THA)
@router.post("/students")
def add_student(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    gender: str = Form(...),
    date_of_birth: str = Form(...),
    photo: UploadFile = File(None)
):
    conn = get_connection()
    if not conn:
        raise HTTPException(500, "Database connection failed")

    # cursor() ko dictionary=True ke saath istemaal karein (agar get_connection nahi karta)
    # Taaki data { 'key': 'value' } format mein mile
    # Hum assume kar rahe hain ki aapne db/database.py mein DictCursor set kar diya hai
    cursor = conn.cursor() 
    saved_filename = None
    student_id = None

    try:
        cursor.execute(
            "INSERT INTO `std` (name, email, gender, date_of_birth, photo) VALUES (%s, %s, %s, %s, %s)",
            (name, email, gender, date_of_birth, None)
        )
        conn.commit()
        student_id = cursor.lastrowid

        if photo and photo.filename:
            saved_filename = f"{student_id}_{os.path.basename(photo.filename)}"
            save_path = os.path.join(UPLOAD_DIR, saved_filename)

            try:
                with open(save_path, "wb") as f:
                    photo.file.seek(0)
                    shutil.copyfileobj(photo.file, f)
            except Exception as save_exc:
                cursor.execute("DELETE FROM `std` WHERE id=%s", (student_id,))
                conn.commit()
                raise HTTPException(500, "Failed to save photo") from save_exc
            finally:
                try:
                    photo.file.close()
                except:
                    pass

            cursor.execute("UPDATE `std` SET photo=%s WHERE id=%s", (saved_filename, student_id))
            conn.commit()

        url = str(request.base_url).rstrip("/")
        return {
            "Message": "Student Added Successfully",
            "id": student_id,
            "name": name, # Return name
            "email": email, # Return email
            "photo": saved_filename,
            "photo_url": f"{url}/uploads/{saved_filename}" if saved_filename else None
        }

    except Exception as e:
        conn.rollback()
        if saved_filename:
            fp = os.path.join(UPLOAD_DIR, saved_filename)
            if os.path.exists(fp):
                os.remove(fp)
        if student_id:
            cursor.execute("DELETE FROM `std` WHERE id=%s", (student_id,))
            conn.commit()
        raise HTTPException(500, str(e))

    finally:
        cursor.close()
        conn.close()


# ==========================================
# 2. GET One Student (FIXED)
# ==========================================
@router.get("/students/{student_id}")
def get_student(student_id: int, request: Request):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor() 
    try:

        cursor.execute(
            "SELECT id, name, email, gender, date_of_birth, photo FROM `std` WHERE id=%s",
            (student_id,)
        )
        # fetchone() ab dictionary return karega
        student = cursor.fetchone()
        print("DEBUG raw row from DB:", student)

        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

 
        photo_url = None
        photo_filename = student.get("photo") # dict se photo lein
        
        if photo_filename:
            safe_name = os.path.basename(str(photo_filename))
            base = str(request.base_url).rstrip("/")
            photo_url = f"{base}/uploads/{safe_name}"

  
        student["photo_url"] = photo_url
        

        if student.get("date_of_birth"):
            student["date_of_birth"] = str(student["date_of_birth"])

        return student 

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print("TRACEBACK:", traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        if cursor is not None:
            try: cursor.close()
            except: pass
        try: conn.close()
        except: pass


# ==========================================
# 3. GET All Students
# ==========================================
@router.get("/students")
def get_all_students(request: Request):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor()
    try:

        cursor.execute("SELECT id, name, email, gender, date_of_birth, photo FROM `std`")
        students = cursor.fetchall()

        base = str(request.base_url).rstrip("/")

        for student in students:
           
            photo_url = None
            photo_filename = student.get("photo")
            
            if photo_filename:
                safe_name = os.path.basename(str(photo_filename))
                photo_url = f"{base}/uploads/{safe_name}"

            student["photo_url"] = photo_url 
            
            
            if student.get("date_of_birth"):
                student["date_of_birth"] = str(student["date_of_birth"])

        return {
            "count": len(students),
            "students": students
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


# ==========================================
# 4. UPDATE Student
# ==========================================
@router.put("/students/{student_id}")
def update_student(student_id: int,
                   request: Request, 
                   name: str = Form(None),
                   email: str = Form(None),
                   gender: str = Form(None),
                   date_of_birth: str = Form(None),
                   photo: UploadFile = File(None)):
    conn = get_connection()
    if not conn: raise HTTPException(500, "DB failed")
    cur = conn.cursor()
    

    cur.execute("SELECT photo FROM `std` WHERE id=%s", (student_id,))
    row = cur.fetchone()
    if not row: raise HTTPException(404, "Not found")
    old_photo = row.get("photo") 

    new_name = None
    if photo and photo.filename: 
        new_name = f"{student_id}_{os.path.basename(photo.filename)}"
        path = os.path.join(UPLOAD_DIR, new_name)
        try:
            with open(path, "wb") as f: 
                photo.file.seek(0)
                shutil.copyfileobj(photo.file, f)
        except:
            if os.path.exists(path): os.remove(path)
            raise HTTPException(500, "Failed to save photo")
        finally:
            if photo: 
                try: photo.file.close()
                except: pass

    parts, vals = [], []
    for k,v in (("name", name), ("email", email), ("gender", gender), ("date_of_birth", date_of_birth)):
        if v is not None:
            parts.append(f"{k}=%s"); vals.append(v)
    if new_name:
        parts.append("photo=%s"); vals.append(new_name)
    if not parts:
        cur.close(); conn.close()
        raise HTTPException(400, "No fields to update")
    vals.append(student_id)
    
    try:
      
        cur.execute(f"UPDATE `std` SET {', '.join(parts)} WHERE id=%s", tuple(vals))
        conn.commit()
    except:
        conn.rollback()
        if new_name:
            try: os.remove(os.path.join(UPLOAD_DIR, new_name))
            except: pass
        raise HTTPException(500, "DB update failed")

    if new_name and old_photo:
        try:
            p = os.path.join(UPLOAD_DIR, os.path.basename(str(old_photo)))
            if os.path.exists(p): os.remove(p)
        except: pass

   
    cur.execute("SELECT * FROM `std` WHERE id=%s", (student_id,))
    updated_student = cur.fetchone()
    
    
    url = str(request.base_url).rstrip("/")
    photo_filename = updated_student.get("photo")
    if photo_filename:
        updated_student["photo_url"] = f"{url}/uploads/{os.path.basename(photo_filename)}"
    else:
        updated_student["photo_url"] = None
    
    if updated_student.get("date_of_birth"):
            updated_student["date_of_birth"] = str(updated_student["date_of_birth"])

    cur.close(); conn.close()
    return {
        "Message":"Updated",
        "student": updated_student
    }


# ==========================================
# 5. DELETE Student 
# ==========================================
@router.delete("/students/{student_id}")
def delete_student(student_id: int):
    conn = get_connection()
    if not conn: raise HTTPException(500, "DB failed")
    cur = conn.cursor()
    
    cur.execute("SELECT photo FROM `std` WHERE id=%s", (student_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        raise HTTPException(404, "Not found")
    old_photo = row.get("photo") 

    try:
        cur.execute("DELETE FROM `std` WHERE id=%s", (student_id,))
        conn.commit()
        if old_photo:
            try:
                fp = os.path.join(UPLOAD_DIR, os.path.basename(str(old_photo)))
                if os.path.exists(fp): os.remove(fp)
            except: pass
    except Exception as e:
        conn.rollback()
        raise HTTPException(500, "Delete failed")
    finally:
        cur.close(); conn.close()

    return {"Message":"Deleted","id":student_id, "deleted_photo": old_photo}




# ____________________________________________________________________________________














# Basic version without dynamic updates and photo upload

# from fastapi import APIRouter, HTTPException
# from db.database import get_connection
# from models.student import Student

# router = APIRouter()

# #1. ADD Student 
# @router.post("/students")
# def add_students(student: Student):
#     conn = get_connection()
#     if conn:
#         try:
#             cursor =conn.cursor()
#             query = """
#                  INSERT INTO std (name, email, gender, date_of_birth)
#                  VALUES (%s, %s, %s, %s)"""
#             cursor.execute(query, (
#                 student.name,
#                 student.email,
#                 student.gender,
#                 student.date_of_birth
#               ))
#             conn.commit()
#             student_id = cursor.lastrowid
#             return {"Message": "Student Added Successfully", "id": student_id}
#         except Exception as e:
#             conn.rollback()
#             raise HTTPException(status_code=500, detail=str(e))
#         finally:
#             cursor.close()
#             conn.close()    
#     raise HTTPException(status_code=500, detail="Database connection failed")



# # API to UPDATE Student
# @router.put("/students/{student_id}")
# def update_student(student_id: int, student: Student):
#     conn = get_connection()
#     if conn:
#         try:
#             cursor = conn.cursor()

#             # convert only provided fields
#             data = student.dict(exclude_unset=True)

#             if not data:
#                 raise HTTPException(status_code=400, detail="No fields provided for update")

#             # build dynamic SET clause
#             fields = [f"{key} = %s" for key in data.keys()]
#             values = list(data.values())
#             values.append(student_id)

#             # CORRECT QUERY using f-string
#             query = f"UPDATE std SET {', '.join(fields)} WHERE id = %s"

#             # CORRECT EXECUTION
#             cursor.execute(query, tuple(values))
#             conn.commit()

#             if cursor.rowcount == 0:
#                 raise HTTPException(status_code=404, detail="Student not found")

#             return {"Message": "Student Updated Successfully", "id": student_id}

#         except Exception as e:
#             conn.rollback()
#             raise HTTPException(status_code=500, detail=str(e))

#         finally:
#             cursor.close()
#             conn.close()

#     raise HTTPException(status_code=500, detail="Database connection failed")



# # API to DELETE Student
# @router.delete("/students/{student_id}")
# def delete_student(student_id: int):
#     conn = get_connection()
#     if conn:
#         try:
#             cursor = conn.cursor()
#             query = "DELETE FROM std WHERE id = %s"
#             cursor.execute(query, (student_id,))
#             conn.commit()

#             if cursor.rowcount == 0:
#                 raise HTTPException(status_code=404, detail="Student not found")
            
#             return {"Message": "Student Deleted Successfully","id": student_id }
        
#         except Exception as e:
#             conn.rollback()
#             raise HTTPException(status_code=500, detail=str(e))
#         finally:
#             cursor.close()
#             conn.close()
#     raise HTTPException(status_code=500, detail="Database connection failed")



# # API to GET One Student
# @router.get("/students/{student_id}")
# def view_single_student(student_id: int):
#     conn = get_connection()
#     if conn:
#         try:
#             cursor = conn.cursor()
#             cursor.execute("SELECT * FROM std where id = %s",(student_id,))
#             student = cursor.fetchone()
#             if not student:
#                 raise HTTPException(status_code=404, detail="Student not found")
#             return student
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=str(e))
#         finally:
#             cursor.close()
#             conn.close()
#     raise HTTPException(status_code=500, detail="Database connection failed")



# # API to GET All Students
# @router.get("/students")
# def view_all_student():
#     conn = get_connection()
#     if conn:
#         try:
#             cursor = conn.cursor()
#             cursor.execute("SELECT * FROM std")
#             students = cursor.fetchall()

#             if not students:
#                 raise HTTPException(status_code=404, detail="No students found")
            
#             return students
#         except Exception as e:
#             raise HTTPException(status_code=500, detail=str(e))

#         finally:
#             cursor.close()
#             conn.close()        

#     raise HTTPException(status_code=500, detail ="Database connection failed")