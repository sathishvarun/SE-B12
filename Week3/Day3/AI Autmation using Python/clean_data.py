
import re
import pandas as pd


def clean_text(value):
    """Remove leading, trailing, and repeated spaces."""
    if pd.isna(value):
        return value

    value = re.sub(r"\s+", " ", str(value)).strip()
    return value


def clean_name(value):
    """Convert names to title case."""
    if pd.isna(value):
        return value

    return clean_text(value).title()


def clean_email(value):
    """Trim spaces and convert email addresses to lowercase."""
    if pd.isna(value):
        return value

    return clean_text(value).lower()


def clean_state(value):
    """Standardize state names without guessing missing values."""
    if pd.isna(value):
        return value

    value = clean_text(value)

    state_mapping = {
        "tamil nadu": "Tamil Nadu",
        "karnataka": "Karnataka",
        "kerala": "Kerala",
        "maharashtra": "Maharashtra",
        "andhra pradesh": "Andhra Pradesh",
        "telangana": "Telangana",
        "uttar pradesh": "Uttar Pradesh",
        "west bengal": "West Bengal",
        "gujarat": "Gujarat",
        "rajasthan": "Rajasthan",
    }

    return state_mapping.get(value.lower(), value.title())


def clean_department(value):
    """Standardize common department names."""
    if pd.isna(value):
        return value

    value = clean_text(value)

    department_mapping = {
        "it": "Information Technology",
        "hr": "Human Resources",
        "information technology": "Information Technology",
        "human resources": "Human Resources",
        "finance": "Finance",
        "marketing": "Marketing",
        "sales": "Sales",
        "operations": "Operations",
    }

    return department_mapping.get(value.lower(), value.title())


def validate_email(value):
    """Check the basic format of an email address."""
    if pd.isna(value) or not str(value).strip():
        return False

    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

    return bool(re.fullmatch(pattern, str(value).strip()))


def clean_indian_mobile(value):
    """
    Normalize a valid Indian mobile number to +91XXXXXXXXXX.
    Return the original value if the number is invalid or ambiguous.
    """
    if pd.isna(value) or not str(value).strip():
        return value

    original = clean_text(value)
    digits = re.sub(r"\D", "", original)

    if len(digits) == 10:
        digits = "91" + digits
    elif len(digits) == 11 and digits.startswith("0"):
        digits = "91" + digits[1:]
    elif len(digits) == 12 and digits.startswith("91"):
        pass
    else:
        return original

    if re.fullmatch(r"91[6-9]\d{9}", digits):
        return "+" + digits

    return original


def clean_employee_data(df):
    """Clean supported columns while preserving the other columns."""
    df = df.copy()

    # Normalize column headers for matching.
    # Original column names are retained in the output.
    column_lookup = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    # Clean all text columns by trimming extra spaces.
    for column in df.columns:
        if df[column].dtype == "object":
            df[column] = df[column].map(clean_text)

    # Apply cleaning to columns that exist in the workbook.
    name_columns = [
        "employee name",
        "first name",
        "last name",
        "manager name",
        "emergency contact name",
    ]

    for name in name_columns:
        if name in column_lookup:
            column = column_lookup[name]
            df[column] = df[column].map(clean_name)

    email_columns = ["email address", "personal email"]

    for name in email_columns:
        if name in column_lookup:
            column = column_lookup[name]
            df[column] = df[column].map(clean_email)

    if "state" in column_lookup:
        column = column_lookup["state"]
        df[column] = df[column].map(clean_state)

    if "department" in column_lookup:
        column = column_lookup["department"]
        df[column] = df[column].map(clean_department)

    phone_columns = [
        "phone number",
        "mobile number",
        "emergency contact phone",
    ]

    for name in phone_columns:
        if name in column_lookup:
            column = column_lookup[name]
            df[column] = df[column].map(clean_indian_mobile)

    # Add an email validation column if a primary email column exists.
    if "email address" in column_lookup:
        email_column = column_lookup["email address"]
        df["Email Valid"] = df[email_column].map(validate_email)

    return df
