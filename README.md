# 🤖 Uzeron AdsBot — Free Tier

Automated Telegram promotional message bot. Logs into the user's Telegram account via OTP and broadcasts their ad message across all joined groups — automatically.

---

## 📁 File Structure

```
├── free_bot.py       → Main bot (dashboard, login, campaigns)
├── logger_bot.py     → Logger bot (receives activity logs)
├── requirements.txt  → Python dependencies
├── Dockerfile        → Container config for Railway
├── env.txt           → Environment variables template
└── README.md         → This file
```

---

## ⚙️ Environment Variables

Copy `env.txt` and fill in your values:

| Variable | Description |
|---|---|
| `API_ID` | Server-side API ID from [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | Server-side API Hash from [my.telegram.org](https://my.telegram.org) |
| `FREE_BOT_TOKEN` | Bot token from @BotFather |
| `LOGGER_BOT_TOKEN` | Second bot token from @BotFather (for logs) |
| `ADMIN_IDS` | Your Telegram user ID (comma-separated for multiple) |
| `DATABASE_URL` | PostgreSQL connection string from Neon.tech |
| `BOT_SESSION_STRING` | Auto-generated on first run — save it back to Railway |

> **Note:** Users never see or enter `API_ID` / `API_HASH`. These live on your server only.

---

## 🔑 Login Flow (How Users Connect Their Account)

The bot uses a **server-side Telegram API key** — users authenticate with just their phone number and OTP. No developer credentials required from the user.

**Step 1 — Phone Number**
User sends their phone number with country code (e.g. `+917239879045`)

**Step 2 — OTP via Inline Keypad**
Bot renders a numeric keypad as inline buttons. User taps digits to enter the OTP received on their Telegram app, then taps ✅ Submit. No typing required.

**Step 3 — 2FA Password (if enabled)**
If the account has Two-Factor Authentication, the bot prompts the user to type their 2FA password as a message.

**Step 4 — Done**
Session is saved server-side. The bot automatically adds the required branding to the user's last name. User never needs to log in again.

---

## 🤖 Bot Commands

### Admin Commands

| Command | Description |
|---|---|
| `/ban USER_ID` | Ban a user from the free tier |
| `/users` | List all active free users |
| `/stats` | Show total users and running campaigns |

### User Commands

| Command | Description |
|---|---|
| `/start` | Open the dashboard |
| `/cancel` | Cancel any active input flow |

All other actions (login, set message, start/stop campaign, upgrade) are done via **inline buttons** on the dashboard — no commands needed.

---

## 📊 Free Tier Limits

| Feature | Free |
|---|---|
| Max Groups | 100 |
| Message Delay | 60 seconds (fixed) |
| Cycle Delay | 10 minutes (fixed) |
| Daily Runtime | 8 hours |
| Account Branding | Required (`• via @Uzeron_AdsBot` in last name) |
| Message Rotation | ❌ |
| Auto Schedule | ❌ |

---

## 🚀 Deploy on Railway (Recommended)

### Step 1 — Upload to GitHub

1. Go to [github.com](https://github.com) → **New Repository**
2. Name it `uzeron-adsbot` → set to **Private** → click **Create**
3. Upload all files by drag-and-drop

### Step 2 — Deploy on Railway

1. Go to [railway.app](https://railway.app)
2. Click **Login with GitHub** (no credit card needed)
3. Click **New Project** → **Deploy from GitHub repo**
4. Select your repository

### Step 3 — Add Environment Variables

In Railway → your project → **Variables** tab, add:

```
API_ID          = your_value
API_HASH        = your_value
FREE_BOT_TOKEN  = your_value
LOGGER_BOT_TOKEN= your_value
ADMIN_IDS       = your_telegram_user_id
DATABASE_URL    = your_neon_postgres_url
```

### Step 4 — First Run & Session String

1. Click **Deploy** and wait ~1 minute
2. Open **Logs** — you'll see a long string printed between the `===` lines
3. Copy that string and add it as:
   ```
   BOT_SESSION_STRING = paste_here
   ```
4. Railway will auto-redeploy. Bot is now live 24/7 ✅

---

## 🗄️ Database Setup (Neon.tech — Free)

1. Go to [neon.tech](https://neon.tech) → **Sign Up** (no credit card)
2. Create a new project → copy the **Connection String**
3. Paste it as `DATABASE_URL` in Railway
4. The bot creates its table automatically on first start — nothing else needed

---

## 🔧 Before You Start

### Get Your Telegram User ID (ADMIN_IDS)
1. Open Telegram → search `@userinfobot`
2. Send `/start` → it shows your numeric User ID
3. Use that number as `ADMIN_IDS`

### Create 2 Bots on BotFather
1. Open Telegram → search `@BotFather`
2. Send `/newbot` → follow the steps → copy the token → this is `FREE_BOT_TOKEN`
3. Send `/newbot` again → copy the new token → this is `LOGGER_BOT_TOKEN`

### Get API ID & API Hash
1. Go to [my.telegram.org](https://my.telegram.org) → log in
2. Click **API development tools**
3. Create an app → copy `App api_id` and `App api_hash`

---

## 💎 Premium Upgrade

Users who want unlimited groups, custom delays, no branding, and 24/7 runtime are directed to:

- **Contact:** [@Pandaysubscription](https://t.me/Pandaysubscription)
- **Premium Bot:** [@Uzeron_AdsBot](https://t.me/Uzeron_AdsBot)

Premium activation is handled manually by the admin — no in-bot payment processing.

---

## 🔗 Community Links

| Name | Link |
|---|---|
| Updates Channel | [t.me/Uzeron_AdsBot](https://t.me/Uzeron_AdsBot) |
| Community Group | [t.me/UzeronCommunity](https://t.me/UzeronCommunity) |
| How To Use | [t.me/Uzeron_Ads](https://t.me/Uzeron_Ads) |
| Premium Contact | [t.me/Pandaysubscription](https://t.me/Pandaysubscription) |

---

## ⚠️ Important Notes

- Never share your `env.txt`, session files, or `API_ID`/`API_HASH` publicly
- Users are required to keep the branding in their last name — 3 removals = ban from free tier
- Respect Telegram's rate limits — the 60s delay is enforced to reduce flood risk
- The bot uses polling mode (not webhooks) for Railway free tier compatibility
