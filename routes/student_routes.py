import os, shutil
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from db.database import get_connection

router = APIRouter()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# 1. ADD Student with photo upload
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

    cursor = conn.cursor()
    saved_filename = None
    student_id = None

    try:
        # Insert student first (photo = None)
        cursor.execute(
            "INSERT INTO std (name,email,gender,date_of_birth,photo) VALUES (%s,%s,%s,%s,%s)",
            (name, email, gender, date_of_birth, None)
        )
        conn.commit()
        student_id = cursor.lastrowid

        # If photo provided, save & update
        if photo:
            saved_filename = f"{student_id}_{os.path.basename(photo.filename)}"
            save_path = os.path.join(UPLOAD_DIR, saved_filename)

            try:

                # save file into uploads folder
                with open(save_path, "wb") as f:
                    shutil.copyfileobj(photo.file, f)
            except:
                
                # cleanup DB row if file save fails
                cursor.execute("DELETE FROM std WHERE id=%s", (student_id,))
                conn.commit()
                raise HTTPException(500, "Failed to save photo")

            # update student record with photo filename in photo column
            cursor.execute("UPDATE std SET photo=%s WHERE id=%s", (saved_filename, student_id))
            conn.commit()

        # Response
        url = str(request.base_url).rstrip("/")
        return {
            "Message": "Student Added Successfully",
            "id": student_id,
            "photo": saved_filename,
            # make full URL to access the photo in browser if uploaded if not then set to None
            "photo_url": f"{url}/uploads/{saved_filename}" if saved_filename else None
        }

    except Exception as e:
        conn.rollback()

        # remove file if created
        if saved_filename:
            fp = os.path.join(UPLOAD_DIR, saved_filename)
            if os.path.exists(fp):
                os.remove(fp)

        # remove row if inserted
        if student_id:
            cursor.execute("DELETE FROM std WHERE id=%s", (student_id,))
            conn.commit()

        raise HTTPException(500, str(e))

    finally:
        cursor.close()
        conn.close()


