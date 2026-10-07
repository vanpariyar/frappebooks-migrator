# Frappe Books: V1 (Desktop) to V2 (Web) Migration Kit

This kit provides a fully dependency-free standalone migrator to port your data from the older Frappe Books Desktop app (Electron/SQLite) to the new Frappe Books Web app (Frappe Framework/MariaDB).

## Features
- **Zero Dependencies:** Written in pure Python. It runs completely offline without needing the Frappe Framework, Node.js, or Bench installed.
- **SQL Dump Generation:** It instantly compiles a raw `output.sql` file that can be imported seamlessly into MariaDB.
- **Full Template Translation:** Automatically translates Vue 2 (`v-if`, `v-for`) custom print templates into standard Frappe Jinja templates.
- **Tailwind & PDF Scaling Injection:** Automatically injects the Tailwind CSS v2 CDN and Chrome PDF scaling CSS fixes to ensure invoices render exactly as they did on the Desktop app.
- **Ledger & Stock History:** Safely maps the `AccountingLedgerEntry` to `Books Ledger Entry` and preserves history flawlessly.
- **Nested Sets Tree Rebuilding:** Automatically recalculates `lft` and `rgt` boundaries for accounts to ensure Profit & Loss and Trial Balance reports nest correctly and don't double-count parent/child totals.
- **Settings Migration:** Migrates Settings, Logos, Defaults, Colors, and Email fields correctly.

## How to use the Standalone Migrator

**Step 1. Run the migrator script**
Run the script passing your old SQLite file and the desired output SQL file name:
```bash
python3 standalone_migrator.py "your_sqlite_database.db" "migration_dump.sql"
```

**Step 2. Import into Frappe Books Web App**
Take the generated `migration_dump.sql` file and import it directly into your live Frappe Books v2 site using Bench:
```bash
bench --site <site-name> mariadb < migration_dump.sql
```

## Need Help?
This standalone tool is perfect for offering seamless, turnkey migration services to your clients. Simply ask for their `.db` file, run the Python script locally, and push the generated `.sql` file to their server!
