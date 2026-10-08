import frappe

def execute():
    frappe.init(site="books.localhost")
    frappe.connect()

    print("=== Document Count Comparison ===")
    queries = [
        ("Sales Invoices", "Books Sales Invoice", "Sales Invoice"),
        ("Payments", "Books Payment", "Payment Entry"),
        ("Journal Entries", "Books Journal Entry", "Journal Entry")
    ]
    
    for label, books_dt, erp_dt in queries:
        books_count = frappe.db.count(books_dt, {"docstatus": 1})
        erp_count = frappe.db.count(erp_dt, {"docstatus": 1})
        status = "✅ Match" if books_count == erp_count else "❌ Mismatch"
        print(f"{label}: Books = {books_count} | ERPNext = {erp_count} | {status}")

    print("\n=== Financial Totals Comparison ===")
    
    # Sales Invoices Total
    books_si_total = frappe.db.sql("SELECT sum(grand_total) FROM `tabBooks Sales Invoice` WHERE docstatus = 1")[0][0] or 0
    erp_si_total = frappe.db.sql("SELECT sum(grand_total) FROM `tabSales Invoice` WHERE docstatus = 1")[0][0] or 0
    si_status = "✅ Match" if books_si_total == erp_si_total else "❌ Mismatch"
    print(f"Sales Invoices Total: Books = {books_si_total} | ERPNext = {erp_si_total} | {si_status}")

    # Payments Total
    books_pay_total = frappe.db.sql("SELECT sum(amount) FROM `tabBooks Payment` WHERE docstatus = 1")[0][0] or 0
    erp_pay_total = frappe.db.sql("SELECT sum(paid_amount) FROM `tabPayment Entry` WHERE docstatus = 1")[0][0] or 0
    pay_status = "✅ Match" if books_pay_total == erp_pay_total else "❌ Mismatch"
    print(f"Payments Total: Books = {books_pay_total} | ERPNext = {erp_pay_total} | {pay_status}")

    # Journal Entries Total
    books_jv_total = frappe.db.sql("SELECT sum(a.debit) FROM `tabBooks Journal Entry Account` a JOIN `tabBooks Journal Entry` p ON a.parent = p.name WHERE p.docstatus = 1")[0][0] or 0
    erp_jv_total = frappe.db.sql("SELECT sum(a.debit) FROM `tabJournal Entry Account` a JOIN `tabJournal Entry` p ON a.parent = p.name WHERE p.docstatus = 1")[0][0] or 0
    jv_status = "✅ Match" if books_jv_total == erp_jv_total else "❌ Mismatch"
    print(f"Journal Entries (Debit Total): Books = {books_jv_total} | ERPNext = {erp_jv_total} | {jv_status}")

    print("\n=== Checking for Missing Journal Entries ===")
    missing_jvs = frappe.db.sql("""
        SELECT name FROM `tabBooks Journal Entry` 
        WHERE docstatus = 1 AND name NOT IN (SELECT name FROM `tabJournal Entry`)
    """, as_dict=True)
    
    if missing_jvs:
        print(f"❌ Found {len(missing_jvs)} submitted Journal Entries in Books that are missing in ERPNext:")
        for jv in missing_jvs:
            print(f"  - {jv.name}")
    else:
        print("✅ No missing submitted Journal Entries.")

execute()
