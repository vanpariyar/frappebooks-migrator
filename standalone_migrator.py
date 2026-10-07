import sqlite3
import json
import re
import os
import sys
import random
import string

def get_mapping(table):
    if table == "PrintTemplate":
        return "Print Format"
    
    # Tables to completely skip
    skip_tables = [
        "DocType", "PatchRun", "SingleValue", "ERPNextSyncQueue", 
        "FetchFromERPNextQueue", "IntegrationErrorLog",
    ]
    if table in skip_tables:
        return None
        
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', table)
    spaced = re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1)
    
    spaced = spaced.replace("POS", "Pos")
    spaced = spaced.replace("UOM", "Uom")
    
    # Custom overrides
    overrides = {
        "Accounting Ledger Entry": "Books Ledger Entry",
        "Stock Ledger Entry": "Books Stock Ledger Entry",
    }
    if spaced in overrides:
        return overrides[spaced]
        
    return "Books " + spaced

FIELD_RENAMES = {
    "Books Account": {
        "rootType":      "root_type",
        "parentAccount": "parent_books_account",
        "accountType":   "account_type",
        "isGroup":       "is_group",
    },
    "Books Party": {
        "defaultAccount":    "default_account",
        "gstType":           "gst_type",
        "fromLead":          "from_lead",
        "loyaltyProgram":    "loyalty_program",
        "loyaltyPoints":     "loyalty_points",
        "outstandingAmount": "outstanding_amount",
    },
    "Books Item": {
        "itemCode":        "item_code",
        "itemGroup":       "item_group",
        "itemType":        "item_type",
        "incomeAccount":   "income_account",
        "expenseAccount":  "expense_account",
        "hsnCode":         "hsn_code",
        "trackItem":       "track_item",
        "hasBatch":        "has_batch",
        "hasSerialNumber": "has_serial_number",
    },
    "Books Payment": {
        "paymentType":     "payment_type",
        "paymentAccount":  "payment_account",
        "paymentMethod":   "payment_method",
        "partyType":       "party_type",
        "referenceType":   "reference_type",
        "referenceName":   "reference_name",
        "clearanceDate":   "clearance_date",
        "referenceDate":   "reference_date",
    },
    "Books Sales Invoice": {
        "isPOS":           "is_pos",
        "entryCurrency":   "entry_currency",
        "exchangeRate":    "exchange_rate",
        "discountPercent": "discount_percent",
        "discountAmount":  "discount_amount",
        "netTotal":        "net_total",
        "totalTaxes":      "total_taxes",
        "grandTotal":      "grand_total",
        "amountPaid":      "amount_paid",
        "outstandingAmount":"outstanding_amount",
        "isReturned":      "is_returned",
        "returnAgainst":   "return_against",
    },
    "Books Purchase Invoice": {
        "entryCurrency":   "entry_currency",
        "exchangeRate":    "exchange_rate",
        "discountPercent": "discount_percent",
        "discountAmount":  "discount_amount",
        "netTotal":        "net_total",
        "totalTaxes":      "total_taxes",
        "grandTotal":      "grand_total",
        "amountPaid":      "amount_paid",
        "outstandingAmount":"outstanding_amount",
        "isReturned":      "is_returned",
        "returnAgainst":   "return_against",
    },
    "Books Journal Entry": {
        "numberSeries":    "number_series",
        "entryType":       "entry_type",
        "referenceNumber": "reference_number",
        "referenceDate":   "reference_date",
        "userRemark":      "user_remark",
    },
    "Books Number Series": {
        "referenceType": "reference_type",
        "startAt":       "start_at",
        "padZeros":      "pad_zeros",
    },
    "Books Ledger Entry": {
        "date": "posting_date",
        "referenceType": "voucher_type",
        "referenceName": "voucher_no",
    },
    "Books Stock Ledger Entry": {
        "date": "posting_date",
        "referenceType": "voucher_type",
        "referenceName": "voucher_no",
        "stockValueDiff": "stock_value_difference",
    },
}

