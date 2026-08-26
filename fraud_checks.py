import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def check_shell_vendors(tx):
    query = """
        MATCH (e:Employee)-[:CREATED]->(v:Vendor)
        WHERE v.phone = e.phone
        RETURN v.vendor_id AS vendor_id, v.vendor_name AS vendor_name,
               e.employee_id AS employee_id, e.name AS employee_name
    """
    return list(tx.run(query))

def check_split_pos(tx):
    query = """
        MATCH (v:Vendor)-[:RECEIVED]->(po1:PurchaseOrder)
        MATCH (v:Vendor)-[:RECEIVED]->(po2:PurchaseOrder)
        WHERE po1.po_id < po2.po_id
          AND po1.date = po2.date
        RETURN v.vendor_id AS vendor_id, v.vendor_name AS vendor_name,
               po1.po_id AS po1_id, po1.amount AS po1_amount,
               po2.po_id AS po2_id, po2.amount AS po2_amount,
               po1.date AS date
    """
    return list(tx.run(query))

def check_duplicate_invoices(tx):
    query = """
        MATCH (po:PurchaseOrder)-[:HAS_INVOICE]->(inv1:Invoice)
        MATCH (po:PurchaseOrder)-[:HAS_INVOICE]->(inv2:Invoice)
        WHERE inv1.invoice_id < inv2.invoice_id
          AND inv1.amount = inv2.amount
        RETURN po.po_id AS po_id,
               inv1.invoice_id AS invoice1_id, inv1.description AS desc1,
               inv2.invoice_id AS invoice2_id, inv2.description AS desc2,
               inv1.amount AS amount
    """
    return list(tx.run(query))

def run_all_checks():
    with driver.session() as session:

        print("=" * 60)
        print("FRAUD CHECK 1: SHELL VENDORS (shared phone with employee)")
        print("=" * 60)
        results = session.execute_read(check_shell_vendors)
        if not results:
            print("No shell vendors found.")
        for r in results:
            print(f"FLAGGED: Vendor {r['vendor_id']} ({r['vendor_name']}) "
                  f"shares a phone number with Employee {r['employee_id']} ({r['employee_name']})")

        print()
        print("=" * 60)
        print("FRAUD CHECK 2: SPLIT PURCHASE ORDERS (same vendor, same date)")
        print("=" * 60)
        results = session.execute_read(check_split_pos)
        if not results:
            print("No split POs found.")
        for r in results:
            print(f"FLAGGED: {r['po1_id']} (₹{r['po1_amount']}) and {r['po2_id']} (₹{r['po2_amount']}) "
                  f"-> same vendor {r['vendor_id']} ({r['vendor_name']}), same date {r['date']}")

        print()
        print("=" * 60)
        print("FRAUD CHECK 3: DUPLICATE INVOICES (same PO, same amount)")
        print("=" * 60)
        results = session.execute_read(check_duplicate_invoices)
        if not results:
            print("No duplicate invoices found.")
        for r in results:
            print(f"FLAGGED: {r['invoice1_id']} (\"{r['desc1']}\") and {r['invoice2_id']} (\"{r['desc2']}\") "
                  f"-> same PO {r['po_id']}, same amount ₹{r['amount']}")

    driver.close()

if __name__ == "__main__":
    run_all_checks()
    