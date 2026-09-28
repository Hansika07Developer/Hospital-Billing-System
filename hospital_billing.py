
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from decimal import Decimal
from pathlib import Path
import datetime as dt
import csv, hashlib

import mysql.connector
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

APP = "MediBill - Hospital Billing System"
BG, CARD, TEXT, MUTED = "#F4F7FB", "#FFFFFF", "#182230", "#667085"
BLUE, NAV, NAV2, BORDER = "#2563EB", "#0F172A", "#1E293B", "#E4E7EC"
GREEN, RED = "#12B76A", "#F04438"
FONT = "Segoe UI"

BILLING_CATALOG = {
    "Medicine": {
        "Paracetamol 500 mg": 20, "Amoxicillin 500 mg": 85,
        "Azithromycin 500 mg": 110, "Cetirizine 10 mg": 15,
        "Omeprazole 20 mg": 35, "Metformin 500 mg": 25,
        "Amlodipine 5 mg": 18, "Ibuprofen 400 mg": 30,
        "ORS Sachet": 22, "Cough Syrup 100 ml": 95,
        "Vitamin C 500 mg": 40, "Antiseptic Cream 20 g": 55,
    },
    "Test": {
        "Complete Blood Count (CBC)": 350, "Blood Glucose": 120,
        "Lipid Profile": 650, "Liver Function Test (LFT)": 700,
        "Kidney Function Test (KFT)": 600, "Thyroid Profile (TSH)": 450,
        "Urine Routine": 180, "HbA1c": 400,
        "Dengue NS1": 750, "Malaria Test": 350,
        "Chest X-Ray": 500, "ECG": 300,
    },
    "Service": {
        "General Consultation": 500, "Specialist Consultation": 900,
        "Emergency Consultation": 1200, "Nursing Care": 350,
        "Injection Administration": 150, "Dressing Service": 250,
        "Nebulization": 300, "Physiotherapy Session": 600,
        "Day Care Service": 1500, "Ambulance Service": 1800,
        "Bed Charge (per day)": 2000, "Wound Care": 400,
    },
    "Consultation": {
        "General Physician": 500, "Cardiology Consultation": 1000,
        "Dermatology Consultation": 800, "Pediatric Consultation": 700,
        "Orthopedic Consultation": 900, "Gynecology Consultation": 900,
        "Neurology Consultation": 1200, "ENT Consultation": 750,
        "Dental Consultation": 600, "Dietitian Consultation": 500,
    },
    "Other": {
        "Registration Fee": 100, "Medical Certificate": 250,
        "Wrist Band": 30, "Surgical Mask": 20,
        "Medical Record Copy": 100, "Equipment Usage": 350,
        "PPE Kit": 250, "Specialist Report": 400,
        "Health Checkup Package": 2500, "Other (custom)": 0,
    },
}

def dec(x):
    try: return Decimal(str(x or 0))
    except: return Decimal("0")
def money(x): return f"₹{dec(x):,.2f}"
def hp(x): return hashlib.sha256(x.encode()).hexdigest()

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "hospital_billing"
}


