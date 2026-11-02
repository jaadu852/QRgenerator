# CloudKrafts QR Manager — Production Edition v19

This package deploys the existing QR Manager on Render (Python web service) with Supabase PostgreSQL. The same app serves the dashboard, vendor activation/management pages, QR redirect URLs, and print-ready PDF generation from one origin: `https://qr.cloudkrafts.in`.

## Preserved features
- Admin login, vendor creation and vendor password management
- QR batch generation and `ck000001`-style IDs
- Vendor activation with shared vendor password and shop name
- Customer QR redirect; destination link can be changed later
- Vendor PIN-based link management
- Admin QR search, status reset to Unused, and link editing
- Batch history and Download / print again
- Four 103 x 103 mm stickers per A4 PDF, no gaps, centered
- Root `logo.png` used as-is; QR overlay retains v18 placement (28% size, 61.3% left, 48.1% top)
- QR IDs below the QR code
- Existing local SQLite data can be migrated to Supabase

## Architecture
- Render Free: Python app and API
- Supabase Free: PostgreSQL database
- Render custom domain: `qr.cloudkrafts.in`
- Existing Shopify store/domain is not changed; only a new `qr` DNS record is added.
- The backend itself serves the frontend. Cloudflare Pages is not needed.

## Before deployment
You need:
1. A GitHub account (private repository recommended).
2. A Render account.
3. A Supabase account.
4. Access to the DNS settings for `cloudkrafts.in`.
5. Your existing `local-data.sqlite3` file if you want to migrate local vendors and QR records.

Never commit `.env`, database passwords, `APP_SECRET`, or `ADMIN_PASSWORD` to GitHub.

## Step 1 — Create Supabase database
1. Create a new Supabase project on the Free plan.
2. Save the database password securely.
3. In Project Settings / Connect, choose the Session pooler connection string (URI) for PostgreSQL.
4. Ensure the URI includes `sslmode=require`. Use the session pooler URI, not the Supabase REST API URL.
5. The app creates its tables automatically on first boot. `schema.sql` is included for reference.

## Step 2 — Upload this project to GitHub
1. Extract this ZIP on your computer.
2. Create a new **private** GitHub repository, for example `cloudkrafts-qr-manager`.
3. Upload the contents of the extracted folder (not the ZIP itself).
4. Confirm `server.py`, `index.html`, `requirements.txt`, `render.yaml`, `logo.png`, and `migrate_sqlite_to_postgres.py` are in the repository root.
5. Do not upload `local-data.sqlite3`. It is excluded by `.gitignore`.

The supplied `logo.png` is included in this package. Replace it only if you intentionally want a different sticker artwork.

## Step 3 — Create the Render service
1. Sign in to Render and choose New > Blueprint.
2. Connect GitHub and select the private repository.
3. Render reads `render.yaml` and creates the free web service.
4. In the Render service Environment page, add these variables:
   - `DATABASE_URL` = Supabase Session pooler URI
   - `ADMIN_PASSWORD` = your own strong, unique password (at least 14 characters)
   - `APP_SECRET` = a random secret of at least 32 characters
   - `PUBLIC_BASE_URL` = `https://qr.cloudkrafts.in`
   - `CK_ENV` = `production` (already declared in render.yaml)
5. Save changes and wait for the deployment to finish.
6. Test the temporary Render URL: open `/healthz`; it should return `{"ok":true,...}`.
7. Open the Render URL root and sign in with your `ADMIN_PASSWORD`.

### Generate a secure APP_SECRET
On Windows PowerShell, run:
```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```
Copy the output and set it as `APP_SECRET` in Render. Keep it in a password manager. **Do not change it after migration**: it encrypts vendor passwords that the admin dashboard can display.

## Step 4 — Connect qr.cloudkrafts.in
1. In Render service Settings > Custom Domains, add `qr.cloudkrafts.in`.
2. Render will show the exact DNS record/target required for your service.
3. Open the DNS settings for `cloudkrafts.in` at the provider that currently manages its DNS.
4. Add only the requested `CNAME` record:
   - Name/Host: `qr`
   - Target/Value: the exact `*.onrender.com` hostname Render displays
5. Do not change the root domain (`@`), Shopify records, MX records, or existing `www` record.
6. Wait for DNS verification and Render TLS certificate issuance.
7. Test `https://qr.cloudkrafts.in/healthz`, then open `https://qr.cloudkrafts.in`.

If Cloudflare manages DNS, set the new `qr` CNAME to **DNS only** during Render domain verification. Do not proxy it until the domain is verified, and DNS-only is the simplest stable setting.

## Step 5 — Migrate your existing local QR records (optional but recommended)
Do this before handing out any live QR stickers. Keep a backup copy of the local SQLite database.

1. Copy `local-data.sqlite3` from your existing local QR Manager folder into the extracted v19 folder temporarily.
2. On Windows PowerShell, set the same database URI and APP_SECRET used in Render:
```powershell
$env:DATABASE_URL = "PASTE_THE_SUPABASE_SESSION_POOLER_URI_HERE"
$env:APP_SECRET = "PASTE_THE_EXACT_APP_SECRET_FROM_RENDER_HERE"
python -m pip install -r requirements.txt
python migrate_sqlite_to_postgres.py .\local-data.sqlite3
```
3. The script stops if the target database already contains vendor/QR records, to avoid accidental duplicates.
4. It copies vendor IDs, QR IDs, statuses, links, PIN hashes, batch history, and audit events. Vendor passwords are encrypted at rest using `APP_SECRET`.
5. Check the vendor list, QR totals, a known QR redirect, and batch reprint in the live dashboard.
6. After successful verification, remove the temporary local database from the project folder. Do not upload it to GitHub.

If you have already created live records before migration, stop and ask for help rather than trying to merge databases manually.

## Step 6 — Production checks
Test each of these using a spare/test QR before selling:
- Admin login with the new password
- Create a test vendor and generate a batch
- Activate one QR with vendor password, shop name, and a valid HTTPS destination
- Scan the QR using a phone on mobile data (not only Wi-Fi)
- Change its destination and scan again
- Search its ID in Admin > Search QR and reset it to Unused
- Download / print again for the test batch
- Open the PDF and confirm 4 stickers, 103 x 103 mm each, then print at A4 / Actual Size (100%)

Do not test by resetting a customer's already-sold QR.

## Free-tier limitations and important reliability notes
- Render Free services may spin down after inactivity. The first request after sleep can be slow while the service wakes up.
- Supabase Free has quotas and project-pause/backup limitations that can change. Check the current Supabase dashboard for your project's database, egress, and pause limits.
- This is a free-tier launch configuration, not a guaranteed always-on SLA. For a commercial QR product, monitor service health and keep a regular database export/backup.
- Free-tier provider limits can change; verify the current plan terms before selling at scale.
- QR stickers depend on `qr.cloudkrafts.in` remaining under your control. Renew the domain and do not rename the subdomain after printing.

## Important security notes
- `ADMIN_PASSWORD` and `APP_SECRET` are production secrets. Never put them in GitHub, screenshots, or customer-facing documents.
- Keep `APP_SECRET` stable and backed up. Losing it means previously encrypted vendor passwords can no longer be displayed (vendor authentication hashes and QR redirects still remain in the database).
- Use HTTPS links for customer destinations wherever possible.
- Use a strong, unique admin password and restrict access to the admin dashboard.
- Take periodic Supabase backups/exports, especially before schema or code updates.

## Local testing
For local testing only, you can still use `start-windows.bat`. Without `DATABASE_URL`, the app uses its local SQLite database. Do not use the local SQLite file as the live production database.
