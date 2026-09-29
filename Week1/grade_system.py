
# Grade System
# This program accepts a mark from 0 to 100
# and prints the corresponding letter grade.

try:
    mark = float(input("Enter your mark (0-100): "))

    if mark < 0 or mark > 100:
        print("Invalid mark. Please enter a number between 0 and 100.")
    elif mark >= 90:
        grade = "A"
        print(f"Mark: {mark} | Grade: {grade}")
    elif mark >= 80:
        grade = "B"
        print(f"Mark: {mark} | Grade: {grade}")
    elif mark >= 70:
        grade = "C"
        print(f"Mark: {mark} | Grade: {grade}")
    elif mark >= 60:
        grade = "D"
        print(f"Mark: {mark} | Grade: {grade}")
    else:
        grade = "E"
        print(f"Mark: {mark} | Grade: {grade}")

except ValueError:
    print("Invalid input. Please enter a number.")

