from faker import Faker 
import csv
import random

fake = Faker()
Faker.seed(42)
random.seed(42)

employees =[]

for i in range(1,21):
    emp_id = f"EMP{i:03d}"
    employees.append({ 
        "employee_id": emp_id, 
        "name": fake.name(),
        "phone": fake.phone_number(),
        "department": random.choice(["Finance","Procurement","Operations","IT","Sales"])
    })

with open("employees.csv", "w",newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["employee_id","name","phone","department"])
    writer.writeheader
    writer.writerows(employees)

print(f"Created{len(employees)} employees -> employees.csv")

