from typing import Optional
from pydantic import BaseModel
from datetime import date, datetime

class Student(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None        # 'Male', 'Female', or 'Other'
    date_of_birth: Optional[date] = None
    created_at: Optional[datetime] = None
    photo: Optional[str] = None        # filename (e.g. "Raheman_profile.jpg") or URL
















# _____________________________________________________________________________________







# Basic CRUD Student model without photo upload

# from typing import Optional
# from pydantic import BaseModel
# from datetime import date, datetime

# class Student(BaseModel):
#     id: Optional[int] = None
#     name: Optional[str] = None
#     email: Optional[str] 
#     gender: Optional[str] = None  # 'Male', 'Female', or 'Other'
#     date_of_birth: Optional[date] = None
#     created_at: Optional[datetime] = None