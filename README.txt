CLOUDKRAFTS QR MANAGER — LOCAL TEST EDITION

START ON WINDOWS
1. Install Python 3 from https://www.python.org/downloads/ and enable "Add Python to PATH".
2. Extract the complete ZIP into a normal folder (do not run from inside the ZIP preview).
3. Double-click start-windows.bat.
4. A black server window should remain open. Do not close it while testing.
5. Your browser opens at http://127.0.0.1:8765. If it does not, open that address manually.
6. Demo admin password: Admin@12345

IF THE WINDOW CLOSES
- Right-click start-windows.bat and choose Edit, or open Command Prompt in this folder.
- Run: py -3 server.py
- If 'py' is not recognized, run: python server.py
- Keep the error text visible and send a screenshot to ChatGPT.
- Ensure Python 3 is installed and the option "Add Python to PATH" was enabled.

FIRST TEST
1. Sign in with Admin@12345.
2. Create a vendor, e.g. Vendor A, with shared password Vendor@2026 (minimum 8 characters).
3. Generate two QR codes.
4. Open Activate, enter ck000001, vendor password, shop name, URL (e.g. https://example.com), and a 6–12 digit owner PIN.
5. Test redirect at http://127.0.0.1:8765/r/ck000001.
6. Open Manage, enter QR ID and owner PIN, change the URL, and test redirect again.

DATA
The local database is saved in local-data.sqlite3 in this folder. Keep this file to retain test records. Back it up before moving or deleting the folder.

IMPORTANT
This is a local test only. QR codes generated here contain localhost addresses and will NOT work on customers' phones or worldwide. Do not print local QR codes for sale. Production QR codes must use your public domain after deployment. This test build does not include production-grade rate limiting or authentication hardening.

DEPENDENCIES
The application uses Python's standard library plus qrcode/Pillow. The launcher attempts to install qrcode[pil] automatically. An internet connection is needed for that first installation if the library is not already installed.
