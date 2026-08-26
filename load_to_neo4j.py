import csv
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Step 1: Load credentials from .env
load_dotenv()
URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")

# Step 2: Connect to Neo4j
driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def run_query(tx, query, **params):
    tx.run(query, **params)

def load_data():
    with driver.session() as session:

        # Clear existing data first (so re-running this script doesn't duplicate)
        session.execute_write(run_query, "MATCH (n) DETACH DELETE n")
        print("Cleared existing graph data")

        # ---------- Employees ----------
        with open("employees.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                session.execute_write(run_query, """
                    CREATE (e:Employee {
                        employee_id: $employee_id,
                        name: $name,
                        phone: $phone,
                        department: $department
                    })
                """, **row)
        print("Loaded Employees")

        # ---------- Vendors + CREATED_BY relationship ----------
        with open("vendors.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                session.execute_write(run_query, """
                    CREATE (v:Vendor {
                        vendor_id: $vendor_id,
                        vendor_name: $vendor_name,
                        phone: $phone,
                        address: $address,
                        bank_account: $bank_account
                    })
                    WITH v
                    MATCH (e:Employee {employee_id: $created_by_employee_id})
                    CREATE (e)-[:CREATED]->(v)
                """, **row)
        print("Loaded Vendors and linked to creators")

        # ---------- Purchase Orders + relationships ----------
        with open("purchase_orders.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                session.execute_write(run_query, """
                    CREATE (po:PurchaseOrder {
                        po_id: $po_id,
                        amount: toFloat($amount),
                        date: $date
                    })
                    WITH po
                    MATCH (e:Employee {employee_id: $created_by_employee_id})
                    CREATE (e)-[:RAISED]->(po)
                    WITH po
                    MATCH (v:Vendor {vendor_id: $vendor_id})
                    CREATE (v)-[:RECEIVED]->(po)
                """, **row)
        print("Loaded Purchase Orders and linked to employees/vendors")

        # ---------- Invoices + relationship ----------
        with open("invoices.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                session.execute_write(run_query, """
                    CREATE (inv:Invoice {
                        invoice_id: $invoice_id,
                        amount: toFloat($amount),
                        description: $description,
                        date: $date
                    })
                    WITH inv
                    MATCH (po:PurchaseOrder {po_id: $po_id})
                    CREATE (po)-[:HAS_INVOICE]->(inv)
                """, **row)
        print("Loaded Invoices and linked to purchase orders")

    driver.close()
    print("All data loaded into Neo4j successfully!")

if __name__ == "__main__":
    load_data()