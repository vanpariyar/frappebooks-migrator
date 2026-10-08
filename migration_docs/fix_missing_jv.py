import frappe

def execute():
    frappe.init(site="books.localhost")
    frappe.connect()
    
    company = "Sahajanand Digital"
    abbr = frappe.db.get_value("Company", company, "abbr") or "SD"
    
    def get_acct(base_name, fallback):
        if not base_name: return fallback
        acct = f"{base_name} - {abbr}"
        if frappe.db.exists("Account", acct):
            return acct
        return fallback
    
    jv_name = "JV-1073"
    
    b_jv = frappe.get_doc("Books Journal Entry", jv_name)
    
    doc = frappe.get_doc("Journal Entry", jv_name)
    doc.cancel()
    doc.delete()
    
    doc = frappe.new_doc("Journal Entry")
    doc.name = b_jv.name
    doc.company = company
    doc.posting_date = b_jv.posting_date or "2024-01-01"
    doc.voucher_type = "Journal Entry" # standard
    doc.cheque_no = b_jv.reference_number
    doc.cheque_date = b_jv.reference_date
    doc.user_remark = b_jv.user_remark
    
    for item in b_jv.accounts:
        doc.append("accounts", {
            "account": get_acct(item.account, None),
            "debit_in_account_currency": item.debit or 0,
            "credit_in_account_currency": item.credit or 0,
            "debit": item.debit or 0,
            "credit": item.credit or 0,
        })
        
    doc.flags.ignore_mandatory = True
    doc.flags.ignore_validate = True
    try:
        doc.insert(set_name=b_jv.name)
        if b_jv.docstatus == 1:
            doc.submit()
        print(f"Successfully migrated {b_jv.name} to ERPNext")
    except Exception as e:
        print(f"Failed to insert {b_jv.name}: {e}")
        
    frappe.db.commit()

execute()
