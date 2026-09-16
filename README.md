# ItzDalxm's vouches

A tiny local website with two pages:

- **`/`** — the public page. Visitors see five tabs: Gambling, SMP vouches, Other, Schematics, Videos.
- **`/admin`** — a password-gated page where you add/delete vouches, upload schematics, and add YouTube videos. Only you can reach this, and only if you know the passphrase.

Everything is saved to `vouches.json` (schematic files themselves live in `uploads/schematics/`), so it all persists across restarts.

**Schematics tab** — upload `.schem`, `.schematic`, `.litematic`, or `.nbt` files (25MB max) with an optional description. Visitors see a download button for each one.

**Videos tab** — paste any YouTube link (watch, youtu.be, or shorts URLs all work) plus a title, and it shows up as an embedded, playable video on the public page.

## Setup

1. Install Flask (only dependency):
   ```
   pip install flask
   ```

2. Open `app.py` and change these two lines near the top to your own values:
   ```python
   app.secret_key = "change-this-secret-key-to-something-random"
   ADMIN_PASSWORD = "changeme"
   ```

3. Run it:
   ```
   python app.py
   ```

4. Visit:
   - Public page: http://localhost:5000
   - Admin page: http://localhost:5000/admin

## Notes

- This is meant for local/personal use. If you ever put this on the public internet, use a real random `secret_key`, a stronger passphrase, and serve it over HTTPS — the current login is fine for a locally-run tool but isn't hardened for public hosting.
- To add a vouch: log in at `/admin`, pick a category, write the text, optionally add who it's from, and post. It shows up instantly on both the admin list and the public page.
- To remove one, click **Delete** next to it on the admin page.
