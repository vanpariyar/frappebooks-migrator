#!/usr/bin/env python3
import os
import sys
import frappe

def fix_document_statuses():
    print("Fixing Document Statuses...")
    for dt in ["Books Sales Invoice", "Books Purchase Invoice", "Books Payment", "Books Journal Entry"]:
        docs = frappe.get_all(dt, pluck="name")
        count = 0
        for name in docs:
            doc = frappe.get_doc(dt, name)
            if hasattr(doc, "set_status"):
                doc.set_status(update=True)
                doc.db_update()
                count += 1
        print(f"  - Updated {count} {dt} statuses.")
    frappe.db.commit()

def inject_template_fixes():
    print("Injecting Tailwind & Scaling fixes into Custom Print Formats...")
    formats = frappe.get_all("Print Format", filters={"custom_format": 1}, pluck="name")
    
    scale_css = """
<style>
  @media print {
    html, body {
      font-size: 12px !important;
    }
    .page-break-avoid, section, footer, .flex {
      page-break-inside: avoid !important;
      break-inside: avoid !important;
    }
  }
</style>
"""
    tailwind_link = '<link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">\n'

    for name in formats:
        try:
            doc = frappe.get_doc("Print Format", name)
            html = doc.html
            
            # Remove breaking classes
            html = html.replace('h-full', '').replace('h-screen', '')
            
            # Inject Tailwind if missing
            if "tailwindcss" not in html:
                html = tailwind_link + html
                
            # Inject Scaling CSS if missing
            if "font-size: 12px !important;" not in html:
                if "rel=\"stylesheet\">" in html:
                    parts = html.split("rel=\"stylesheet\">")
                    html = parts[0] + "rel=\"stylesheet\">\n" + scale_css + parts[1]
                else:
                    html = scale_css + html
            
            # Fix amount in words
            html = html.replace("totals.amount_in_words", 'totals.amount_paid_in_words if doc.doctype == "Books Payment" else totals.grand_total_in_words')
            
            doc.html = html
            doc.save(ignore_permissions=True)
            print(f"  - Fixed scaling & CSS for: {name}")
        except Exception as e:
            print(f"  - Skipped {name}: {e}")
            frappe.db.rollback()
    
    frappe.db.commit()

def execute():
    frappe.init(site="books.localhost", sites_path="sites")
    frappe.connect()
    
    print("--- Starting Post-Migration Toolkit ---")
    fix_document_statuses()
    inject_template_fixes()
    print("--- Migration Toolkit Complete ---")

if __name__ == "__main__":
    # Ensure this script is run within a Frappe Bench environment
    if not os.path.exists("apps/frappe"):
        print("Error: Please run this script from the root of your frappe bench directory (e.g., books-bench).")
        print("Usage: bench execute path/to/migrator.py")
        sys.exit(1)
        
    sys.path.insert(0, os.path.abspath("apps/frappe"))
    execute()
