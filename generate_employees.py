from faker import Faker
import csv
import random
from datetime import datetime, timedelta

fake = Faker()
Faker.seed(42)
random.seed(42)

roles_by_department = {
    "Finance": ["Finance Executive", "Finance Manager", "Accountant"],
    "Procurement": ["Procurement Officer", "Procurement Manager", "Procurement Intern"],
    "Operations": ["Operations Executive", "Operations Manager"],
    "IT": ["IT Support", "IT Manager"],
    "Sales": ["Sales Executive", "Sales Manager"]
}

employees = []

for i in range(1, 101):  # scaled up from 20 to 100
    emp_id = f"EMP{i:03d}"
    department = random.choice(list(roles_by_department.keys()))
    role = random.choice(roles_by_department[department])
    name = fake.name()

    join_date = fake.date_between(start_date="-3y", end_date="today")

    employees.append({
        "employee_id": emp_id,
        "name": name,
        "email": f"{name.lower().replace(' ', '.')}@sentinelcorp.com",
        "phone": fake.phone_number(),
        "department": department,
        "role": role,
        "join_date": join_date.strftime("%Y-%m-%d")
    })

with open("employees.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["employee_id", "name", "email", "phone", "department", "role", "join_date"])
    writer.writeheader()
    writer.writerows(employees)

print(f"Created {len(employees)} employees -> employees.csv")