# MediBill Modern Tkinter Edition

Modern hospital billing desktop application using only:
- Python
- Tkinter/ttk
- MySQL
- ReportLab for PDF invoices

## Navigation
Dashboard | Patients | New Billing | Invoices | Reports

## Features
- Responsive-style resizable Tkinter layout
- Sidebar navigation and modern cards
- Patient management/search
- Itemized medicines, tests, services and consultation
- Total Price, Paid Fee and Pending Fee
- Automatic Pending / Partially Paid / Paid status
- Invoice search/edit/delete
- Professional PDF invoice
- Monthly billing report
- CSV export
- Existing database upgrade support for `paid_amount` and `notes`

## Install
pip install -r requirements.txt

Import `database.sql` into MySQL, then edit the `DB` settings at the top of `hospital_billing.py`.

Default login:
admin / admin123

PDFs are saved under `~/MediBill_Invoices/`.
