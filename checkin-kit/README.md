# Check-in kit

A static site with no server, plus a Google Sheet as the database.

- `/`: **Check-in Pass Studio**. Fill in the guest, then download a branded PDF pass with a QR code.
- `/checkin/`: **Check-in Desk**. Scan the QR code (or type the code) to see the booking and confirm the check-in. Each code works once.
- `apps-script/Code.gs`: the Google Sheet backend.

## Setup (once)
1. Create a Google Sheet, then open **Extensions › Apps Script**. Paste `apps-script/Code.gs`.
2. Change `API_KEY` to a long random string and `STAFF_PIN` to your staff PIN.
3. Run `setup`, then go to **Deploy › New deployment › Web app**. Set *Execute as* to **Me** and *Who has access* to **Anyone**. Copy the `/exec` URL.
4. In the Studio, open **Google Sheet connection** and paste the `/exec` URL and the API key. They are remembered on that computer.

The QR code carries the sheet address, so the desk needs no setup. A phone camera opens the desk with the booking already loaded. Staff enter their name and the PIN to confirm.

If you edit `Code.gs` later, use **Deploy › Manage deployments › Edit › New version** so the URL stays the same.
