from faker import Faker
import csv
import random
from datetime import datetime, timedelta

fake = Faker()
Faker.seed(42)
random.seed(42)

VENDOR_CATEGORIES = ["IT Hardware", "Office Supplies", "Catering", "Logistics",
                      "Software Licensing", "Cleaning Services", "Printing & Packaging"]

# Read existing employees so we can link vendors to them
employees = []
with open("../../data/employees.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        employees.append(row)

vendors = []

for i in range(1, 301):  # scaled up from 32 to 300
    vendor_id = f"VEN{i:03d}"
    creator = random.choice(employees)
    vendor_name = fake.company()
    onboarding_date = fake.date_between(start_date="-2y", end_date="today")

    vendors.append({
        "vendor_id": vendor_id,
        "vendor_name": vendor_name,
        "email": f"contact@{vendor_name.lower().replace(' ', '').replace(',', '')[:15]}.com",
        "phone": fake.phone_number(),
        "address": fake.address().replace("\n", ", "),
        "bank_account": fake.iban(),
        "registration_number": fake.bothify(text="REG-########"),
        "vendor_category": random.choice(VENDOR_CATEGORIES),
        "onboarding_date": onboarding_date.strftime("%Y-%m-%d"),
        "has_contract": random.choice(["Yes", "No"]),
        "created_by_employee_id": creator["employee_id"]
    })

fieldnames = ["vendor_id", "vendor_name", "email", "phone", "address", "bank_account",
              "registration_number", "vendor_category", "onboarding_date", "has_contract",
              "created_by_employee_id"]

with open("../../data/vendors.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(vendors)

print(f"Created {len(vendors)} vendors -> ../../data/vendors.csv")