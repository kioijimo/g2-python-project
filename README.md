# g2-python-project

An equipment and inventory management system built with Django.

---

## Step-by-Step Setup & Execution Order

Follow these steps in order to set up, seed, and run the project locally on Windows (PowerShell):

### Step 1: Create and Activate the Virtual Environment
Create a `.venv` virtual environment in the project root and activate it in PowerShell:

```powershell
python -m venv .venv
.venv/Scripts/Activate.ps1
```
*(If using Command Prompt `cmd.exe` instead of PowerShell, run `.venv\Scripts\activate.bat`)*

### Step 2: Install Python Dependencies
Install Django and all required packages into the active virtual environment:

```powershell
pip install -r requirements.txt
```

### Step 3: Initialize & Install Tailwind (First-time setup)
Initialize and install the Tailwind subapp dependencies if not already installed:

```powershell
python manage.py tailwind init
python manage.py tailwind install
```

### Step 4: Apply Database Migrations
Create and apply the SQLite database schema migrations:

```powershell
python manage.py makemigrations
python manage.py migrate
```

### Step 5: Seed Demonstration Data (Recommended)
Populate the database with the complete demonstration dataset (system settings, 9 user accounts, 4 categories, 8 catalog items, 24 physical equipment units, 20 borrow requests across all lifecycle states, maintenance tickets, and audit logs):

```powershell
.venv\Scripts\python.exe manage.py seed_demo_data --flush
```
> **What `--flush` does**: Safely clears existing records and resets SQLite sequences before inserting fresh demonstration data so IDs and statuses are deterministic.
> *(Alternatively, raw SQL seed data is also available in `seed_demo_data.sql`.)*

### Step 6: Build Tailwind CSS (Optional — only needed after editing template classes)
Compile the standalone Tailwind CSS bundle:

```powershell
python manage.py tailwind build
```

### Step 7: Run the Development Server
Activate the virtual environment and start the local Django development server:

```powershell
.venv/Scripts/Activate.ps1
python manage.py runserver
```
Open **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)** in your browser.

---

## Demo Accounts & Login Credentials

After running `.venv\Scripts\python.exe manage.py seed_demo_data --flush`, all seeded accounts share the following password:

- **Default Password (all demo accounts)**: `DemoPass123!`

| ID | Name | Email | Role |
| :-: | :--- | :--- | :--- |
| 1 | Admin Officer | `admin@example.com` | Administrator |
| 2 | Vonlery Villanueva | `vonlery.villanueva@example.com` | Regular user |
| 3 | Marc Justin Pavia | `marc.pavia@example.com` | Regular user |
| 4 | Lester Perez | `lester.perez@example.com` | Regular user |
| 5 | John Ace Padilla | `john.padilla@example.com` | Regular user |
| 6 | Janver Flores | `janver.flores@example.com` | Regular user |
| 7 | Denzelkeane Aquino | `denzelkeane.aquino@example.com` | Regular user |
| 8 | Rafael Cruz | `rafael.cruz@example.com` | Regular user |
| 9 | Beatrice Mendoza | `beatrice.mendoza@example.com` | Regular user |

---

## Creating or Promoting an Administrator Manually

Only administrators can access `/manage/`. If you are not using the seeded demo data, you can create an administrator from the command line:

```powershell
python manage.py createadmin --email admin@example.com
```

To promote an existing regular user account to administrator:

```powershell
python manage.py createadmin --email user@example.com --promote
```

---

## Running Automated Tests

Run the test suite using the virtual environment's Python executable:

```powershell
.venv\Scripts\python.exe manage.py test
```

---

## Design System & UI Guidelines

This project uses Tailwind CSS v4 Standalone and standardized Django template components (`templates/components/`).
For visual principles, design tokens, component standards, form widget styling, and AI agent rules, see:
- [Design System Documentation](docs/DESIGN_SYSTEM.md)
