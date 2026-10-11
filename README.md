# StayCare - Boarding House Management System

A full-featured, responsive web application for managing boarding houses and dormitories. Built with **Python Flask**, **SQLite**, and **HTML5/Vanilla CSS/JavaScript**.

---

## Features

- **Admin Authentication**: Secure login/logout with password hashing (PBKDF2/Werkzeug) and session protection.
- **Interactive Overview Dashboard**:
  - Live metric cards: Total Rooms, Active Tenants, Occupancy Rate (%), and Rental Revenue (₱).
  - Quick operations shortcuts.
  - Recent payment transactions and pending maintenance tickets.
- **Room Management**:
  - Add, edit, and delete rooms.
  - Configurable room capacity, monthly rental rate (₱), and amenities description.
  - Live occupancy progress bars showing remaining available bed slots.
  - Safe deletion protection (prevents deleting rooms with active tenants).
- **Tenant Management**:
  - Tenant registration with contact details and emergency contact.
  - Smart room assignment with real-time room capacity check (prevents overbooking).
  - Comprehensive tenant profile with payment history and check-out (free room slot) action.
- **Rent Payment Tracking**:
  - Record rent collections with auto-filled rental rates.
  - Multiple payment methods: Cash, GCash, Bank Transfer, Other.
  - Track statuses: Fully Paid, Partial, and Overdue.
  - Printable official payment receipts with formatted receipt numbers (`#RCP-0001`).
- **Maintenance Request System**:
  - File repair tickets for rooms and tenants with urgency priority (Low, Medium, High, Urgent).
  - Track ticket status (Pending, In Progress, Resolved) and repair costs.
- **Comprehensive Reports**:
  - Detailed room occupancy breakdown.
  - Tenant directory and rental status report.
  - Financial collection reports (Cash vs GCash/online breakdown).
  - Print-friendly layout (`Ctrl + P` / Print button).
- **Timezone**: All dates and transaction timestamps use `Asia/Manila` time.

---

## Technology Stack

- **Backend**: Python 3.9+ & Flask
- **Database**: SQLite (SQLAlchemy ORM)
- **Frontend**: Responsive HTML5, Vanilla CSS (Design system, CSS variables), and JavaScript
- **Version Control**: Git

---

## Project Structure

```text
Boarding House Management System/
│
├── app.py                     # Main application routes and business logic
├── config.py                  # Application configuration & database settings
├── models.py                  # Database schemas with Asia/Manila timezone
├── requirements.txt           # Python dependencies
├── .gitignore                 # Excludes venv, cache, and local database
├── README.md                  # Project documentation & guide
│
├── static/
│   ├── css/
│   │   └── style.css          # Modern responsive design system
│   └── js/
│       └── main.js            # Mobile navigation, alerts, UI interactions
│
└── templates/
    ├── base.html              # Responsive layout template with navigation
    ├── login.html             # Admin login page
    ├── dashboard.html         # Overview dashboard
    ├── rooms/
    │   ├── index.html         # Room catalog & occupancy cards
    │   ├── form.html          # Add / Edit room
    │   └── view.html          # Room profile, active occupants & repair history
    ├── tenants/
    │   ├── index.html         # Tenant directory
    │   ├── form.html          # Register / Edit tenant
    │   └── view.html          # Tenant profile & payment history
    ├── payments/
    │   ├── index.html         # Payment logs & financial totals
    │   ├── form.html          # Record & edit payments
    │   └── receipt.html       # Official printable receipt
    ├── maintenance/
    │   ├── index.html         # Maintenance tickets & status update
    │   └── form.html          # File & edit repair requests
    └── reports/
        └── index.html         # Printable management reports
```

---

## How to Run Locally

### 1. Install Dependencies (First time only)
Open PowerShell or Command Prompt in the project folder and run:
```bash
py -m pip install -r requirements.txt
```
*(or `python -m pip install -r requirements.txt`)*

### 2. Start the Application
Run:
```bash
py app.py
```
*(or `python app.py`)*

### 3. Open in Your Web Browser
Open your browser and navigate to:
```text
http://127.0.0.1:5000
```

### Default Administrator Credentials
* **Username:** `admin`
* **Password:** `admin123`

---

## Pushing to GitHub

To upload this repository to your GitHub account:

1. Create a new empty repository on [GitHub](https://github.com).
2. Run the following commands in PowerShell inside your project folder:
   ```bash
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   git branch -M main
   git push -u origin main
   ```

---

## Deploying Online

You can easily deploy this Flask app for free or low cost on:
- **Render.com**: Connect your GitHub repository, choose **Web Service**, set Build Command to `pip install -r requirements.txt`, and Start Command to `python app.py` (or `gunicorn app:app`).
- **PythonAnywhere**: Upload or clone from GitHub and configure the Web tab using Python 3.9+.
