CloudKrafts QR Manager v16

Fixes:
1. Print A4 stickers now downloads a backend-generated PDF instead of relying on Chrome's print renderer.
2. The PDF embeds root logo.png directly at original source resolution (lossless PNG), with QR PNG overlay and ID.
3. Batch history "Download / print again" now works by retrieving all QR IDs for that exact batch and generating its PDF.
4. PDF route marks the batch as downloaded only after successful PDF creation.
5. Startup checks/installs reportlab alongside qrcode and Pillow.

Setup:
- Keep logo.png in the same root folder as server.py and start-windows.bat.
- Keep existing local-data.sqlite3 when upgrading.
- Run start-windows.bat.
- Generate a batch, then click Print A4 stickers to download the PDF.
- Use Download / print again on any batch history row to regenerate that batch's PDF.

Print:
- PDF page: A4 portrait.
- Four stickers per page, each 103 x 103 mm, 2x2, zero gaps, centered.
- Print PDF using Actual Size / 100%; disable Fit/Shrink.
- PDF is generated from the original PNG source; browser print preview is bypassed.
