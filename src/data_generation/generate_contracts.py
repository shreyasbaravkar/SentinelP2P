from faker import Faker
import csv
import random
from datetime import datetime, timedelta

fake = Faker()
Faker.seed(42)
random.seed(42)

# Read vendors, only keep the ones that have a contract
vendors = []
with open("../../data/vendors.csv", "r") as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row["has_contract"] == "Yes":
            vendors.append(row)

# Template contract clauses per category (simple, believable text)
CLAUSE_TEMPLATES = {
    "IT Hardware": "The vendor shall supply IT hardware equipment at an agreed rate of ₹{rate} per unit/order, with delivery within 15 business days of order confirmation.",
    "Office Supplies": "The vendor shall provide office supplies at an agreed rate of ₹{rate} per order, payable within the agreed payment terms.",
    "Catering": "The vendor shall provide catering services at an agreed rate of ₹{rate} per event, inclusive of setup and service charges.",
    "Logistics": "The vendor shall provide logistics and courier services at an agreed rate of ₹{rate} per shipment.",
    "Software Licensing": "The vendor shall provide software licenses at an agreed rate of ₹{rate} per license renewal cycle.",
    "Cleaning Services": "The vendor shall provide cleaning services at an agreed rate of ₹{rate} per month.",
    "Printing & Packaging": "The vendor shall provide printing and packaging materials at an agreed rate of ₹{rate} per order."
}

contracts = []
for i, vendor in enumerate(vendors, start=1):
    contract_id = f"CON{i:03d}"
    agreed_rate = round(random.uniform(500, 25000), 2)
    category = vendor["vendor_category"]
    clause_text = CLAUSE_TEMPLATES.get(category, "The vendor shall supply goods/services at an agreed rate of ₹{rate}.").format(rate=agreed_rate)

    start_date = fake.date_between(start_date="-2y", end_date="-6m")
    end_date = start_date + timedelta(days=730)  # 2-year contract

    contracts.append({
        "contract_id": contract_id,
        "vendor_id": vendor["vendor_id"],
        "contract_text": clause_text,
        "agreed_rate": agreed_rate,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d")
    })

with open("../../data/contracts.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["contract_id", "vendor_id", "contract_text", "agreed_rate", "start_date", "end_date"])
    writer.writeheader()
    writer.writerows(contracts)

print(f"Created {len(contracts)} contracts -> ../../data/contracts.csv")