class Database:
    def __init__(self):
        self.c = None

    def connect(self):
        if self.c is None or not self.c.is_connected():
            self.c = mysql.connector.connect(**DB_CONFIG)
            self.setup()

    def q(self, sql, p=(), fetch=False, many=False):
        self.connect()
        cur = self.c.cursor(dictionary=True)

        try:
            if many:
                cur.executemany(sql, p)
            else:
                cur.execute(sql, p)

            out = cur.fetchall() if fetch else cur.lastrowid
            self.c.commit()
            return out

        finally:
            cur.close()

    def scalar(self, sql, p=()):
        r = self.q(sql, p, True)
        return next(iter(r[0].values())) if r else 0

    def setup(self):
        self.q("""
            CREATE TABLE IF NOT EXISTS users(
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(50) DEFAULT 'Admin'
            )
        """)

        self.q("""
            CREATE TABLE IF NOT EXISTS patients(
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                age INT,
                gender VARCHAR(20),
                phone VARCHAR(30),
                address VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.q("""
            CREATE TABLE IF NOT EXISTS bills(
                id INT AUTO_INCREMENT PRIMARY KEY,
                patient_id INT NOT NULL,
                bill_date DATE NOT NULL,
                doctor VARCHAR(150),
                total_amount DECIMAL(12,2) DEFAULT 0,
                paid_amount DECIMAL(12,2) DEFAULT 0,
                payment_status VARCHAR(30) DEFAULT 'Pending',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(patient_id) REFERENCES patients(id)
            )
        """)

        self.q("""
            CREATE TABLE IF NOT EXISTS bill_items(
                id INT AUTO_INCREMENT PRIMARY KEY,
                bill_id INT NOT NULL,
                item_type VARCHAR(50) NOT NULL,
                description VARCHAR(255) NOT NULL,
                quantity DECIMAL(10,2) DEFAULT 1,
                unit_price DECIMAL(12,2) DEFAULT 0,
                amount DECIMAL(12,2) DEFAULT 0,
                FOREIGN KEY(bill_id) REFERENCES bills(id) ON DELETE CASCADE
            )
        """)

        cols = self.q("SHOW COLUMNS FROM bills", fetch=True)
        names = {x["Field"] for x in cols}

        if "paid_amount" not in names:
            self.q("""
                ALTER TABLE bills
                ADD paid_amount DECIMAL(12,2) DEFAULT 0
                AFTER total_amount
            """)

        if "notes" not in names:
            self.q("""
                ALTER TABLE bills
                ADD notes TEXT
                AFTER payment_status
            """)

        if "doctor" not in names:
            self.q("ALTER TABLE bills ADD doctor VARCHAR(150) AFTER bill_date")

        if not self.q("SELECT id FROM users LIMIT 1", fetch=True):
            self.q(
                "INSERT INTO users(username,password,role) VALUES(%s,%s,%s)",
                ("admin", hp("admin123"), "Administrator")
            )
class Scroll(ttk.Frame):
    def __init__(self,p):
        super().__init__(p); self.c=tk.Canvas(self,bg=BG,highlightthickness=0)
        self.s=ttk.Scrollbar(self,command=self.c.yview); self.i=ttk.Frame(self.c)
        self.w=self.c.create_window((0,0),window=self.i,anchor="nw")
        self.i.bind("<Configure>",lambda e:self.c.configure(scrollregion=self.c.bbox("all")))
        self.c.bind("<Configure>",lambda e:self.c.itemconfigure(self.w,width=e.width))
        self.c.configure(yscrollcommand=self.s.set); self.c.pack(side="left",fill="both",expand=True); self.s.pack(side="right",fill="y")

class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title(APP); self.geometry("1320x800"); self.minsize(1050,650)
        self.configure(bg=BG); self.db=Database(); self.user=None; self.page=""; self.items=[]
        self.style(); self.protocol("WM_DELETE_WINDOW",self.destroy); self.login()

    def style(self):
        s=ttk.Style(self)
        try:s.theme_use("clam")
        except:pass
        s.configure(".",font=(FONT,10)); s.configure("TFrame",background=BG)
        s.configure("TEntry",padding=8); s.configure("TCombobox",padding=7)
        s.configure("Treeview",rowheight=34); s.configure("Treeview.Heading",font=(FONT,9,"bold"),padding=8)
        s.configure("Primary.TButton",font=(FONT,10,"bold"),padding=(14,9))
        s.configure("TButton",padding=(12,8))

    def login(self):
        for x in self.winfo_children(): x.destroy()
        f=tk.Frame(self,bg=BG); f.pack(fill="both",expand=True)
        c=tk.Frame(f,bg=CARD,highlightbackground=BORDER,highlightthickness=1)
        c.place(relx=.5,rely=.5,anchor="center",width=430,height=410)
        tk.Label(c,text="MediBill",bg=CARD,fg=BLUE,font=(FONT,30,"bold")).pack(pady=(45,4))
        tk.Label(c,text="Hospital Billing Management",bg=CARD,fg=TEXT,font=(FONT,13,"bold")).pack()
        form=tk.Frame(c,bg=CARD); form.pack(fill="x",padx=45,pady=30)
        tk.Label(form,text="Username",bg=CARD,fg=TEXT).pack(anchor="w")
        self.u=ttk.Entry(form); self.u.pack(fill="x",pady=(4,14))
        tk.Label(form,text="Password",bg=CARD,fg=TEXT).pack(anchor="w")
        self.p=ttk.Entry(form,show="•"); self.p.pack(fill="x",pady=(4,18))
        ttk.Button(form,text="Sign In",style="Primary.TButton",command=self.do_login).pack(fill="x")
        tk.Label(c,text="Default login: admin / admin123",bg=CARD,fg=MUTED,font=(FONT,8)).pack()
        self.p.bind("<Return>",lambda e:self.do_login()); self.u.focus()

    def do_login(self):
        try:
            r=self.db.q("SELECT id,username,role FROM users WHERE username=%s AND password=%s",
                        (self.u.get().strip(),hp(self.p.get())),True)
            if not r: messagebox.showerror("Login","Invalid username or password."); return
            self.user=r[0]; self.shell(); self.dashboard()
        except Exception as e: messagebox.showerror("Database",str(e))

    def shell(self):
        for x in self.winfo_children(): x.destroy()
        self.grid_columnconfigure(1,weight=1); self.grid_rowconfigure(0,weight=1)
        side=tk.Frame(self,bg=NAV,width=225); side.grid(row=0,column=0,sticky="nsew"); side.grid_propagate(False)
        tk.Label(side,text="MediBill",bg=NAV,fg="white",font=(FONT,23,"bold")).pack(anchor="w",padx=22,pady=(28,2))
        tk.Label(side,text="Hospital Billing",bg=NAV,fg="#94A3B8").pack(anchor="w",padx=22,pady=(0,25))
        self.nav={}
        for k,txt in [("dash","⌂  Dashboard"),("patients","♙  Patients"),("bill","＋  New Billing"),("inv","▣  Invoices"),("report","◔  Reports")]:
            b=tk.Button(side,text=txt,anchor="w",relief="flat",bd=0,bg=NAV,fg="#CBD5E1",
                        activebackground=NAV2,activeforeground="white",font=(FONT,10,"bold"),
                        padx=18,pady=11,command=lambda x=k:self.go(x))
            b.pack(fill="x",padx=10,pady=2); self.nav[k]=b
        bot=tk.Frame(side,bg=NAV); bot.pack(side="bottom",fill="x",padx=18,pady=20)
        tk.Label(bot,text=self.user["username"],bg=NAV,fg="white",font=(FONT,10,"bold")).pack(anchor="w")
        tk.Label(bot,text=self.user["role"],bg=NAV,fg="#94A3B8",font=(FONT,8)).pack(anchor="w",pady=(2,10))
        tk.Button(bot,text="Sign out",command=self.login,bg=NAV2,fg="white",relief="flat",bd=0,pady=7).pack(fill="x")
        main=tk.Frame(self,bg=BG); main.grid(row=0,column=1,sticky="nsew"); main.grid_rowconfigure(1,weight=1); main.grid_columnconfigure(0,weight=1)
        self.head=tk.Frame(main,bg=CARD,highlightbackground=BORDER,highlightthickness=1); self.head.grid(row=0,column=0,sticky="ew")
        self.head.grid_columnconfigure(0,weight=1)
        self.title=tk.Label(self.head,text="",bg=CARD,fg=TEXT,font=(FONT,17,"bold")); self.title.grid(row=0,column=0,sticky="w",padx=25,pady=20)
        tk.Label(self.head,text=self.user["username"],bg="#EFF6FF",fg=BLUE,font=(FONT,9,"bold"),padx=12,pady=7).grid(row=0,column=1,padx=25)
        self.content=tk.Frame(main,bg=BG); self.content.grid(row=1,column=0,sticky="nsew"); self.content.grid_rowconfigure(0,weight=1); self.content.grid_columnconfigure(0,weight=1)

    def go(self,k):
        {"dash":self.dashboard,"patients":self.patients,"bill":self.billing,"inv":self.invoices,"report":self.reports}[k]()

    def start(self,k,title):
        self.page=k; self.title.config(text=title)
        for x in self.content.winfo_children(): x.destroy()
        for n,b in self.nav.items(): b.config(bg=NAV)
        self.nav[k].config(bg=NAV2)

    def panel(self,p,title,row=0,col=0):
        f=tk.Frame(p,bg=CARD,highlightbackground=BORDER,highlightthickness=1)
        f.grid(row=row,column=col,sticky="nsew",padx=7,pady=7); f.grid_columnconfigure(0,weight=1)
        tk.Label(f,text=title,bg=CARD,fg=TEXT,font=(FONT,12,"bold")).grid(row=0,column=0,sticky="w",padx=18,pady=(15,10))
        return f

    def tree(self,p,cols,row=1):
        box=tk.Frame(p,bg=CARD); box.grid(row=row,column=0,sticky="nsew",padx=12,pady=(0,12))
        p.grid_rowconfigure(row,weight=1)
        ids=[x[0] for x in cols]; t=ttk.Treeview(box,columns=ids,show="headings")
        for i,h,w in cols:t.heading(i,text=h);t.column(i,width=w,anchor="w")
        s=ttk.Scrollbar(box,command=t.yview);t.configure(yscrollcommand=s.set)
        t.pack(side="left",fill="both",expand=True);s.pack(side="right",fill="y");return t

    def card(self,p,title,value,col,sub=""):
        p.grid_columnconfigure(col,weight=1)
        f=tk.Frame(p,bg=CARD,highlightbackground=BORDER,highlightthickness=1);f.grid(row=0,column=col,sticky="nsew",padx=6,pady=6)
        tk.Label(f,text=title.upper(),bg=CARD,fg=MUTED,font=(FONT,8,"bold")).pack(anchor="w",padx=16,pady=(14,2))
        tk.Label(f,text=value,bg=CARD,fg=TEXT,font=(FONT,19,"bold")).pack(anchor="w",padx=16)
        tk.Label(f,text=sub,bg=CARD,fg=MUTED,font=(FONT,8)).pack(anchor="w",padx=16,pady=(2,14))

    def dashboard(self):
        self.start("dash","Dashboard"); s=Scroll(self.content);s.grid(row=0,column=0,sticky="nsew");b=s.i;b.grid_columnconfigure(0,weight=1)
        tk.Label(b,text="Good day 👋",bg=BG,fg=TEXT,font=(FONT,21,"bold")).grid(row=0,column=0,sticky="w",padx=22,pady=(20,2))
        tk.Label(b,text="Monitor billing, collections and outstanding payments.",bg=BG,fg=MUTED).grid(row=1,column=0,sticky="w",padx=22,pady=(0,12))
        total=self.db.scalar("SELECT COALESCE(SUM(total_amount),0) FROM bills"); paid=self.db.scalar("SELECT COALESCE(SUM(paid_amount),0) FROM bills")
        cards=tk.Frame(b,bg=BG);cards.grid(row=2,column=0,sticky="ew",padx=15)
        self.card(cards,"Total Amount",money(total),0,"All invoices");self.card(cards,"Paid Fee",money(paid),1,"Collected")
        self.card(cards,"Pending Fee",money(dec(total)-dec(paid)),2,"Outstanding");self.card(cards,"Total Bills",str(self.db.scalar("SELECT COUNT(*) FROM bills")),3,"Invoices")
        lower=tk.Frame(b,bg=BG);lower.grid(row=3,column=0,sticky="nsew",padx=22,pady=14);lower.grid_columnconfigure(0,weight=3);lower.grid_columnconfigure(1,weight=2)
        p=self.panel(lower,"Recent invoices",0,0);t=self.tree(p,[("id","Invoice",90),("patient","Patient",170),("date","Date",110),("total","Total",100),("paid","Paid",100),("pending","Pending",110)])
        rows=self.db.q("""SELECT b.id,p.name patient,b.bill_date,b.total_amount,b.paid_amount,b.total_amount-b.paid_amount pending
                         FROM bills b JOIN patients p ON p.id=b.patient_id ORDER BY b.id DESC LIMIT 8""",fetch=True)
        for r in rows:t.insert("", "end",values=(f"INV-{r['id']:05d}",r["patient"],r["bill_date"],money(r["total_amount"]),money(r["paid_amount"]),money(r["pending"])))
        p2=self.panel(lower,"Pending payments",0,1);t2=self.tree(p2,[("patient","Patient",160),("pending","Pending",110),("status","Status",120)])
        rows=self.db.q("""SELECT p.name patient,b.total_amount-b.paid_amount pending,b.payment_status
                          FROM bills b JOIN patients p ON p.id=b.patient_id WHERE b.total_amount>b.paid_amount ORDER BY pending DESC LIMIT 8""",fetch=True)
        for r in rows:t2.insert("", "end",values=(r["patient"],money(r["pending"]),r["payment_status"]))
        q=tk.Frame(b,bg=BG);q.grid(row=4,column=0,sticky="e",padx=22,pady=10)
        ttk.Button(q,text="+ New Billing",style="Primary.TButton",command=self.billing).pack(side="left",padx=4)
        ttk.Button(q,text="Patients",command=self.patients).pack(side="left",padx=4);ttk.Button(q,text="Invoices",command=self.invoices).pack(side="left",padx=4)

    def patients(self):
        self.start("patients","Patients");s=Scroll(self.content);s.grid(row=0,column=0,sticky="nsew");b=s.i;b.grid_columnconfigure(0,weight=1)
        f=self.panel(b,"Add patient",0,0);f.grid_columnconfigure(0,weight=1);f.grid_columnconfigure(1,weight=1)
        self.pvars={k:tk.StringVar() for k in ["name","age","gender","phone","address"]}
        labels=["Full name","Age","Gender","Phone","Address"]
        for i,k in enumerate(self.pvars):
            c=i%2;r=1+(i//2)*2;tk.Label(f,text=labels[i],bg=CARD,fg=TEXT,font=(FONT,9,"bold")).grid(row=r,column=c,sticky="w",padx=18,pady=(5,3))
            w=ttk.Combobox(f,textvariable=self.pvars[k],values=["Male","Female","Other"],state="readonly") if k=="gender" else ttk.Entry(f,textvariable=self.pvars[k])
            w.grid(row=r+1,column=c,sticky="ew",padx=18,pady=(0,7))
        ttk.Button(f,text="Save Patient",style="Primary.TButton",command=self.add_patient).grid(row=7,column=0,columnspan=2,sticky="e",padx=18,pady=14)
        p=self.panel(b,"Patient directory",0,1);bar=tk.Frame(p,bg=CARD);bar.grid(row=1,column=0,sticky="ew",padx=18,pady=(0,8));bar.grid_columnconfigure(0,weight=1)
        self.ps=ttk.Entry(bar);self.ps.grid(row=0,column=0,sticky="ew",padx=(0,8));self.ps.insert(0,"Search name / phone")
        self.ps.bind("<FocusIn>",lambda e:self.placeholder(self.ps,"Search name / phone"));ttk.Button(bar,text="Refresh",command=self.refresh_patients).grid(row=0,column=1)
        self.pt=self.tree(p,[("id","ID",60),("name","Name",220),("age","Age",70),("gender","Gender",90),("phone","Phone",140),("address","Address",250)])
        self.refresh_patients()

    def placeholder(self,w,text):
        if w.get()==text:w.delete(0,"end")

    def add_patient(self):
        v=[self.pvars[k].get().strip() for k in ["name","age","gender","phone","address"]]
        if not v[0]:return messagebox.showwarning("Patient","Full name is required.")
        self.db.q("INSERT INTO patients(name,age,gender,phone,address) VALUES(%s,%s,%s,%s,%s)",tuple(v))
        messagebox.showinfo("Patient","Patient added.");self.refresh_patients()
        for x in self.pvars.values():x.set("")

    def refresh_patients(self):
        if not hasattr(self,"pt") or not self.pt.winfo_exists():return
        for x in self.pt.get_children():self.pt.delete(x)
        q=self.ps.get().strip();q="" if q=="Search name / phone" else q
        for r in self.db.q("""SELECT id,name,age,gender,phone,address FROM patients
                              WHERE name LIKE %s OR phone LIKE %s ORDER BY id DESC""",(f"%{q}%",f"%{q}%"),True):
            self.pt.insert("", "end",values=(r["id"],r["name"],r["age"] or "",r["gender"] or "",r["phone"] or "",r["address"] or ""))

    def billing(self,bill_id=None):
        self.start("bill","Edit Invoice" if bill_id else "New Billing")
        s=Scroll(self.content);s.grid(row=0,column=0,sticky="nsew")
        b=s.i;b.grid_columnconfigure(0,weight=7);b.grid_columnconfigure(1,weight=3);b.grid_rowconfigure(2,weight=1)

        p=self.panel(b,"Patient Information",0,0)
        for col in range(4):p.grid_columnconfigure(col,weight=1)
        patients=self.db.q("SELECT id,name,age,gender,phone,address FROM patients ORDER BY name",fetch=True)
        self.patient_records={}
        self.pmap={}
        values=[]
        for row in patients:
            label=f"{row['id']} • {row['name']}"
            self.patient_records[label]=row
            self.pmap[label]=row["id"]
            values.append(label)

        self.patient_mode=tk.StringVar(value="existing" if values else "manual")
        tk.Label(p,text="Patient entry",bg=CARD,fg=TEXT).grid(row=1,column=0,padx=18,pady=7,sticky="w")
        self.patient_mode_frame=tk.Frame(p,bg=CARD)
        self.patient_mode_frame.grid(row=1,column=1,columnspan=3,sticky="w",padx=18,pady=7)
        ttk.Radiobutton(self.patient_mode_frame,text="Existing patient",variable=self.patient_mode,value="existing",command=self.toggle_patient_fields).pack(side="left",padx=(0,18))
        ttk.Radiobutton(self.patient_mode_frame,text="Enter new patient",variable=self.patient_mode,value="manual",command=self.toggle_patient_fields).pack(side="left")

        tk.Label(p,text="Select patient",bg=CARD,fg=TEXT).grid(row=2,column=0,padx=18,pady=7,sticky="w")
        self.bc=ttk.Combobox(p,values=values,state="readonly")
        self.bc.grid(row=2,column=1,columnspan=3,padx=18,pady=7,sticky="ew")
        self.bc.bind("<<ComboboxSelected>>",self.load_patient_details)

        self.patient_fields={
            "name": tk.StringVar(),
            "age": tk.StringVar(),
            "gender": tk.StringVar(value="Male"),
            "phone": tk.StringVar(),
            "address": tk.StringVar(),
        }
        self.patient_id_text=tk.StringVar(value="Assigned when saved")
        tk.Label(p,text="Patient ID",bg=CARD,fg=TEXT).grid(row=3,column=0,padx=18,pady=7,sticky="w")
        tk.Label(p,textvariable=self.patient_id_text,bg=CARD,fg=BLUE,font=(FONT,9,"bold")).grid(row=3,column=1,padx=18,pady=7,sticky="w")
        self.patient_inputs={}
        patient_layout=[("Name","name",3,2),("Age","age",4,0),("Phone","phone",4,2),("Gender","gender",5,0),("Address","address",5,2)]
        for label,key,row,col in patient_layout:
            tk.Label(p,text=label,bg=CARD,fg=TEXT).grid(row=row,column=col,padx=18,pady=7,sticky="w")
            if key=="gender":
                widget=ttk.Combobox(p,textvariable=self.patient_fields[key],values=["Male","Female","Other"],state="readonly")
            else:
                widget=ttk.Entry(p,textvariable=self.patient_fields[key])
            widget.grid(row=row,column=col+1,padx=18,pady=7,sticky="ew")
            self.patient_inputs[key]=widget

        details=self.panel(b,"Invoice Details",1,0)
        for col in range(4):details.grid_columnconfigure(col,weight=1)
        tk.Label(details,text="Bill date",bg=CARD,fg=TEXT).grid(row=1,column=0,padx=18,pady=8,sticky="w")
        self.bd=ttk.Entry(details);self.bd.insert(0,str(dt.date.today()));self.bd.grid(row=1,column=1,padx=18,pady=8,sticky="ew")
        tk.Label(details,text="Doctor",bg=CARD,fg=TEXT).grid(row=1,column=2,padx=18,pady=8,sticky="w")
        self.doctor=ttk.Entry(details);self.doctor.grid(row=1,column=3,padx=18,pady=8,sticky="ew")
        tk.Label(details,text="Notes",bg=CARD,fg=TEXT).grid(row=2,column=0,padx=18,pady=8,sticky="w")
        self.bn=ttk.Entry(details);self.bn.grid(row=2,column=1,columnspan=3,padx=18,pady=8,sticky="ew")

        self.toggle_patient_fields()
        if self.patient_mode.get()=="existing" and values:
            self.bc.current(0)
            self.load_patient_details()

        ip=self.panel(b,"Bill Items",2,0)
        bar=tk.Frame(ip,bg=CARD);bar.grid(row=1,column=0,sticky="ew",padx=18,pady=(0,8))
        for col,weight in enumerate((1,2,1,1,1,0)):
            bar.grid_columnconfigure(col,weight=weight)
        for col,label in enumerate(("Category","Catalog option","Description","Qty","Unit price","")):
            tk.Label(bar,text=label,bg=CARD,fg=MUTED,font=(FONT,8,"bold")).grid(row=0,column=col,sticky="w",padx=4,pady=(0,3))
        self.it=ttk.Combobox(bar,values=list(BILLING_CATALOG),state="readonly",width=16)
        self.it.set("Medicine");self.it.grid(row=1,column=0,padx=4,sticky="ew")
        self.it.bind("<<ComboboxSelected>>",self.update_catalog_items)
        self.item_name=tk.StringVar()
        self.catalog_item=ttk.Combobox(bar,textvariable=self.item_name,state="readonly",width=28)
        self.catalog_item.grid(row=1,column=1,padx=4,sticky="ew")
        self.catalog_item.bind("<<ComboboxSelected>>",self.select_catalog_item)
        self.idesc=ttk.Entry(bar,width=28);self.idesc.grid(row=1,column=2,padx=4,sticky="ew")
        self.idesc.insert(0,"Description")
        self.idesc.bind("<FocusIn>",lambda e:self.placeholder(self.idesc,"Description"))
        self.iqty=ttk.Entry(bar,width=8);self.iqty.insert(0,"1");self.iqty.grid(row=1,column=3,padx=4,sticky="ew")
        self.iprice=ttk.Entry(bar,width=12);self.iprice.grid(row=1,column=4,padx=4,sticky="ew")
        self.add_item_button=ttk.Button(bar,text="Add Item",style="Primary.TButton",command=self.add_item)
        self.add_item_button.grid(row=1,column=5,padx=5)
        tk.Label(ip,text="Choose a catalog item to fill its description and suggested price. You can adjust the price before adding.",bg=CARD,fg=MUTED,font=(FONT,8)).grid(row=2,column=0,sticky="w",padx=18,pady=(0,8))
        self.items=[];self.itt=self.tree(ip,[("type","Type",100),("desc","Description",340),("qty","Qty",70),("price","Unit Price",120),("amount","Amount",130)],row=3)
        self.editing_item_index=None
        self.itt.bind("<<TreeviewSelect>>",self.select_bill_item)
        self.itt.bind("<Double-1>",self.remove_item)
        item_actions=tk.Frame(ip,bg=CARD);item_actions.grid(row=4,column=0,sticky="e",padx=18,pady=(0,12))
        self.update_item_button=ttk.Button(item_actions,text="Update Selected",command=self.update_item,state="disabled")
        self.update_item_button.pack(side="left",padx=4)
        self.remove_item_button=ttk.Button(item_actions,text="Remove Selected",command=self.remove_item,state="disabled")
        self.remove_item_button.pack(side="left",padx=4)
        self.update_catalog_items()
        pay=self.panel(b,"Invoice Summary",0,1)
        pay.grid(row=0,column=1,rowspan=3,sticky="nsew",padx=7,pady=7)
        pay.grid_columnconfigure(0,weight=1)
        tk.Label(pay,text="Review payment breakdown before saving.",bg=CARD,fg=MUTED,wraplength=250,justify="left").grid(row=1,column=0,sticky="w",padx=18,pady=(0,8))
        self.tv,self.pv,self.rv=[tk.StringVar(value="₹0.00") for _ in range(3)]
        for row,(label,value,color) in enumerate([("TOTAL PRICE",self.tv,BLUE),("FEE PAID",self.pv,GREEN),("PENDING FEE",self.rv,RED)],start=2):
            card=tk.Frame(pay,bg="#F8FAFC",highlightbackground=BORDER,highlightthickness=1)
            card.grid(row=row,column=0,sticky="ew",padx=18,pady=6)
            tk.Label(card,text=label,bg="#F8FAFC",fg=MUTED,font=(FONT,8,"bold")).pack(anchor="w",padx=14,pady=(10,2))
            tk.Label(card,textvariable=value,bg="#F8FAFC",fg=color,font=(FONT,18,"bold")).pack(anchor="w",padx=14,pady=(0,10))
        tk.Label(pay,text="Fee paid",bg=CARD,fg=TEXT).grid(row=5,column=0,sticky="w",padx=18,pady=(10,3))
        self.pa=ttk.Entry(pay);self.pa.grid(row=6,column=0,sticky="ew",padx=18)
        self.pa.bind("<KeyRelease>",lambda e:self.summary())
        self.pa.bind("<FocusOut>",lambda e:self.summary())
        self.payment_status=tk.StringVar(value="Pending")
        tk.Label(pay,text="Payment status",bg=CARD,fg=TEXT).grid(row=7,column=0,sticky="w",padx=18,pady=(12,2))
        tk.Label(pay,textvariable=self.payment_status,bg=CARD,fg=TEXT,font=(FONT,10,"bold")).grid(row=8,column=0,sticky="w",padx=18)
        actions=tk.Frame(pay,bg=CARD);actions.grid(row=9,column=0,sticky="ew",padx=14,pady=18)
        ttk.Button(actions,text="Save Bill",command=lambda:self.save_bill(False,bill_id)).pack(fill="x",pady=4)
        ttk.Button(actions,text="Save Bill & Generate PDF",style="Primary.TButton",command=lambda:self.save_bill(True,bill_id)).pack(fill="x",pady=4)
        ttk.Button(actions,text="Reset Form",command=lambda:self.billing()).pack(fill="x",pady=4)
        if bill_id:self.load_bill(bill_id)

    def toggle_patient_fields(self):
        if not hasattr(self, "patient_mode"):
            return
        if self.patient_mode.get() == "existing":
            self.bc.grid()
            for widget in self.patient_inputs.values():
                widget.configure(state="disabled")
            if self.bc.get():
                self.load_patient_details()
        else:
            self.bc.grid_remove()
            for key,widget in self.patient_inputs.items():
                widget.configure(state="readonly" if key=="gender" else "normal")
            self.patient_id_text.set("Assigned when saved")
            for value in self.patient_fields.values():
                value.set("" if value is not self.patient_fields["gender"] else "Male")

    def load_patient_details(self, event=None):
        patient=self.patient_records.get(self.bc.get())
        if not patient:
            return
        self.patient_id_text.set(f"PAT-{patient['id']:05d}")
        self.patient_fields["name"].set(patient["name"] or "")
        self.patient_fields["age"].set(patient["age"] or "")
        self.patient_fields["gender"].set(patient["gender"] or "Other")
        self.patient_fields["phone"].set(patient["phone"] or "")
        self.patient_fields["address"].set(patient["address"] or "")

    def update_catalog_items(self, event=None):
        category=self.it.get()
        options=list(BILLING_CATALOG.get(category,{}))
        options.append("Custom item...")
        self.catalog_item.configure(values=options)
        self.item_name.set("")
        self.idesc.delete(0,"end")
        self.iprice.delete(0,"end")

    def select_catalog_item(self, event=None):
        name=self.item_name.get()
        if name=="Custom item...":
            self.idesc.delete(0,"end")
            self.iprice.delete(0,"end")
            self.idesc.focus_set()
            return
        price=BILLING_CATALOG.get(self.it.get(),{}).get(name)
        if price is None:
            return
        self.idesc.delete(0,"end")
        self.idesc.insert(0,name)
        self.iprice.delete(0,"end")
        self.iprice.insert(0,str(price))

    def add_item(self):
        try:
            d=self.idesc.get().strip()
            if d=="Description":d=""
            q=Decimal(self.iqty.get().strip());pr=Decimal(self.iprice.get().strip())
            if not d or q<=0 or pr<0:raise ValueError("Enter a description, positive quantity and valid price.")
            a=q*pr;self.items.append(dict(type=self.it.get(),desc=d,qty=q,price=pr,amount=a))
            self.itt.insert("", "end",values=(self.it.get(),d,q,money(pr),money(a)))
            self.clear_item_editor();self.summary()
        except (ValueError, ArithmeticError):messagebox.showwarning("Item","Enter a description, positive numeric quantity, and valid non-negative price.")

    def select_bill_item(self, event=None):
        selected=self.itt.selection()
        if not selected:
            return
        index=self.itt.index(selected[0])
        item=self.items[index]
        self.editing_item_index=index
        self.it.set(item["type"])
        self.update_catalog_items()
        self.idesc.delete(0,"end");self.idesc.insert(0,item["desc"])
        self.iqty.delete(0,"end");self.iqty.insert(0,str(item["qty"]))
        self.iprice.delete(0,"end");self.iprice.insert(0,str(item["price"]))
        if item["desc"] in BILLING_CATALOG.get(item["type"],{}):
            self.item_name.set(item["desc"])
        else:
            self.item_name.set("Custom item...")
        self.update_item_button.config(state="normal")
        self.remove_item_button.config(state="normal")

    def update_item(self):
        if self.editing_item_index is None:
            return
        try:
            description=self.idesc.get().strip()
            quantity=Decimal(self.iqty.get().strip())
            price=Decimal(self.iprice.get().strip())
            if not description or quantity<=0 or price<0:
                raise ValueError
            item=dict(type=self.it.get(),desc=description,qty=quantity,price=price,amount=quantity*price)
            self.items[self.editing_item_index]=item
            row=self.itt.selection()[0]
            self.itt.item(row,values=(item["type"],item["desc"],item["qty"],money(item["price"]),money(item["amount"])))
            self.clear_item_editor()
            self.summary()
        except (ValueError, ArithmeticError, IndexError):
            messagebox.showwarning("Item","Select an item and enter a description, positive quantity, and valid non-negative price.")

    def clear_item_editor(self):
        self.editing_item_index=None
        self.item_name.set("")
        self.idesc.delete(0,"end")
        self.iqty.delete(0,"end");self.iqty.insert(0,"1")
        self.iprice.delete(0,"end")
        selected=self.itt.selection()
        if selected:
            self.itt.selection_remove(*selected)
        self.update_item_button.config(state="disabled")
        self.remove_item_button.config(state="disabled")

    def remove_item(self,e=None):
        s=self.itt.selection()
        if s:
            index=self.itt.index(s[0])
            self.items.pop(index);self.itt.delete(s[0])
            self.clear_item_editor();self.summary()
    def summary(self):
        total=sum((x["amount"] for x in self.items),Decimal("0"));paid=dec(self.pa.get())
        self.tv.set(money(total));self.pv.set(money(paid));self.rv.set(money(max(total-paid,0)))
        self.payment_status.set("Paid" if total and paid==total else "Partially Paid" if paid else "Pending")
    def load_bill(self,bid):
        r=self.db.q("SELECT * FROM bills WHERE id=%s",(bid,),True)
        if not r:return
        b=r[0]
        for x,pid in self.pmap.items():
            if pid==b["patient_id"]:self.bc.set(x);self.load_patient_details();break
        self.bd.delete(0,"end");self.bd.insert(0,str(b["bill_date"]))
        self.doctor.insert(0,b.get("doctor") or "")
        self.bn.insert(0,b["notes"] or "");self.pa.insert(0,str(b["paid_amount"] or 0))
        for x in self.db.q("SELECT * FROM bill_items WHERE bill_id=%s ORDER BY id",(bid,),True):
            z=dict(type=x["item_type"],desc=x["description"],qty=dec(x["quantity"]),price=dec(x["unit_price"]),amount=dec(x["amount"]));self.items.append(z);self.itt.insert("", "end",values=(z["type"],z["desc"],z["qty"],money(z["price"]),money(z["amount"])))
        self.summary()
    def save_bill(self,pdf=False,bid=None):
        try:
            if not self.items:raise ValueError("Add at least one medicine, test, service, or consultation item.")
            total=sum((x["amount"] for x in self.items),Decimal("0"));paid=dec(self.pa.get())
            if paid<0 or paid>total:raise ValueError("Paid amount must be between 0 and total.")

            if self.patient_mode.get() == "existing":
                patient_key=self.bc.get().strip()
                if patient_key not in self.pmap: raise ValueError("Select an existing patient or switch to manual patient entry.")
                patient_id=self.pmap[patient_key]
            else:
                name=self.patient_fields["name"].get().strip()
                if not name: raise ValueError("Enter patient name for manual billing.")
                age=self.patient_fields["age"].get().strip()
                gender=self.patient_fields["gender"].get().strip()
                phone=self.patient_fields["phone"].get().strip()
                address=self.patient_fields["address"].get().strip()
                existing=self.db.q("SELECT id FROM patients WHERE name=%s AND (phone=%s OR phone IS NULL OR phone='') LIMIT 1",(name, phone or ""),True)
                if existing:
                    patient_id=existing[0]["id"]
                else:
                    patient_id=self.db.q("INSERT INTO patients(name,age,gender,phone,address) VALUES(%s,%s,%s,%s,%s)",(name, int(age) if age else None, gender or "Other", phone or "", address or ""))

            status="Paid" if paid==total and total else ("Partially Paid" if paid else "Pending")
            args=(patient_id,self.bd.get().strip(),self.doctor.get().strip(),total,paid,status,self.bn.get().strip())
            if bid:self.db.q("UPDATE bills SET patient_id=%s,bill_date=%s,doctor=%s,total_amount=%s,paid_amount=%s,payment_status=%s,notes=%s WHERE id=%s",args+(bid,));new=bid;self.db.q("DELETE FROM bill_items WHERE bill_id=%s",(bid,))
            else:new=self.db.q("INSERT INTO bills(patient_id,bill_date,doctor,total_amount,paid_amount,payment_status,notes) VALUES(%s,%s,%s,%s,%s,%s,%s)",args)
            self.db.q("INSERT INTO bill_items(bill_id,item_type,description,quantity,unit_price,amount) VALUES(%s,%s,%s,%s,%s,%s)",
                      [(new,x["type"],x["desc"],x["qty"],x["price"],x["amount"]) for x in self.items],many=True)
            if pdf:self.pdf(new)
            else:messagebox.showinfo("Saved",f"Invoice INV-{new:05d} saved.")
            self.invoices()
        except Exception as e:messagebox.showerror("Billing",str(e))

    def invoices(self):
        self.start("inv","Invoices");s=Scroll(self.content);s.grid(row=0,column=0,sticky="nsew");b=s.i;b.grid_columnconfigure(0,weight=1)
        p=self.panel(b,"Invoice register",0,0);bar=tk.Frame(p,bg=CARD);bar.grid(row=1,column=0,sticky="ew",padx=18,pady=(0,8));bar.grid_columnconfigure(0,weight=1)
        self.isearch=ttk.Entry(bar);self.isearch.grid(row=0,column=0,sticky="ew",padx=5);self.isearch.insert(0,"Search invoice / patient");self.isearch.bind("<FocusIn>",lambda e:self.placeholder(self.isearch,"Search invoice / patient"))
        ttk.Button(bar,text="Search",command=self.refresh_inv).grid(row=0,column=1);ttk.Button(bar,text="+ New Billing",style="Primary.TButton",command=self.billing).grid(row=0,column=2,padx=5)
        self.ivt=self.tree(p,[("id","Invoice",100),("patient","Patient",190),("date","Date",110),("total","Total",120),("paid","Paid",120),("pending","Pending",120),("status","Status",120)])
        self.ivt.bind("<Double-1>",lambda e:self.edit_inv())
        a=tk.Frame(p,bg=CARD);a.grid(row=3,column=0,sticky="e",padx=18,pady=12)
        ttk.Button(a,text="Edit",command=self.edit_inv).pack(side="left",padx=3);ttk.Button(a,text="Generate PDF",command=self.pdf_inv).pack(side="left",padx=3);ttk.Button(a,text="Delete",command=self.del_inv).pack(side="left",padx=3)
        self.refresh_inv()
    def refresh_inv(self):
        if not hasattr(self,"ivt") or not self.ivt.winfo_exists():return
        for x in self.ivt.get_children():self.ivt.delete(x)
        q=self.isearch.get().strip();q="" if q=="Search invoice / patient" else q
        for r in self.db.q("""SELECT b.id,p.name patient,b.bill_date,b.total_amount,b.paid_amount,b.total_amount-b.paid_amount pending,b.payment_status
                              FROM bills b JOIN patients p ON p.id=b.patient_id WHERE p.name LIKE %s OR CAST(b.id AS CHAR) LIKE %s ORDER BY b.id DESC""",(f"%{q}%",f"%{q}%"),True):
            self.ivt.insert("", "end",iid=str(r["id"]),values=(f"INV-{r['id']:05d}",r["patient"],r["bill_date"],money(r["total_amount"]),money(r["paid_amount"]),money(r["pending"]),r["payment_status"]))
    def sel(self):
        x=self.ivt.selection();return int(x[0]) if x else None
    def edit_inv(self):
        if self.sel():self.billing(self.sel())
    def pdf_inv(self):
        if self.sel():self.pdf(self.sel())
    def del_inv(self):
        x=self.sel()
        if x and messagebox.askyesno("Delete","Delete selected invoice?"):self.db.q("DELETE FROM bills WHERE id=%s",(x,));self.refresh_inv()

    def pdf(self,bid):
        r=self.db.q("""SELECT b.*,p.name patient,p.age,p.gender,p.phone FROM bills b JOIN patients p ON p.id=b.patient_id WHERE b.id=%s""",(bid,),True)
        if not r:return
        b=r[0];items=self.db.q("SELECT * FROM bill_items WHERE bill_id=%s ORDER BY id",(bid,),True)
        folder=Path.home()/"MediBill_Invoices";folder.mkdir(exist_ok=True);path=folder/f"Invoice_INV-{bid:05d}.pdf"
        styles=getSampleStyleSheet();doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=36,leftMargin=36,topMargin=36,bottomMargin=36)
        story=[Paragraph("<b>MEDIBILL</b>",styles["Title"]),Paragraph("Hospital Billing & Invoice",styles["Normal"]),Spacer(1,14)]
        info=[[f"Invoice: INV-{bid:05d}",f"Date: {b['bill_date']}"],[f"Patient: {b['patient']}",f"Status: {b['payment_status']}"],[f"Phone: {b['phone'] or '-'}",f"Age/Gender: {b['age'] or '-'} / {b['gender'] or '-'}"],[f"Doctor: {b.get('doctor') or '-'}",""]]
        t=Table(info,colWidths=[280,230]);t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F8FAFC")),("GRID",(0,0),(-1,-1),.4,colors.HexColor("#E4E7EC")),("PADDING",(0,0),(-1,-1),8)]));story += [t,Spacer(1,15)]
        data=[["Type","Description","Qty","Unit Price","Amount"]]+[[x["item_type"],x["description"],str(x["quantity"]),money(x["unit_price"]),money(x["amount"])] for x in items]
        t=Table(data,colWidths=[75,220,55,85,75],repeatRows=1);t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0F172A")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.4,colors.HexColor("#D0D5DD")),("PADDING",(0,0),(-1,-1),7),("ALIGN",(2,1),(-1,-1),"RIGHT")]))
        story += [t,Spacer(1,16)]
        z=Table([["Total Price",money(b["total_amount"])],["Paid Fee",money(b["paid_amount"])],["Pending Fee",money(dec(b["total_amount"])-dec(b["paid_amount"]))]],colWidths=[150,150],hAlign="RIGHT")
        z.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#F8FAFC")),("GRID",(0,0),(-1,-1),.4,colors.HexColor("#E4E7EC")),("FONTNAME",(0,0),(-1,-1),"Helvetica-Bold"),("ALIGN",(1,0),(1,-1),"RIGHT"),("PADDING",(0,0),(-1,-1),8)]));story.append(z)
        doc.build(story);messagebox.showinfo("PDF",f"Invoice saved to:\n{path}")

    def reports(self):
        self.start("report","Reports");s=Scroll(self.content);s.grid(row=0,column=0,sticky="nsew");b=s.i;b.grid_columnconfigure(0,weight=1)
        total=self.db.scalar("SELECT COALESCE(SUM(total_amount),0) FROM bills");paid=self.db.scalar("SELECT COALESCE(SUM(paid_amount),0) FROM bills")
        cards=tk.Frame(b,bg=BG);cards.grid(row=0,column=0,sticky="ew",padx=15)
        self.card(cards,"Revenue Billed",money(total),0,"Gross invoice value");self.card(cards,"Collected",money(paid),1,"Payments received");self.card(cards,"Outstanding",money(dec(total)-dec(paid)),2,"Pending collections");self.card(cards,"Patients",str(self.db.scalar("SELECT COUNT(*) FROM patients")),3,"Registered patients")
        p=self.panel(b,"Monthly billing summary",0,1);t=self.tree(p,[("month","Month",150),("bills","Bills",80),("total","Total",140),("paid","Paid",140),("pending","Pending",140)])
        for r in self.db.q("""SELECT DATE_FORMAT(bill_date,'%Y-%m') month,COUNT(*) bills,SUM(total_amount) total,SUM(paid_amount) paid,SUM(total_amount-paid_amount) pending
                              FROM bills GROUP BY DATE_FORMAT(bill_date,'%Y-%m') ORDER BY month DESC LIMIT 12""",fetch=True):
            t.insert("", "end",values=(r["month"],r["bills"],money(r["total"]),money(r["paid"]),money(r["pending"])))
        ttk.Button(b,text="Export Billing CSV",command=self.export).grid(row=2,column=0,sticky="e",padx=22,pady=12)
    def export(self):
        path=filedialog.asksaveasfilename(defaultextension=".csv",filetypes=[("CSV","*.csv")],initialfile="billing_report.csv")
        if not path:return
        rows=self.db.q("""SELECT b.id,p.name patient,b.bill_date,b.total_amount,b.paid_amount,b.total_amount-b.paid_amount pending,b.payment_status
                          FROM bills b JOIN patients p ON p.id=b.patient_id ORDER BY b.id DESC""",fetch=True)
        with open(path,"w",newline="",encoding="utf-8") as f:
            w=csv.writer(f);w.writerow(["Invoice","Patient","Date","Total","Paid","Pending","Status"])
            for r in rows:w.writerow([f"INV-{r['id']:05d}",r["patient"],r["bill_date"],r["total_amount"],r["paid_amount"],r["pending"],r["payment_status"]])
        messagebox.showinfo("Export",f"CSV exported to:\n{path}")

if __name__=="__main__":
    App().mainloop()
