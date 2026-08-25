from faker import Faker
import csv
import random
from datetime import datetime, timedelta

fake = Faker()
Faker.seed(42)
random.seed(42)

# Step 1: Read PO detail ( we need po_id, amount, and date to build a matching invoice )
pos =[]
with open("purchase_orders.csv","r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        pos.append(row)

# Step 2: Some generic item description to pick from 
item_descriptions = [
    "Office stationery supply",
    "IT hardware procurrement",
    "Cleaning services",
    "Software license renewal",
    "Catering services",
    "Printing and packaging materials",
    "Logistics and courier services"
]

# Step 3: Create one invoice for each PO
invoices = []
for i, po in enumerate(pos, start=1):
    invoice_id = f"INV{i:04d}"
    po_date = datetime.strptime(po["date"], "%Y-%m-%d")
    invoice_date = po_date + timedelta(days=random.randint(1, 15))

    invoices.append({
        "invoice_id": invoice_id,
        "po_id":po["amount"],
        "description": random.choice(item_descriptions),
        "date": invoice_date.strftime("%Y-%m-%d")
   })

# Step 4: Save to CSV
with open("invoices.csv","w",newline="") as f:
    writer  = csv.DictWriter(f, fieldnames=["invoice_id","po_id","amount","description","date"])
    writer.writeheader()
    writer.writerows(invoices)

print(f"Created {len(invoices)} invoices -> invoices.csv")