# 2. GET One Student with photo URL
@router.get("/students/{student_id}")
def get_student(student_id: int, request: Request):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = None
    try:
        cursor = conn.cursor()  # keep your cursor creation style
        cursor.execute(
            "SELECT id, name, email, gender, date_of_birth, photo FROM std WHERE id=%s",
            (student_id,)
        )
        row = cursor.fetchone()
        print("DEBUG raw row from DB:", row)

        if not row:
            raise HTTPException(status_code=404, detail="Student not found")

        # === handle both dict and tuple results without changing your overall logic ===
        if isinstance(row, dict):
            student_id_db = row.get("id")
            name = row.get("name")
            email = row.get("email")
            gender = row.get("gender")
            date_of_birth = row.get("date_of_birth")
            photo = row.get("photo")
        else:
            # tuple fallback (same order as SELECT)
            student_id_db, name, email, gender, date_of_birth, photo = row


        # Build photo URL only if file exists (use absolute uploads path to avoid cwd issues)
        photo_url = None
        if photo:
            safe_name = os.path.basename(str(photo))
            uploads_path = os.path.abspath(UPLOAD_DIR)  # keep your UPLOAD_DIR but resolve absolute path
            file_path = os.path.join(uploads_path, safe_name)
            print("DEBUG checking file_path:", file_path, "exists?", os.path.exists(file_path))

            if os.path.exists(file_path):
                base = str(request.base_url).rstrip("/")
                photo_url = f"{base}/uploads/{safe_name}"
            else:
                # file missing on disk
                print("DEBUG: photo file missing on disk:", file_path)
                photo = None
                photo_url = None

        return {
            "id": student_id_db,
            "name": name,
            "email": email,
            "gender": gender,
            "date_of_birth": str(date_of_birth) if date_of_birth else None,
            "photo": photo,
            "photo_url": photo_url
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print("TRACEBACK:", traceback.format_exc())
        # return a generic 500 (avoid leaking internals)
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        if cursor is not None:
            try:
                cursor.close()
            except:
                pass
        try:
            conn.close()
        except:
            pass






# 3. GET All Students with photo URLs
@router.get("/students")
def get_all_students(request: Request):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor()
    try:
        # No WHERE condition
        cursor.execute("SELECT id, name, email, gender, date_of_birth, photo FROM std")
        rows = cursor.fetchall()

        students = []
        base = str(request.base_url).rstrip("/")

        for row in rows:
            try:
                # dict type
                sid = row["id"]
                name = row.get("name")
                email = row.get("email")
                gender = row.get("gender")
                dob = row.get("date_of_birth")
                photo = row.get("photo")
            except:
                # tuple type
                sid, name, email, gender, dob, photo = row

            # Build photo URL
            photo_url = None
            if photo:
                safe_name = os.path.basename(photo)
                file_path = os.path.join(UPLOAD_DIR, safe_name)
                if os.path.exists(file_path):
                    photo_url = f"{base}/uploads/{safe_name}"
                else:
                    photo = None

            students.append({
                "id": sid,
                "name": name,
                "email": email,
                "gender": gender,
                "date_of_birth": str(dob) if dob else None,
                "photo": photo,
                "photo_url": photo_url
            })

        return {
            "count": len(students),
            "students": students
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()





# 4. UPDATE Student with optional photo replacement
@router.put("/students/{student_id}")
def update_student(student_id: int,
                   name: str = Form(None),
                   email: str = Form(None),
                   gender: str = Form(None),
                   date_of_birth: str = Form(None),
                   photo: UploadFile = File(None)):
    conn = get_connection()
    if not conn: raise HTTPException(500, "DB failed")
    cur = conn.cursor()
    # get old photo
    cur.execute("SELECT photo FROM std WHERE id=%s", (student_id,))
    row = cur.fetchone()
    if not row: raise HTTPException(404, "Not found")
    old_photo = (row.get("photo") if isinstance(row, dict) else row[0])

    # save new photo first (if provided)
    new_name = None
    if photo:
        new_name = f"{student_id}_{os.path.basename(photo.filename)}"
        path = os.path.join(UPLOAD_DIR, new_name)
        try:
            with open(path, "wb") as f: shutil.copyfileobj(photo.file, f)
        except:
            if os.path.exists(path): os.remove(path)
            raise HTTPException(500, "Failed to save photo")

    # build update
    parts, vals = [], []
    for k,v in (("name", name), ("email", email), ("gender", gender), ("date_of_birth", date_of_birth)):
        if v is not None:
            parts.append(f"{k}=%s"); vals.append(v)
    if new_name:
        parts.append("photo=%s"); vals.append(new_name)
    if not parts:
        raise HTTPException(400, "No fields to update")
    vals.append(student_id)
    try:
        cur.execute(f"UPDATE std SET {', '.join(parts)} WHERE id=%s", tuple(vals))
        conn.commit()
    except:
        conn.rollback()
        if new_name:
            try: os.remove(os.path.join(UPLOAD_DIR, new_name))
            except: pass
        raise HTTPException(500, "DB update failed")

    # remove old file if replaced
    if new_name and old_photo:
        try:
            p = os.path.join(UPLOAD_DIR, os.path.basename(str(old_photo)))
            if os.path.exists(p): os.remove(p)
        except: pass

    cur.close(); conn.close()
    return {"Message":"Updated","id":student_id}




# Minimal DELETE (deletes DB row and photo file)
@router.delete("/students/{student_id}")
def delete_student(student_id: int):
    conn = get_connection()
    if not conn: raise HTTPException(500, "DB failed")
    cur = conn.cursor()
    cur.execute("SELECT photo FROM std WHERE id=%s", (student_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        raise HTTPException(404, "Not found")
    old_photo = (row.get("photo") if isinstance(row, dict) else row[0])

    try:
        cur.execute("DELETE FROM std WHERE id=%s", (student_id,))
        conn.commit()
        # delete file
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

    return {"Message":"Deleted","id":student_id}




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