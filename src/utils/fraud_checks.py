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
        WHERE v.phone = e.phone OR v.email = e.email
        RETURN v.vendor_id AS vendor_id, v.vendor_name AS vendor_name,
               e.employee_id AS employee_id, e.name AS employee_name
    """
    return list(tx.run(query))

def check_split_pos(tx):
    query = """
        MATCH (v:Vendor)-[:RECEIVED]->(po1:PurchaseOrder)
        MATCH (v:Vendor)-[:RECEIVED]->(po2:PurchaseOrder)
        WHERE po1.po_id < po2.po_id AND po1.date = po2.date
        RETURN v.vendor_id AS vendor_id, v.vendor_name AS vendor_name,
               po1.po_id AS po1_id, po1.amount AS po1_amount,
               po2.po_id AS po2_id, po2.amount AS po2_amount, po1.date AS date
    """
    return list(tx.run(query))

def check_duplicate_invoices(tx):
    query = """
        MATCH (po:PurchaseOrder)-[:HAS_INVOICE]->(inv1:Invoice)
        MATCH (po:PurchaseOrder)-[:HAS_INVOICE]->(inv2:Invoice)
        WHERE inv1.invoice_id < inv2.invoice_id AND inv1.amount = inv2.amount
        RETURN po.po_id AS po_id,
               inv1.invoice_id AS invoice1_id, inv1.description AS desc1,
               inv2.invoice_id AS invoice2_id, inv2.description AS desc2,
               inv1.amount AS amount
    """
    return list(tx.run(query))

def check_same_creator_approver(tx):
    query = """
        MATCH (e:Employee)-[:RAISED]->(po:PurchaseOrder)<-[:APPROVED]-(e)
        RETURN e.employee_id AS employee_id, e.name AS employee_name,
               po.po_id AS po_id, po.amount AS amount
    """
    return list(tx.run(query))

def check_new_vendor_high_value(tx):
    query = """
        MATCH (v:Vendor)-[:RECEIVED]->(po:PurchaseOrder)
        WHERE date(po.date) >= date(v.onboarding_date)
          AND duration.inDays(date(v.onboarding_date), date(po.date)).days <= 7
          AND po.amount > 15000
        RETURN v.vendor_id AS vendor_id, v.vendor_name AS vendor_name,
               v.onboarding_date AS onboarding_date,
               po.po_id AS po_id, po.date AS po_date, po.amount AS amount
    """
    return list(tx.run(query))

def check_contract_rate_mismatch(tx):
    query = """
        MATCH (v:Vendor)-[:HAS_CONTRACT]->(c:Contract)
        MATCH (v:Vendor)-[:RECEIVED]->(po:PurchaseOrder)-[:HAS_INVOICE]->(inv:Invoice)
        WHERE inv.amount > c.agreed_rate * 1.3
        RETURN v.vendor_id AS vendor_id, v.vendor_name AS vendor_name,
               c.agreed_rate AS agreed_rate, inv.invoice_id AS invoice_id, inv.amount AS invoice_amount
    """
    return list(tx.run(query))

def check_email_match(tx):
    query = """
        MATCH (v:Vendor), (e:Employee)
        WHERE v.email = e.email
        RETURN v.vendor_id AS vendor_id, v.vendor_name AS vendor_name,
               e.employee_id AS employee_id, e.name AS employee_name
    """
    return list(tx.run(query))

def check_category_mismatch(tx):
    query = """
        MATCH (po:PurchaseOrder)-[:HAS_INVOICE]->(inv:Invoice)
        WHERE po.item_category <> inv.item_category
        RETURN po.po_id AS po_id, po.item_category AS po_category,
               inv.invoice_id AS invoice_id, inv.item_category AS invoice_category
    """
    return list(tx.run(query))


def print_section(title, results, formatter):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)
    if not results:
        print("No cases found.")
    for r in results:
        print(formatter(r))


def run_all_checks():
    with driver.session() as session:

        print_section("FRAUD CHECK 1: SHELL VENDORS (shared phone/email with employee)",
            session.execute_read(check_shell_vendors),
            lambda r: f"FLAGGED: Vendor {r['vendor_id']} ({r['vendor_name']}) matches Employee {r['employee_id']} ({r['employee_name']})")

        print_section("FRAUD CHECK 2: SPLIT PURCHASE ORDERS (same vendor, same date)",
            session.execute_read(check_split_pos),
            lambda r: f"FLAGGED: {r['po1_id']} (Rs.{r['po1_amount']}) and {r['po2_id']} (Rs.{r['po2_amount']}) -> vendor {r['vendor_id']}, date {r['date']}")

        print_section("FRAUD CHECK 3: DUPLICATE INVOICES (same PO, same amount)",
            session.execute_read(check_duplicate_invoices),
            lambda r: f"FLAGGED: {r['invoice1_id']} and {r['invoice2_id']} -> same PO {r['po_id']}, same amount Rs.{r['amount']}")

        print_section("FRAUD CHECK 4: SAME EMPLOYEE CREATED AND APPROVED PO",
            session.execute_read(check_same_creator_approver),
            lambda r: f"FLAGGED: Employee {r['employee_id']} ({r['employee_name']}) both created and approved PO {r['po_id']} (Rs.{r['amount']})")

        print_section("FRAUD CHECK 5: NEW VENDOR + HIGH-VALUE PO SOON AFTER ONBOARDING",
            session.execute_read(check_new_vendor_high_value),
            lambda r: f"FLAGGED: Vendor {r['vendor_id']} onboarded {r['onboarding_date']}, got PO {r['po_id']} (Rs.{r['amount']}) on {r['po_date']}")

        print_section("FRAUD CHECK 6: INVOICE AMOUNT EXCEEDS CONTRACT RATE",
            session.execute_read(check_contract_rate_mismatch),
            lambda r: f"FLAGGED: Vendor {r['vendor_id']} contract rate Rs.{r['agreed_rate']}, but invoice {r['invoice_id']} billed Rs.{r['invoice_amount']}")

        print_section("FRAUD CHECK 7: VENDOR EMAIL MATCHES EMPLOYEE EMAIL",
            session.execute_read(check_email_match),
            lambda r: f"FLAGGED: Vendor {r['vendor_id']} ({r['vendor_name']}) shares email with Employee {r['employee_id']} ({r['employee_name']})")

        print_section("FRAUD CHECK 8: PO CATEGORY DOESN'T MATCH INVOICE CATEGORY",
            session.execute_read(check_category_mismatch),
            lambda r: f"FLAGGED: PO {r['po_id']} category '{r['po_category']}' != Invoice {r['invoice_id']} category '{r['invoice_category']}'")

    driver.close()

if __name__ == "__main__":
    run_all_checks()