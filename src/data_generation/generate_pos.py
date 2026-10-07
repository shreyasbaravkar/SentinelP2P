from faker import Faker
import csv
import random
from datetime import datetime, timedelta

fake = Faker()
Faker.seed(42)
random.seed(42)

ITEM_CATEGORIES = ["IT Hardware", "Office Supplies", "Catering", "Logistics",
                    "Software Licensing", "Cleaning Services", "Printing & Packaging"]

PAYMENT_TERMS = ["Net 15", "Net 30", "Net 45", "Net 60"]

# Read employees and vendors
employees = []
with open("../../data/employees.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        employees.append(row)

vendors = []
with open("../../data/vendors.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        vendors.append(row)

pos = []
start_date = datetime(2025, 1, 1)

for i in range(1, 701):  # scaled up from 104 to 700
    po_id = f"PO{i:04d}"
    random_days = random.randint(0, 600)
    po_date = start_date + timedelta(days=random_days)

    vendor = random.choice(vendors)
    creator = random.choice(employees)
    approver = random.choice(employees)  # usually different, but sometimes same (fraud signal)

    pos.append({
        "po_id": po_id,
        "vendor_id": vendor["vendor_id"],
        "amount": round(random.uniform(500, 25000), 2),
        "item_category": vendor["vendor_category"],  # matches vendor's category by default
        "date": po_date.strftime("%Y-%m-%d"),
        "created_by_employee_id": creator["employee_id"],
        "approved_by_employee_id": approver["employee_id"],
        "payment_terms": random.choice(PAYMENT_TERMS)
    })

fieldnames = ["po_id", "vendor_id", "amount", "item_category", "date",
              "created_by_employee_id", "approved_by_employee_id", "payment_terms"]

with open("../../data/purchase_orders.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(pos)

print(f"Created {len(pos)} purchase orders -> ../../data/purchase_orders.csv")