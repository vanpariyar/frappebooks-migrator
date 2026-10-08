import frappe

def execute():
    frappe.init(site="books.localhost")
    frappe.connect()
    frappe.flags.ignore_permissions = True
    
    addresses = frappe.get_all("Books Address", fields=["name", "address_line1", "address_line2", "city", "state", "country", "postal_code", "email_address", "phone", "fax"])
    
    migrated_count = 0
    for ba in addresses:
        # Check if address exists
        address_name = ba.name + "-Billing"
        if not frappe.db.exists("Address", address_name):
            
            # Find the linked party
            # In Frappe Books, party name usually matches the address name or is linked via address field
            parties = frappe.get_all("Books Party", filters={"address": ba.name}, fields=["name", "role"])
            if not parties:
                # If no direct link, fallback to assuming party name = address name
                parties = frappe.get_all("Books Party", filters={"name": ba.name}, fields=["name", "role"])
                
            if not parties:
                print(f"Warning: Could not find any party for address '{ba.name}'. Skipping.")
                continue
                
            party = parties[0]
            link_doctype = "Supplier" if party.role == "Supplier" else "Customer"
            link_name = party.name
            
            doc = frappe.new_doc("Address")
            doc.address_title = ba.name
            doc.address_type = "Billing"
            doc.address_line1 = ba.address_line1 or "Not Provided"
            doc.address_line2 = ba.address_line2
            doc.city = ba.city or "Not Provided"
            doc.state = ba.state
            doc.country = ba.country or "India" # Defaulting for ERPNext mandatory field
            import re
            
            clean_phone = ba.phone
            if clean_phone:
                clean_phone = re.sub(r'[^\d+]', '', clean_phone)

            doc.pincode = ba.postal_code
            doc.email_id = ba.email_address
            doc.phone = clean_phone
            doc.fax = ba.fax
            
            doc.append("links", {
                "link_doctype": link_doctype,
                "link_name": link_name
            })
            
            doc.flags.ignore_mandatory = True
            doc.flags.ignore_validate = True
            
            try:
                doc.insert(set_name=address_name)
                migrated_count += 1
                print(f"Migrated Address: {address_name} for {link_doctype} {link_name}")
            except Exception as e:
                print(f"Failed to migrate Address '{ba.name}': {e}")
        else:
            print(f"Address {address_name} already exists.")
            
    frappe.db.commit()
    print(f"Total Addresses Migrated: {migrated_count}")

execute()
