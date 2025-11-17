# students_router.py
import os
import shutil
import tempfile
import logging
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional
from db.database import get_connection

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter()

# Use env var so you can change in Render dashboard.
# Default to /tmp/uploads for Render testing (ephemeral).
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def save_upload(photo: UploadFile, student_id: int) -> str:
    """Write upload to UPLOAD_DIR atomically and return saved filename."""
    if not photo or not getattr(photo, "filename", None):
        raise ValueError("No photo provided")

    fname = os.path.basename(photo.filename)
    saved_name = f"{student_id}_{fname}"
    target = os.path.join(UPLOAD_DIR, saved_name)

    # create temp file in same dir for atomic replace
    fd, tmp_path = tempfile.mkstemp(dir=UPLOAD_DIR)
    os.close(fd)
    try:
        with open(tmp_path, "wb") as out_f:
            photo.file.seek(0)
            shutil.copyfileobj(photo.file, out_f)
        # atomic move
        os.replace(tmp_path, target)
        return saved_name
    finally:
        # cleanup tmp if still exists
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        try:
            photo.file.close()
        except Exception:
            pass


@router.get("/debug-files")
def debug_files():
    """Use logs to inspect upload dir contents and cwd on Render."""
    try:
        up = os.path.abspath(UPLOAD_DIR)
        return {
            "UPLOAD_DIR": up,
            "exists": os.path.exists(up),
            "cwd": os.getcwd(),
            "ls_cwd": os.listdir(os.getcwd())[:200],
            "ls_upload": os.listdir(up)[:200] if os.path.exists(up) else None,
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# 1. POST (add student)
@router.post("/students")
def add_student(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    gender: str = Form(...),
    date_of_birth: str = Form(...),
    photo: UploadFile = File(None),
):
    conn = get_connection()
    if not conn:
        raise HTTPException(500, "Database connection failed")

    cursor = conn.cursor()
    saved_filename: Optional[str] = None
    student_id = None

    try:
        cursor.execute(
            "INSERT INTO `std` (name, email, gender, date_of_birth, photo) VALUES (%s, %s, %s, %s, %s)",
            (name, email, gender, date_of_birth, None),
        )
        conn.commit()
        student_id = cursor.lastrowid

        if photo and getattr(photo, "filename", None):
            try:
                saved_filename = save_upload(photo, student_id)
            except Exception as save_exc:
                # rollback DB row
                try:
                    cursor.execute("DELETE FROM `std` WHERE id=%s", (student_id,))
                    conn.commit()
                except Exception:
                    conn.rollback()
                logger.exception("Failed to save uploaded photo")
                raise HTTPException(status_code=500, detail="Failed to save photo") from save_exc

            # save filename in DB
            cursor.execute("UPDATE `std` SET photo=%s WHERE id=%s", (saved_filename, student_id))
            conn.commit()

        base = str(request.base_url).rstrip("/")
        return {
            "Message": "Student Added Successfully",
            "id": student_id,
            "name": name,
            "email": email,
            "photo": saved_filename,
            "photo_url": f"{base}/uploads/{saved_filename}" if saved_filename else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        # cleanup any saved file
        if saved_filename:
            try:
                fp = os.path.join(UPLOAD_DIR, saved_filename)
                if os.path.exists(fp):
                    os.remove(fp)
            except Exception:
                pass
        if student_id:
            try:
                cursor.execute("DELETE FROM `std` WHERE id=%s", (student_id,))
                conn.commit()
            except Exception:
                conn.rollback()
        logger.exception("Error in add_student")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            cursor.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass


# 2. GET one student
@router.get("/students/{student_id}")
def get_student(student_id: int, request: Request):
    conn = get_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection failed")

    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id, name, email, gender, date_of_birth, photo FROM `std` WHERE id=%s",
            (student_id,),
        )
        student = cursor.fetchone()
        logger.debug("DEBUG raw row from DB: %s", student)

        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        photo_filename = student.get("photo")
        photo_url = None
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
    except Exception:
        logger.exception("Error fetching student")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        try:
            cursor.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass


# 3. GET all students
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
            photo_filename = student.get("photo")
            photo_url = None
            if photo_filename:
                safe_name = os.path.basename(str(photo_filename))
                photo_url = f"{base}/uploads/{safe_name}"
            student["photo_url"] = photo_url
            if student.get("date_of_birth"):
                student["date_of_birth"] = str(student["date_of_birth"])

        return {"count": len(students), "students": students}
    except Exception:
        logger.exception("Error fetching students")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    finally:
        try:
            cursor.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass


# 4. UPDATE student
@router.put("/students/{student_id}")
def update_student(
    student_id: int,
    request: Request,
    name: str = Form(None),
    email: str = Form(None),
    gender: str = Form(None),
    date_of_birth: str = Form(None),
    photo: UploadFile = File(None),
):
    conn = get_connection()
    if not conn:
        raise HTTPException(500, "DB failed")
    cur = conn.cursor()

    try:
        cur.execute("SELECT photo FROM `std` WHERE id=%s", (student_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Not found")
        old_photo = row.get("photo")

        new_name = None
        if photo and getattr(photo, "filename", None):
            try:
                new_name = save_upload(photo, student_id)
            except Exception:
                logger.exception("Failed to save new photo")
                raise HTTPException(500, "Failed to save photo")

        parts, vals = [], []
        for k, v in (("name", name), ("email", email), ("gender", gender), ("date_of_birth", date_of_birth)):
            if v is not None:
                parts.append(f"{k}=%s")
                vals.append(v)
        if new_name:
            parts.append("photo=%s")
            vals.append(new_name)
        if not parts:
            raise HTTPException(400, "No fields to update")

        vals.append(student_id)

        try:
            cur.execute(f"UPDATE `std` SET {', '.join(parts)} WHERE id=%s", tuple(vals))
            conn.commit()
        except Exception:
            conn.rollback()
            if new_name:
                try:
                    os.remove(os.path.join(UPLOAD_DIR, new_name))
                except Exception:
                    pass
            raise HTTPException(500, "DB update failed")

        if new_name and old_photo:
            try:
                p = os.path.join(UPLOAD_DIR, os.path.basename(str(old_photo)))
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

        cur.execute("SELECT id, name, email, gender, date_of_birth, photo FROM `std` WHERE id=%s", (student_id,))
        updated_student = cur.fetchone()

        base = str(request.base_url).rstrip("/")
        photo_filename = updated_student.get("photo")
        updated_student["photo_url"] = f"{base}/uploads/{os.path.basename(photo_filename)}" if photo_filename else None
        if updated_student.get("date_of_birth"):
            updated_student["date_of_birth"] = str(updated_student["date_of_birth"])

        return {"Message": "Updated", "student": updated_student}
    finally:
        try:
            cur.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass


# 5. DELETE student
@router.delete("/students/{student_id}")
def delete_student(student_id: int):
    conn = get_connection()
    if not conn:
        raise HTTPException(500, "DB failed")
    cur = conn.cursor()

    try:
        cur.execute("SELECT photo FROM `std` WHERE id=%s", (student_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Not found")
        old_photo = row.get("photo")

        try:
            cur.execute("DELETE FROM `std` WHERE id=%s", (student_id,))
            conn.commit()
            if old_photo:
                try:
                    fp = os.path.join(UPLOAD_DIR, os.path.basename(str(old_photo)))
                    if os.path.exists(fp):
                        os.remove(fp)
                except Exception:
                    pass
        except Exception:
            conn.rollback()
            raise HTTPException(500, "Delete failed")

        return {"Message": "Deleted", "id": student_id, "deleted_photo": old_photo}
    finally:
        try:
            cur.close()
        except:
            pass
        try:
            conn.close()
        except:
            pass





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