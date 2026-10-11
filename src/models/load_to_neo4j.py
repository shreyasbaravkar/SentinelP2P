import csv
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USER")
PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def read_csv(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def run_batch(tx, query, rows):
    tx.run(query, rows=rows)

def load_data():
    employees = read_csv("../../data/employees.csv")
    vendors = read_csv("../../data/vendors.csv")
    pos = read_csv("../../data/purchase_orders.csv")
    invoices = read_csv("../../data/invoices.csv")
    contracts = read_csv("../../data/contracts.csv")

    with driver.session() as session:

        session.execute_write(run_batch, "MATCH (n) DETACH DELETE n", [])
        print("Cleared existing graph data")

        # ---------- Employees ----------
        session.execute_write(run_batch, """
            UNWIND $rows AS row
            CREATE (e:Employee {
                employee_id: row.employee_id,
                name: row.name,
                email: row.email,
                phone: row.phone,
                department: row.department,
                role: row.role,
                join_date: row.join_date
            })
        """, employees)
        print(f"Loaded {len(employees)} Employees")

        # ---------- Vendors + CREATED relationship ----------
        session.execute_write(run_batch, """
            UNWIND $rows AS row
            CREATE (v:Vendor {
                vendor_id: row.vendor_id,
                vendor_name: row.vendor_name,
                email: row.email,
                phone: row.phone,
                address: row.address,
                bank_account: row.bank_account,
                registration_number: row.registration_number,
                vendor_category: row.vendor_category,
                onboarding_date: row.onboarding_date,
                has_contract: row.has_contract
            })
            WITH v, row
            MATCH (e:Employee {employee_id: row.created_by_employee_id})
            CREATE (e)-[:CREATED]->(v)
        """, vendors)
        print(f"Loaded {len(vendors)} Vendors and linked to creators")

        # ---------- Purchase Orders + relationships ----------
        session.execute_write(run_batch, """
            UNWIND $rows AS row
            CREATE (po:PurchaseOrder {
                po_id: row.po_id,
                amount: toFloat(row.amount),
                item_category: row.item_category,
                date: row.date,
                payment_terms: row.payment_terms
            })
            WITH po, row
            MATCH (creator:Employee {employee_id: row.created_by_employee_id})
            CREATE (creator)-[:RAISED]->(po)
            WITH po, row
            MATCH (approver:Employee {employee_id: row.approved_by_employee_id})
            CREATE (approver)-[:APPROVED]->(po)
            WITH po, row
            MATCH (v:Vendor {vendor_id: row.vendor_id})
            CREATE (v)-[:RECEIVED]->(po)
        """, pos)
        print(f"Loaded {len(pos)} Purchase Orders and linked to employees/vendors")

        # ---------- Invoices + relationship ----------
        session.execute_write(run_batch, """
            UNWIND $rows AS row
            CREATE (inv:Invoice {
                invoice_id: row.invoice_id,
                amount: toFloat(row.amount),
                item_category: row.item_category,
                description: row.description,
                date: row.date,
                payment_status: row.payment_status
            })
            WITH inv, row
            MATCH (po:PurchaseOrder {po_id: row.po_id})
            CREATE (po)-[:HAS_INVOICE]->(inv)
            WITH inv, row
            MATCH (submitter:Employee {employee_id: row.submitted_by_employee_id})
            CREATE (submitter)-[:SUBMITTED]->(inv)
        """, invoices)
        print(f"Loaded {len(invoices)} Invoices and linked to purchase orders/employees")

        # ---------- Contracts + relationship ----------
        session.execute_write(run_batch, """
            UNWIND $rows AS row
            CREATE (c:Contract {
                contract_id: row.contract_id,
                contract_text: row.contract_text,
                agreed_rate: toFloat(row.agreed_rate),
                start_date: row.start_date,
                end_date: row.end_date
            })
            WITH c, row
            MATCH (v:Vendor {vendor_id: row.vendor_id})
            CREATE (v)-[:HAS_CONTRACT]->(c)
        """, contracts)
        print(f"Loaded {len(contracts)} Contracts and linked to vendors")

    driver.close()
    print("All data loaded into Neo4j successfully!")

if __name__ == "__main__":
    load_data()