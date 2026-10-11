from faker import Faker
import csv
import random
from datetime import datetime, timedelta

fake = Faker()
Faker.seed(42)
random.seed(42)

PAYMENT_STATUSES = ["Paid", "Pending", "Overdue"]

employees = []
with open("../../data/employees.csv", "r", encoding="utf-8") as f:
    employees = list(csv.DictReader(f))

pos = []
with open("../../data/purchase_orders.csv", "r", encoding="utf-8") as f:
    pos = list(csv.DictReader(f))

# NEW: read contracts to respect agreed rates for clean invoices
vendor_contract_rate = {}
with open("../../data/contracts.csv", "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        vendor_contract_rate[row["vendor_id"]] = float(row["agreed_rate"])

item_descriptions = [
    "Office stationery supply", "IT hardware procurement", "Cleaning services",
    "Software license renewal", "Furniture purchase", "Catering services",
    "Printing and packaging materials", "Logistics and courier services"
]

selected_pos = random.sample(pos, 650)

invoices = []
for i, po in enumerate(selected_pos, start=1):
    invoice_id = f"INV{i:04d}"
    po_date = datetime.strptime(po["date"], "%Y-%m-%d")
    invoice_date = po_date + timedelta(days=random.randint(1, 15))
    submitter = random.choice(employees)

    # If this vendor has a contract, respect its agreed rate (small realistic variation)
    if po["vendor_id"] in vendor_contract_rate:
        rate = vendor_contract_rate[po["vendor_id"]]
        amount = round(rate * random.uniform(0.95, 1.1), 2)  # normal invoices stay close to agreed rate
    else:
        amount = po["amount"]  # no contract on file, just use PO amount as before

    invoices.append({
        "invoice_id": invoice_id,
        "po_id": po["po_id"],
        "amount": amount,
        "item_category": po["item_category"],
        "description": random.choice(item_descriptions),
        "date": invoice_date.strftime("%Y-%m-%d"),
        "payment_status": random.choice(PAYMENT_STATUSES),
        "submitted_by_employee_id": submitter["employee_id"]
    })

fieldnames = ["invoice_id", "po_id", "amount", "item_category", "description",
              "date", "payment_status", "submitted_by_employee_id"]

with open("../../data/invoices.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(invoices)

print(f"Created {len(invoices)} invoices -> ../../data/invoices.csv")