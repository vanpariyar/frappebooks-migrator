import frappe
import sqlite3
import re

def camel_to_snake(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

MAPPING = {
    "for": "item_usage",
    "parentSchemaName": "parenttype",
    "parentFieldname": "parentfield",
    "date": "posting_date" # Only used by Journal Entry, others use date
}

def execute():
    # Make sure we're in the correct context
    frappe.init(site="books.localhost", sites_path="sites")
    frappe.connect()

    # Provide the path to the sqlite file
    conn = sqlite3.connect("../Sahajanand Digital.books 2.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]

    # Ordered mapping to avoid reference issues
    table_order = [
        "Color", "Currency", "UOM", "NumberSeries", "Account", "Address", "ItemGroup",
        "Party", "Item", "Tax", "PriceList", "Location", "CustomField", "CustomForm",
        "PaymentMethod", "LoyaltyProgram", "CouponCode", "SalesQuote", "SalesOrder",
        "SalesInvoice", "PurchaseReceipt", "PurchaseInvoice", "JournalEntry", "Payment"
    ]
    
    for t in tables:
        if t not in table_order and not t.endswith("Item") and not t.endswith("Detail"):
            table_order.append(t)
            
    for t in tables:
        # Convert PascalCase to Space Separated Title Case
        spaced_t = re.sub(r"([A-Z])", r" \1", t).strip()
        # Handle exceptions
        spaced_t = spaced_t.replace("U O M", "Uom")
        spaced_t = spaced_t.replace("P O S", "Pos")
        spaced_t = spaced_t.replace("E R P Next", "ERPNext")
        doctype = f"Books {spaced_t}"
        
        if doctype == "Books Pos Closing Shift": pass
        elif doctype == "Books Pos Opening Shift": pass
        elif doctype == "Books Pos Profile": pass
        elif doctype == "Books Accounting Ledger Entry": doctype = "Books Ledger Entry"
        
        if not frappe.db.exists("DocType", doctype):
            continue
            
        print(f"Migrating {t} to {doctype}...")
        valid_columns = frappe.get_meta(doctype).get_valid_columns()
        
        cursor.execute(f"SELECT * FROM `{t}`")
        rows = cursor.fetchall()
        for row in rows:
            d = dict(row)
            doc_dict = {}
            for k, v in d.items():
                if k == "name": doc_dict["name"] = v
                elif k == "created": doc_dict["creation"] = v
                elif k == "modified": doc_dict["modified"] = v
                elif k == "createdBy": doc_dict["owner"] = v
                elif k == "modifiedBy": doc_dict["modified_by"] = v
                else:
                    snake_key = camel_to_snake(k)
                    if k in MAPPING:
                        snake_key = MAPPING[k]
                    
                    if doctype == "Books Ledger Entry":
                        if k == "referenceType": snake_key = "voucher_type"
                        elif k == "referenceName": snake_key = "voucher_no"
                        elif k == "date": snake_key = "posting_date"
                    
                    if snake_key in valid_columns:
                        doc_dict[snake_key] = v
                    elif k == "date" and "date" in valid_columns:
                        doc_dict["date"] = v
                        
                    if k == "quantity" and "qty" in valid_columns:
                        doc_dict["qty"] = v
                        
            if not doc_dict.get("name"):
                continue

            try:
                # add missing standard fields
                doc_dict["creation"] = doc_dict.get("creation") or frappe.utils.now()
                doc_dict["modified"] = doc_dict.get("modified") or frappe.utils.now()
                doc_dict["owner"] = doc_dict.get("owner") or "Administrator"
                doc_dict["modified_by"] = doc_dict.get("modified_by") or "Administrator"
                doc_dict["docstatus"] = doc_dict.get("docstatus", 0)
                
                # Handling NULLs
                if "loyalty_points" in valid_columns and (doc_dict.get("loyalty_points") is None or doc_dict.get("loyalty_points") == ""):
                    doc_dict["loyalty_points"] = 0
                if "discount_percent" in valid_columns and (doc_dict.get("discount_percent") is None or doc_dict.get("discount_percent") == ""):
                    doc_dict["discount_percent"] = 0.0
                
                # Also map parenttype if this is a child table
                if "parenttype" in doc_dict and doc_dict["parenttype"]:
                    ptype = doc_dict["parenttype"]
                    spaced_pt = re.sub(r"([A-Z])", r" \1", ptype).strip()
                    if not spaced_pt.startswith("Books "):
                        spaced_pt = "Books " + spaced_pt
                    doc_dict["parenttype"] = spaced_pt
                        
                # map docstatus
                if "submitted" in d and d["submitted"]: doc_dict["docstatus"] = 1
                if "cancelled" in d and d["cancelled"]: doc_dict["docstatus"] = 2
                        
                fields = list(doc_dict.keys())
                
                # Fix datetime strings for MariaDB compatibility
                fixed_values = []
                for k in fields:
                    v = doc_dict[k]
                    if isinstance(v, str) and len(v) > 18 and v[10] == 'T' and v.endswith('Z'):
                        v = v.replace('T', ' ').replace('Z', '')
                    fixed_values.append(v)
                    
                if frappe.db.exists(doctype, doc_dict["name"]):
                    # UPDATE
                    update_str = ", ".join([f"`{c}` = %s" for c in fields if c != "name"])
                    update_values = tuple(fixed_values[i] for i, c in enumerate(fields) if c != "name")
                    frappe.db.sql(f"UPDATE `tab{doctype}` SET {update_str} WHERE name = %s", update_values + (doc_dict["name"],))
                else:
                    # INSERT
                    values = tuple(fixed_values)
                    placeholders = ", ".join(["%s"] * len(fields))
                    columns = ", ".join([f"`{c}`" for c in fields])
                    frappe.db.sql(f"INSERT INTO `tab{doctype}` ({columns}) VALUES ({placeholders})", values)
            except Exception as e:
                with open("migration_errors.txt", "a") as f:
                    f.write(f"Error {doctype} {doc_dict.get('name')}: {e}\n")
                    
    frappe.db.commit()
    with open("migration_errors.txt", "a") as f:
        f.write("Migration complete!\n")

if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.abspath("apps/frappe"))
    execute()
