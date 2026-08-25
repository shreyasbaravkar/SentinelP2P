from faker import Faker
import csv
import random
from datetime import datetime, timedelta

fake = Faker()
Faker.seed(42)
random.seed(42)

# Step1: Read employee IDs
employee_ids = []
with open("employees.csv","r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        employee_ids.append(row["employee_id"])

# Step 2: Read vendor IDs
vendor_ids= []
with open("vendors.csv","r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        vendor_ids.append(row["vendor_id"])

# Step 3: Generate 100 POs
pos = []
start_date = datetime(2026, 1, 1)


for i in range (1,101):
    po_id = f"Po{i:04d}"
    random_days = random.randint(0,200)
    po_date= start_date + timedelta(days=random_days)


    pos.append({
        "po_id": po_id,
        "vendor_id": random.choice(vendor_ids),
        "amount": round(random.uniform(500,25000), 2),
        "date": po_date.strftime("%Y-%m-%d"),
        "created_by_employee_id": random.choice(employee_ids)
                })

# Step 4: Save to CSV
with open ("purchase_orders.csv","w",newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["po_id","vendor_id","amount","date","created_by_employee_id"])
    writer.writeheader()
    writer.writerows(pos)

print(f"Created {len(pos)} purchase orders -> purchase_orders.csv")
