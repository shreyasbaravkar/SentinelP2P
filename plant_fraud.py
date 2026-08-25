import csv
import random
from datetime import datetime, timedelta

random.seed(42)

# FRAUD TYPE 1: SPLIT PO
# Take one legit-looking big purchase and break it into two smaller POs

# Read exisitng POs and vendors
with open("purchase_orders.csv","r") as f:
    reader = csv.DictReader(f)
    pos = list(reader)

with open("vendors.csv","r") as f:
    reader = csv.DictReader(f)
    vendors = list(reader)

with open("employees.csv","r") as f:
    reader = csv.DictReader(f)
    employees = list(reader)

next_po_num = len(pos) + 1

for case in range(2): 
    vendor = random.choice(vendors)
    employee = random.choice(employees)
    same_date = datetime(2026, 6, 1) + timedelta(days=case * 10)
    total_amount = 18000

    for half in range(2):
        po_id = f"PO{next_po_num:04d}"
        pos.append({
            "po_id":po_id,
            "vendor_id": vendor["vendor_id"],
            "amount": str(total_amount/2),
            "created_by_employee_id": employee["employee_id"],
            "date": same_date.strftime("%Y-%m-%d")
        })
        next_po_num +=1

# Save updated POs (clean + split-Po fraud case)
with open("purchase_orders.csv","w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["po_id","vendor_id","amount","date","created_by_employee_id"])
    writer.writeheader()
    writer.writerows(pos)

print("planted 2 split-PO fraud cases -> purchase_orders.csv updated")



# FRAUD TYPE 2: SHELL VENDOR
# Create fake vendors whose phone number secretly matches a real employee
next_vendor_num = len(vendors) + 1
shell_vendor_names = ["Precision Supply Co","Metro Business Solutions"]

for case in range(2):
    employee = random.choice(employees)
    vendor_id = f"VEN{next_vendor_num:03d}"

    vendors.append({
        "vendor_id": vendor_id,
        "vendor_name": shell_vendor_names[case],
        "phone": employee["phone"],
        "address": "Unit 4B, Industrial Estate, Remote City",
        "bank_account": f"GB00FAKE0000000000{case}",
        "created_by_employee_id": employee["employee_id"]
    })
    next_vendor_num += 1 


# Save updated vendors (clean + shell-vendor fraud cases)
with open("vendors.csv","w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["vendor_id","vendor_name","phone","address","bank_account","created_by_employee_id"])
    writer.writeheader()
    writer.writerows(vendors)

print("Planted 2 shell-vendor fraud cases -> vendors.csv updated")



# ============================================================
# FRAUD TYPE 3: DUPLICATE INVOICE
# Take 2 real invoices and create a reworded duplicate of each
# ============================================================

with open("invoices.csv", "r") as f:
    reader = csv.DictReader(f)
    invoices = list(reader)

next_invoice_num = len(invoices) + 1

def reword(description):
    return description + " (resubmitted)"

# Pick 2 random existing invoices to duplicate
originals_to_duplicate = random.sample(invoices, 2)

for original in originals_to_duplicate:
    new_invoice_id = f"INV{next_invoice_num:04d}"
    invoices.append({
        "invoice_id": new_invoice_id,
        "po_id": original["po_id"],
        "amount": original["amount"],
        "description": reword(original["description"]),
        "date": original["date"]
    })
    next_invoice_num += 1

with open("invoices.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["invoice_id", "po_id", "amount", "description", "date"])
    writer.writeheader()
    writer.writerows(invoices)

print("Planted 2 duplicate-invoice fraud cases -> invoices.csv updated")