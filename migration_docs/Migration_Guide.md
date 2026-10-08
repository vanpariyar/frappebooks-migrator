# Frappe Books to ERPNext Migration Guide

This document explains the migration process from the standalone Frappe Books app (and its legacy SQLite database) to standard ERPNext within the same Frappe Bench.

## 1. Overview of the Migration

The migration process generally involves moving data from `tabBooks *` tables into the standard ERPNext `tab*` tables. 

**Native Scripts available:**
The Frappe Books app comes with built-in scripts to migrate basic documents:
- **Sales Invoices**: `apps/frappe_books/frappe_books/migrate_invoices.py`
- **Payments**: `apps/frappe_books/frappe_books/migrate_to_erpnext.py`

*Note: These native scripts may sometimes fail to migrate certain Journal Entries or fully sync all documents.*

## 2. Common Issues & Fixes

### Issue A: Profit and Loss Exactly Doubled in Frappe Books
**Root Cause**: When the `migrate_books.py` script imports the legacy Frappe Books SQLite file (`Sahajanand Digital.books 2.db`), it copies the raw `AccountingLedgerEntry` rows verbatim into `tabBooks Ledger Entry`. Later, when Frappe Books documents (like Sales Invoices) are submitted inside the MariaDB database, the system's `on_submit` hooks generate a *second* set of ledger entries. This results in every transaction being counted twice.

**Solution**: Delete the stale ledger entries that were imported from SQLite directly, leaving only the cleanly auto-generated ones.
```sql
-- Connect to the MariaDB site database
DELETE FROM `tabBooks Ledger Entry` WHERE owner != 'Administrator';
```
*(This assumes the auto-generated ones were created by the 'Administrator' user during migration).*

### Issue B: Missing Journal Entries in ERPNext
**Root Cause**: The default `migrate_to_erpnext.py` focuses largely on Payments and Invoices, occasionally missing direct Journal Entries (like Bank-to-Bank Contra Entries). 

**Solution**: Use the `fix_missing_jv.py` script provided in the root bench directory.
1. Open `fix_missing_jv.py`.
2. Update the `missing_jvs` array with the names of the missing documents (e.g., `missing_jvs = ["JV-1073"]`).
3. Run the script:
   ```bash
   cd sites
   ../env/bin/python ../migration_docs/fix_missing_jv.py
   ```

### Issue C: Minor Debtors/Creditors Discrepancies
**Root Cause**: ERPNext strictly enforces rounding rules on Sales Invoices, whereas older Frappe Books versions may not. When migrating, ERPNext will automatically post fractions of a rupee (e.g., `0.48`) to the `Rounded Off` account, meaning your `Debtors` account will differ slightly between Frappe Books and ERPNext.
**Solution**: This is standard accounting behavior and requires no fix.

## 3. Testing Migration Parity

To ensure your ERPNext data perfectly matches your Frappe Books data, use the `test_migration.py` script.

**How to run the test:**
```bash
cd /Users/multidots/Documents/Github/frappe/books-bench
cd sites
../env/bin/python ../migration_docs/test_migration.py
```

**What it checks:**
1. **Document Counts**: Ensures the exact same number of submitted Sales Invoices, Payments, and Journal Entries exist in both systems.
2. **Financial Totals**: Compares the sum of Grand Totals (for Invoices), Paid Amounts (for Payments), and Total Debits (for JVs).
3. **Missing JVs**: Explicitly identifies any `Books Journal Entry` that failed to copy over to ERPNext.

---
*Generated to help maintain data integrity during cross-app migrations.*
