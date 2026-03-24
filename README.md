# Inditech HR

Inditech HR is a Django application for managing employee, intern, consultant, and freelancer records, contracts, holidays, approved leaves, attendance submissions, and month-end payroll generation.

## Features

- Google-authenticated login flow using `django-allauth`
- System-admin-controlled HR manager and finance manager role assignments
- Master employee records with monthly compensation, leave policy, contract dates, and current contract file
- Finance workflows for yearly and ad hoc holidays plus approved leave entry
- Daily attendance submission for authenticated employees with one submission per day
- Payroll generation for completed months with leave-without-pay calculation
- MySQL-ready configuration for AWS EC2 deployment, plus SQLite fallback for tests

## Local development

1. Create a virtual environment if needed:

   ```bash
   ../RFA-copy/.venv/bin/python3.11 -m venv .venv311
   ```

2. Install dependencies:

   ```bash
   .venv311/bin/pip install -r requirements.txt
   ```

3. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

4. Start MySQL locally with Docker when Docker Desktop is running:

   ```bash
   docker compose up -d db
   ```

5. Run migrations:

   ```bash
   .venv311/bin/python manage.py migrate
   ```

6. Start the application:

   ```bash
   .venv311/bin/python manage.py runserver
   ```

For test-only workflows you can force SQLite:

```bash
USE_SQLITE=1 .venv311/bin/python manage.py test
```

## Google auth setup

Create a Google OAuth application and place the client values in `.env`:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

Set the authorized redirect URI to:

```text
http://127.0.0.1:8000/accounts/google/login/callback/
```

For deployment, add the production domain callback as well.

## Roles

- System admin email defaults to `gopala.krishnan@inditech.co.in`
- HR manager and finance manager emails are managed inside the application
- Employee access is derived from matching the authenticated Google email to `Employee.work_email`

## Payroll rules implemented

- Working days are Monday through Saturday
- Holidays are excluded from working days
- Attendance is limited to the current day only
- Missing attendance on a working day without approved leave is treated as leave without pay
- Approved leave beyond the monthly cap or annual allowance is treated as leave without pay
- Leave without pay deduction uses monthly compensation divided by the number of calendar days in the month
- Payroll generation is blocked until the selected month has completed

## Deployment target 1

The application is configured for Django + MySQL and is suitable for deployment on AWS EC2 behind a standard reverse proxy such as Nginx.
