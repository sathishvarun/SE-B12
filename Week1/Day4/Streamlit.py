import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Student Grade System",
    page_icon="🎓"
)

# Title
st.title("🎓 Student Grade System")
st.write("Enter student marks to calculate the grade.")

# Student name
student_name = st.text_input("Student Name")

st.subheader("Enter Marks")

# Subject marks
tamil = st.number_input(
    "Tamil",
    min_value=0,
    max_value=100,
    value=0
)

english = st.number_input(
    "English",
    min_value=0,
    max_value=100,
    value=0
)

maths = st.number_input(
    "Mathematics",
    min_value=0,
    max_value=100,
    value=0
)

science = st.number_input(
    "Science",
    min_value=0,
    max_value=100,
    value=0
)

social = st.number_input(
    "Social Science",
    min_value=0,
    max_value=100,
    value=0
)


# Calculate button
if st.button("Calculate Grade"):

    # Check student name
    if student_name == "":
        st.warning("Please enter the student name.")

    else:

        # Calculate total
        total = (
            tamil
            + english
            + maths
            + science
            + social
        )

        # Calculate average
        average = total / 5

        # Grade calculation
        if average >= 90:
            grade = "A+"
        elif average >= 80:
            grade = "A"
        elif average >= 70:
            grade = "B"
        elif average >= 60:
            grade = "C"
        elif average >= 50:
            grade = "D"
        else:
            grade = "F"


        # Pass / Fail
        # Every subject must have 35 or above
        if (
            tamil >= 35
            and english >= 35
            and maths >= 35
            and science >= 35
            and social >= 35
        ):
            result = "PASS"
        else:
            result = "FAIL"


        # Display result
        st.success(f"Results for {student_name}")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Marks", total)

        with col2:
            st.metric("Average", f"{average:.2f}")

        with col3:
            st.metric("Grade", grade)


        # Display Pass / Fail
        st.write("### Result")

        if result == "PASS":
            st.success("🎉 PASS")
        else:
            st.error("❌ FAIL")


        # Display subject marks
        st.write("### Subject Marks")

        st.write(f"Tamil: {tamil}")
        st.write(f"English: {english}")
        st.write(f"Mathematics: {maths}")
        st.write(f"Science: {science}")
        st.write(f"Social Science: {social}")