def rename_fields(doctype, doc_dict):
    """Rename camelCase SQLite fields to snake_case MariaDB fields."""
    new_dict = {}
    
    global_overrides = {
        "parentAccount": "parent_books_account",
        "parentFieldname": "parentfield",
        "parentSchemaName": "parenttype",
        "createdBy": "owner",
        "modifiedBy": "modified_by",
        "created": "creation",
        "modified": "modified",
        "isPOS": "is_pos",
        "docType": "doc_type",
    }
    
    renames = FIELD_RENAMES.get(doctype, {})
    
    for k, v in doc_dict.items():
        if k in renames:
            new_k = renames[k]
        elif k in global_overrides:
            new_k = global_overrides[k]
        else:
            new_k = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', k).lower()
        
        # Rewrite the value to match the new Doctype name for internal reference fields
        if new_k in ("parenttype", "doc_type", "voucher_type", "party_type") and v:
            mapped_type = get_mapping(v)
            if mapped_type:
                v = mapped_type

        new_dict[new_k] = v
        
    return new_dict

def sql_quote(val):
    if val is None: return "NULL"
    if isinstance(val, (int, float)): return str(val)
    if isinstance(val, bool): return "1" if val else "0"
    if isinstance(val, (dict, list)): val = json.dumps(val)
    val = str(val).replace("\\", "\\\\").replace("'", "''")
    return f"'{val}'"

