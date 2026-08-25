from faker import Faker
import csv
import random

fake = Faker()
Faker.seed(42)
random.seed(42)

# Step1: Read the existing employees so we can link vendors to them
employee_ids = []
with open("employees.csv","r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        employee_ids.append(row["employee_id"])

# Step 2: Generate 30 vendors
vendors = []
for i in range(1,31):
    vendor_id = f"VEN{i:03d}"
    vendors.append({
        "vendor_id": vendor_id,
        "vendor_name" : fake.company(),
        "phone": fake.phone_number(),
        "address": fake.address().replace("\n", ", "),
        "bank_account": fake.iban(),
        "created_by_employee_id": random.choice(employee_ids)
    }) 

# Step 3: Save to CSV
with open("vendors.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["vendor_id","vendor_name","phone","address","bank_account","created_by_employee_id"])
    writer.writeheader()
    writer.writerows(vendors)

print(f"Created {len(vendors)} vendors -> vendors.csv")

