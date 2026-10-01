from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


# Data model for POST request
class Student(BaseModel):
    name: str
    age: int
    course: str


# GET - Welcome message
@app.get("/")
def home():
    return {
        "message": "Welcome to Student API"
    }


# GET - Get student information
@app.get("/student/{student_id}")
def get_student(student_id: int):
    return {
        "student_id": student_id,
        "message": f"Getting information for student {student_id}"
    }


# POST - Create student
@app.post("/student")
def create_student(student: Student):
    return {
        "message": "Student created successfully",
        "student": student
    }