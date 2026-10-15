
from pathlib import Path

import pandas as pd
from clean_data import clean_employee_data, validate_email


# 1. Define the input and output file paths
BASE_DIR = Path(__file__).parent

INPUT_FILE = BASE_DIR / "employee_sample_data_50_fields_50_records.xlsx"
OUTPUT_FILE = BASE_DIR / "employee_cleaned_output.xlsx"
SHEET_NAME = "Dirty Employee Data"


def validate_records(df):
    """Validate cleaned records and create an issue report."""
    issues_list = []
    email_column = "Email Address"
    phone_column = "Phone Number"
    salary_column = "Employee Salary"

    # Find duplicate email addresses, ignoring blanks.
    duplicate_emails = set()

    if email_column in df.columns:
        emails = df[email_column].dropna().astype(str).str.strip().str.lower()
        emails = emails[emails != ""]
        duplicate_emails = set(
            emails[emails.duplicated(keep=False)].tolist()
        )

    for index, row in df.iterrows():
        issues = []

        # Check required employee information.
        for column in ["Employee ID", "Employee Name"]:
            if column in df.columns and pd.isna(row[column]):
                issues.append(f"{column}: missing")

        # Validate email.
        if email_column in df.columns:
            email = row[email_column]

            if pd.isna(email) or str(email).strip() == "":
                issues.append("Email Address: missing")
            elif not validate_email(email):
                issues.append("Email Address: invalid format")
            elif str(email).strip().lower() in duplicate_emails:
                issues.append("Email Address: duplicate")

        # Validate normalized Indian mobile number.
        if phone_column in df.columns:
            phone = row[phone_column]

            if pd.isna(phone) or str(phone).strip() == "":
                issues.append("Phone Number: missing")
            elif not (
                len(str(phone)) == 13
                and str(phone).startswith("+91")
                and str(phone)[3] in "6789"
                and str(phone)[3:].isdigit()
            ):
                issues.append("Phone Number: invalid or needs review")

        # Validate salary without inventing missing values.
        if salary_column in df.columns:
            salary = row[salary_column]

            if pd.isna(salary) or str(salary).strip() == "":
                issues.append("Employee Salary: missing")
            else:
                try:
                    amount = float(str(salary).replace(",", "").strip())

                    if amount < 0:
                        issues.append("Employee Salary: negative")
                except (ValueError, TypeError):
                    issues.append("Employee Salary: non-numeric")

        issues_list.append({
            "Excel Row": index + 2,
            "Issues": "; ".join(issues) if issues else "None",
            "Record Status": "Needs Review" if issues else "Valid",
        })

    return pd.DataFrame(issues_list)


def main():
    # 2. Check that the input workbook exists.
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input Excel file not found: {INPUT_FILE}"
        )

    print("Reading the original Excel file...")

    # 3. Extract: read the source worksheet.
    original_df = pd.read_excel(
        INPUT_FILE,
        sheet_name=SHEET_NAME,
        dtype=object,
    )

    print(f"Rows read: {len(original_df)}")
    print(f"Columns read: {len(original_df.columns)}")

    # 4. Transform: clean the employee data.
    print("Cleaning employee data...")

    cleaned_df = clean_employee_data(original_df)

    # 5. Validate the cleaned records.
    print("Validating employee records...")

    validation_df = validate_records(cleaned_df)

    # 6. Add the validation results to the cleaned data.
    cleaned_df["Cleaning Issues"] = validation_df["Issues"].values
    cleaned_df["Record Status"] = validation_df["Record Status"].values

    # 7. Prepare a summary.
    valid_count = (
        validation_df["Record Status"] == "Valid"
    ).sum()

    review_count = (
        validation_df["Record Status"] == "Needs Review"
    ).sum()

    summary_df = pd.DataFrame({
        "Metric": [
            "Input file",
            "Worksheet",
            "Total records",
            "Total columns after cleaning",
            "Valid records",
            "Records needing review",
        ],
        "Value": [
            INPUT_FILE.name,
            SHEET_NAME,
            len(cleaned_df),
            len(cleaned_df.columns),
            int(valid_count),
            int(review_count),
        ],
    })

    # 8. Load: save everything into a new Excel workbook.
    with pd.ExcelWriter(OUTPUT_FILE, engine="openpyxl") as writer:
        cleaned_df.to_excel(
            writer,
            sheet_name="Cleaned Data",
            index=False,
        )

        validation_df.to_excel(
            writer,
            sheet_name="Validation Report",
            index=False,
        )

        summary_df.to_excel(
            writer,
            sheet_name="Summary",
            index=False,
        )

    print("\n" + "=" * 50)
    print("EMPLOYEE DATA CLEANING COMPLETED")
    print("=" * 50)
    print(f"Total records: {len(cleaned_df)}")
    print(f"Valid records: {valid_count}")
    print(f"Records needing review: {review_count}")
    print(f"Output saved to: {OUTPUT_FILE}")
    print("Original Excel file was not modified.")


if __name__ == "__main__":
    main()