def generate_settings_sql(conn):
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT parent, fieldname, value FROM SingleValue")
    except sqlite3.OperationalError:
        return []
        
    rows = cursor.fetchall()
    
    SETTINGS_MAP = {
        ("PrintSettings", "companyName"):   ("Books Print Settings", "company_name"),
        ("PrintSettings", "phone"):         ("Books Print Settings", "phone"),
        ("PrintSettings", "email"):         ("Books Print Settings", "email"),
        ("PrintSettings", "address"):       ("Books Print Settings", "address"),
        ("PrintSettings", "gstin"):         ("Books Print Settings", "gstin"),
        ("PrintSettings", "logo"):          ("Books Print Settings", "logo"),
        ("PrintSettings", "displayLogo"):   ("Books Print Settings", "display_logo"),
        ("PrintSettings", "color"):         ("Books Print Settings", "color"),
        ("PrintSettings", "font"):          ("Books Print Settings", "font"),
        ("PrintSettings", "amountInWords"): ("Books Print Settings", "amount_in_words"),
        ("PrintSettings", "displayTime"):   ("Books Print Settings", "display_time"),
        ("PrintSettings", "termsAndConditions"): ("Books Print Settings", "terms_and_conditions"),

        ("AccountingSettings", "companyName"):      ("Books Accounting Settings", "company_name"),
        ("AccountingSettings", "fullname"):         ("Books Accounting Settings", "fullname"),
        ("AccountingSettings", "email"):            ("Books Accounting Settings", "email"),
        ("AccountingSettings", "gstin"):            ("Books Accounting Settings", "gstin"),
        ("AccountingSettings", "country"):          ("Books Accounting Settings", "country"),
        ("AccountingSettings", "bankName"):         ("Books Accounting Settings", "bank_name"),
        ("AccountingSettings", "fiscalYearStart"):  ("Books Accounting Settings", "fiscal_year_start"),
        ("AccountingSettings", "fiscalYearEnd"):    ("Books Accounting Settings", "fiscal_year_end"),
        ("AccountingSettings", "currency"):         ("Books Accounting Settings", "currency"),
        ("AccountingSettings", "writeOffAccount"):  ("Books Accounting Settings", "write_off_account"),
        ("AccountingSettings", "roundOffAccount"):  ("Books Accounting Settings", "round_off_account"),
        ("AccountingSettings", "discountAccount"):  ("Books Accounting Settings", "discount_account"),
        ("AccountingSettings", "enableLead"):                      ("Books Accounting Settings", "enable_lead"),
        ("AccountingSettings", "enablePricingRule"):               ("Books Accounting Settings", "enable_pricing_rule"),
        ("AccountingSettings", "enableLoyaltyProgram"):            ("Books Accounting Settings", "enable_loyalty_program"),
        ("AccountingSettings", "enableCouponCode"):                ("Books Accounting Settings", "enable_coupon_code"),
        ("AccountingSettings", "enablePartialPayment"):            ("Books Accounting Settings", "enable_partial_payment"),
        ("AccountingSettings", "enableitemGroup"):                 ("Books Accounting Settings", "enableitem_group"),
        ("AccountingSettings", "enableItemEnquiry"):               ("Books Accounting Settings", "enable_item_enquiry"),
        ("AccountingSettings", "enablePointOfSaleWithOutInventory"):("Books Accounting Settings", "enable_point_of_sale_with_out_inventory"),

        ("Defaults", "salesInvoicePrintTemplate"):  ("Books Defaults", "sales_invoice_print_template"),
        ("Defaults", "purchaseInvoicePrintTemplate"):("Books Defaults", "purchase_invoice_print_template"),
        ("Defaults", "paymentPrintTemplate"):       ("Books Defaults", "payment_print_template"),
        ("Defaults", "salesQuotePrintTemplate"):    ("Books Defaults", "sales_quote_print_template"),
        ("Defaults", "posPrintTemplate"):           ("Books Defaults", "pos_print_template"),
        ("Defaults", "shipmentPrintTemplate"):      ("Books Defaults", "shipment_print_template"),
        ("Defaults", "salesPaymentAccount"):        ("Books Defaults", "sales_payment_account"),
        ("Defaults", "purchasePaymentAccount"):     ("Books Defaults", "purchase_payment_account"),
        ("Defaults", "saveButtonColour"):           ("Books Defaults", "save_button_colour"),
        ("Defaults", "cancelButtonColour"):         ("Books Defaults", "cancel_button_colour"),
        ("Defaults", "submitButtonColour"):         ("Books Defaults", "save_button_colour"),
        ("Defaults", "heldButtonColour"):           ("Books Defaults", "held_button_colour"),
        ("Defaults", "returnButtonColour"):         ("Books Defaults", "return_button_colour"),
        ("Defaults", "payButtonColour"):            ("Books Defaults", "pay_button_colour"),
    }

    updates = {}
    for parent, fieldname, value in rows:
        key = (parent, fieldname)
        if key in SETTINGS_MAP:
            target_dt, target_field = SETTINGS_MAP[key]
            updates[(target_dt, target_field)] = value

    sql_statements = []
    for (doctype, fieldname), value in updates.items():
        if isinstance(value, str) and value in ("1.0", "0.0"):
            value = int(float(value))
        
        # In Frappe, Single doctypes are updated in the tabSingles table
        # REPLACE INTO is used so it inserts or updates if it already exists
        sql = f"REPLACE INTO `tabSingles` (`doctype`, `field`, `value`) VALUES ({sql_quote(doctype)}, {sql_quote(fieldname)}, {sql_quote(value)});"
        sql_statements.append(sql)
        
    return sql_statements

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 standalone_migrator.py <source.db> <output.sql>")
        sys.exit(1)
        
    db_path = sys.argv[1]
    out_path = sys.argv[2]
    
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        sys.exit(1)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    sql_lines = [
        "/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;",
        "/*!40101 SET NAMES utf8mb4 */;",
        "/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;",
        "/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;",
        ""
    ]

    print("Generating schema imports...")
    for table in tables:
        doctype = get_mapping(table)
        if not doctype:
            continue
            
        cursor.execute(f"PRAGMA table_info(`{table}`)")
        columns = [c[1] for c in cursor.fetchall()]

        try:
            cursor.execute(f"SELECT * FROM `{table}`")
        except sqlite3.OperationalError:
            continue
            
        rows = cursor.fetchall()
        for row in rows:
            doc_dict = dict(zip(columns, row))
            if not doc_dict.get("name"):
                continue

            doc_dict = rename_fields(doctype, doc_dict)

            if doctype == "Print Format":
                html = doc_dict.get("html", "")
                if html:
                    html = re.sub(r'v-if="([^"]+)"', r'{% if \1 %}', html)
                    html = html.replace('v-else', '{% else %}')
                    html = re.sub(r'v-for="([^"]+) in ([^"]+)"', r'{% for \1 in \2 %}', html)
                    html = re.sub(r':key="[^"]+"', '', html)
                    
                    html = html.replace('doc.netTotal', 'books_format(doc.net_total, "Currency", doc.currency)')
                    html = html.replace('doc.grandTotal', 'books_format(doc.grand_total, "Currency", doc.currency)')
                    html = html.replace('doc.totalDiscount', 'books_format(doc.total_discount, "Currency", doc.currency)')
                    html = html.replace('doc.discountAfterTax', 'doc.discount_after_tax')
                    html = html.replace('row.hsnCode', 'row.hsn_code')
                    html = html.replace('print.companyName', '(print.company_name or "") | e')
                    html = html.replace('print.displayLogo', 'print.display_logo')
                    html = html.replace('print.logo', '{{ print.logo }}')
                    html = html.replace('print.gstin', 'print.gstin')
                    html = html.replace('print.address', 'print.address')
                    html = html.replace('print.phone', 'print.phone')
                    html = html.replace('print.email', 'print.email')
                    html = html.replace('doc.grandTotalInWords', 'totals.grand_total_in_words')
                    html = html.replace('doc.amountInWords', 'totals.amount_paid_in_words')
                    html = re.sub(r't\`([^\`]+)\`', r'{{ _("\1") }}', html)
                    
                    scale_css = "<style>@media print { html, body { font-size: 12px !important; } .page-break-avoid, section, footer, .flex { page-break-inside: avoid !important; break-inside: avoid !important; } }</style>\\n"
                    tailwind_link = '<link href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" rel="stylesheet">\\n'
                    html = tailwind_link + scale_css + "{%- set print = get_print_settings() -%}\\n{%- set totals = get_print_totals(doc) if doc else None -%}\\n" + html
                    
                    doc_dict["html"] = html
                    doc_dict["custom_format"] = 1
                    
                    if "doc_type" not in doc_dict or not doc_dict["doc_type"]:
                        doc_dict["doc_type"] = "Books Sales Invoice"
                    doc_dict["print_format_for"] = "DocType"

            if doctype == "Books Payment" and not doc_dict.get("amount_paid"):
                doc_dict["amount_paid"] = doc_dict.get("amount", 0)

            if "name" in doc_dict:
                del doc_dict["name"]

            fields = list(doc_dict.keys())
            fields.append("name")
            
            fixed_values = []
            for f in fields:
                if f == "name":
                    fixed_values.append(row[columns.index("name")] if "name" in columns else "".join(random.choices(string.ascii_letters + string.digits, k=10)))
                elif f in doc_dict:
                    v = doc_dict[f]
                    if isinstance(v, dict) or isinstance(v, list):
                        v = json.dumps(v)
                    elif isinstance(v, str) and re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', v):
                        v = v.replace("T", " ").replace("Z", "")
                    fixed_values.append(v)
                else:
                    fixed_values.append(None)
                    
            if not re.match(r'^[a-zA-Z0-9_\s]+$', doctype):
                continue
                
            valid_fields = []
            valid_values = []
            for i, c in enumerate(fields):
                v = fixed_values[i]
                if v is not None and re.match(r'^[a-zA-Z0-9_]+$', c):
                    valid_fields.append(c)
                    valid_values.append(v)
                    
            if not valid_fields:
                continue

            cols_sql = ", ".join([f"`{c}`" for c in valid_fields])
            vals_sql = ", ".join([sql_quote(v) for v in valid_values])
            
            sql_lines.append(f"REPLACE INTO `tab{doctype}` ({cols_sql}) VALUES ({vals_sql});")

    print("Generating settings imports...")
    settings_sqls = generate_settings_sql(conn)
    sql_lines.extend(settings_sqls)
    
    print("Rebuilding nested set trees...")
    cursor.execute("SELECT name, parentAccount FROM `Account`")
    accounts_rows = cursor.fetchall()
    tree = {}
    roots = []
    for row in accounts_rows:
        tree[row[0]] = {"children": [], "lft": 0, "rgt": 0}
    for row in accounts_rows:
        name, parent = row[0], row[1]
        if parent and parent in tree:
            tree[parent]["children"].append(name)
        else:
            roots.append(name)
            
    counter = 1
    def traverse(node):
        nonlocal counter
        tree[node]["lft"] = counter
        counter += 1
        for child in sorted(tree[node]["children"]):
            traverse(child)
        tree[node]["rgt"] = counter
        counter += 1
        
    for root in sorted(roots):
        traverse(root)
        
    for name, data in tree.items():
        sql_lines.append(f"UPDATE `tabBooks Account` SET lft={data['lft']}, rgt={data['rgt']} WHERE name={sql_quote(name)};")

    sql_lines.extend([
        "",
        "/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;",
        "/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;"
    ])

    print(f"Writing to {out_path}...")
    with open(out_path, "w") as f:
        f.write("\n".join(sql_lines))
        
    print(f"Successfully generated standalone migration dump! Run with: bench --site <site-name> mariadb < {out_path}")

if __name__ == "__main__":
    main()
