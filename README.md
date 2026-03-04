# School Event Portal

Mobile-first web app for event registration. Students see the active event on the dashboard, enter their roll no to register; new users create a one-time profile, then confirm registration with optional extra amount.

## Setup

1. Create a virtual environment and install dependencies:

   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Ensure MySQL is running with database `school_event` and tables: `students`, `batches`, `events`, `event_registrations`, `payments`. Have at least one active event (`is_active = 1`) and batches for the profile form.

3. If you use site maintenance donation, add the column (once):  
   `ALTER TABLE event_registrations ADD COLUMN site_fee INT DEFAULT 0 AFTER extra_amount;`  
   For bKash TXN ID:  
   `ALTER TABLE event_registrations ADD COLUMN txn_no VARCHAR(100) DEFAULT NULL AFTER total_amount;`  
   For registration photo:  
   `ALTER TABLE event_registrations ADD COLUMN photo VARCHAR(255) DEFAULT NULL AFTER txn_no;`  
   For student profile photo (Create Profile):  
   `ALTER TABLE students ADD COLUMN photo VARCHAR(255) DEFAULT NULL AFTER blood_group;`

4. Edit `config.py` if your DB host/user/password differ (and `SITE_FEE` for the donation amount, default 20).

## Run

```bash
python app.py
```

Open http://127.0.0.1:5000 in a browser (or your phone on the same network).

## Routes

| Interface | Route | Purpose |
|-----------|--------|---------|
| **User** | `/` | Dashboard, register for events |
| **User** | `/register`, `/profile/create`, `/event/<id>/register`, `/success` | Registration flow |
| **Admin** | `/admin` | Dashboard: create events, view registrations |
| **Admin** | `/admin/login` | Password login (required for all /admin pages) |
| **Admin** | `/admin/create-event` | Form to add new event |
| **Admin** | `/admin/students` | View all student profiles |
| **Admin** | `/admin/students/<id>/edit` | Edit one student |
| **Admin** | `/admin/registrations` | View registrations (filter by event) |

Admin is protected by a single password. Set `ADMIN_PASSWORD` in `config.py` (default `admin123`).

## Flow

1. **Dashboard** – One active event card, [REGISTER].
2. **Enter Roll No** – Student ID to check if profile exists.
3. **Create Profile** (if new) – Student ID, name, email, phone, batch → Save & Continue.
4. **Event Registration** – Read-only details, base fee, optional extra amount, total (auto), [CONFIRM REGISTRATION].
5. **Success** – Total amount and “Pay at school office”, [BACK TO DASHBOARD].

## UX

- One column, cards (no tables), font ≥16px, big buttons, minimal scrolling.

---

## Production deployment

1. **Set environment variables** (do not rely on defaults):

   - `SECRET_KEY` – long random string (e.g. `openssl rand -hex 32`)
   - `ADMIN_PASSWORD` – strong admin password
   - `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` – MySQL credentials
   - `FLASK_ENV=production` – disables debug and enables secure cookies

   Optional: `SCHOOL_NAME`, `PORT`, `SITE_FEE`, `DEFAULT_BATCH_NAME`.  
   See `.env.example` for a full list.

2. **Run with Gunicorn** (Linux):

   ```bash
   pip install -r requirements.txt
   gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
   ```

   Use `PORT` or a reverse proxy (e.g. Nginx) to bind to 80/443. Serve static files via Nginx if desired.

3. **HTTPS**: Use a reverse proxy (Nginx, Caddy) with SSL (e.g. Let’s Encrypt). The app sets `SESSION_COOKIE_SECURE=True` when `FLASK_ENV` is not `development`.

4. **Windows server**: Use Waitress instead of Gunicorn:  
   `pip install waitress` then  
   `waitress-serve --port=5000 wsgi:app`
