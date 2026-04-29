# -*- coding: utf-8 -*-
"""
Uzeron AdsBot — Free Tier  (clean rewrite)
"""

import os, sys, asyncio, psycopg2, json, pytz, requests
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from dotenv import load_dotenv

load_dotenv()

# ── ENV ────────────────────────────────────────────────────────────────────────
DATABASE_URL     = os.getenv('DATABASE_URL')
BOT_API_ID       = int(os.getenv('API_ID'))
BOT_API_HASH     = os.getenv('API_HASH')
FREE_BOT_TOKEN   = os.getenv('FREE_BOT_TOKEN')
LOGGER_BOT_TOKEN = os.getenv('LOGGER_BOT_TOKEN')
ADMINS           = [int(x) for x in os.getenv('ADMIN_IDS','').split(',') if x.strip()]

# ── LINKS ──────────────────────────────────────────────────────────────────────
CONTACT_USERNAME = "@Pandaysubscription"
PREMIUM_BOT      = "@Uzeron_AdsBot"
SUPPORT_LINK     = "https://t.me/Uzeron_Ads_support"

FORCE_JOIN_CHANNEL = "@UzeronAdsBot"          # bot must be admin here
CHANNEL_LINK       = "https://t.me/Uzeron_AdsBot"
CHANNEL_NAME       = "Uzeron"
COMMUNITY_LINK     = "https://t.me/UzeronCommunity"
COMMUNITY_NAME     = "Uzeron Community"
HOW_TO_USE_LINK    = "https://t.me/Uzeron_Ads"
HOW_TO_USE_NAME    = "@Uzeron_Ads"

IST = pytz.timezone('Asia/Kolkata')

# ── FREE TIER CONSTANTS ────────────────────────────────────────────────────────
FREE_MAX_GROUPS          = 100
FREE_CYCLE_DELAY         = 600
FREE_MSG_DELAY           = 60
FREE_MAX_RUNTIME         = 8 * 3600
FREE_BRANDING_LASTNAME   = "• via @Uzeron_AdsBot"
FREE_BRANDING_BIO        = "🚀 Free Ads via @Uzeron_AdsBot | Upgrade: @Pandaysubscription"
FREE_WARNINGS_BEFORE_BAN = 3

# ── BOT API HELPERS (sync, for use outside async context) ─────────────────────
def _tg(method: str, **kwargs) -> dict:
    url = f"https://api.telegram.org/bot{FREE_BOT_TOKEN}/{method}"
    try:
        data = {k: json.dumps(v) if isinstance(v,(dict,list)) else v
                for k,v in kwargs.items()}
        return requests.post(url, data=data, timeout=10).json()
    except Exception as e:
        print(f"[tg:{method}] {e}")
        return {}

def send_msg(chat_id, text, keyboard=None):
    kw = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if keyboard: kw["reply_markup"] = keyboard
    _tg("sendMessage", **kw)

def edit_msg(chat_id, msg_id, text, keyboard=None):
    kw = {"chat_id": chat_id, "message_id": msg_id,
          "text": text, "parse_mode": "HTML"}
    if keyboard: kw["reply_markup"] = keyboard
    _tg("editMessageText", **kw)

def check_joined_sync(uid: int) -> bool:
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{FREE_BOT_TOKEN}/getChatMember",
            params={"chat_id": FORCE_JOIN_CHANNEL, "user_id": uid}, timeout=6
        ).json()
        return r.get("result",{}).get("status","") in ("member","administrator","creator","restricted")
    except Exception as e:
        print(f"[check_joined] {e}")
        return True  # fail-open

# ── KEYBOARDS (return JSON string, ready to send) ─────────────────────────────
def kb(rows): return json.dumps({"inline_keyboard": rows})

def kb_force_join(): return kb([
    [{"text": f"📢 Join {CHANNEL_NAME}",   "url": CHANNEL_LINK}],
    [{"text": f"👥 Join {COMMUNITY_NAME}", "url": COMMUNITY_LINK}],
    [{"text": "✅  I've Joined — Continue","callback_data": "check_join"}],
])

def kb_dashboard(): return kb([
    [{"text":"👤 My Account",      "callback_data":"account"},
     {"text":"📊 Status",         "callback_data":"status"}],
    [{"text":"✍️ Set Ad Message",  "callback_data":"setmessage"},
     {"text":"⏱ 60s │ 🔄 10m",   "callback_data":"delay_info"}],
    [{"text":"🚀 Start Campaign",  "callback_data":"startcampaign"},
     {"text":"🛑 Stop Campaign",   "callback_data":"stopcampaign"}],
    [{"text":"🔑 Login",           "callback_data":"login"},
     {"text":"💎 Go Premium",      "callback_data":"upgrade"}],
    [{"text":f"📢 {CHANNEL_NAME}","url":CHANNEL_LINK},
     {"text":"📖 How To Use",     "url":HOW_TO_USE_LINK}],
    [{"text":"🚪 Logout",          "callback_data":"logout"}],
])

def kb_back(): return kb([[{"text":"🏠 Back to Dashboard","callback_data":"dashboard"}]])

def kb_upgrade(): return kb([
    [{"text":f"💎 Upgrade — {CONTACT_USERNAME}","url":"https://t.me/Pandaysubscription"}],
    [{"text":"📢 Support","url":SUPPORT_LINK},
     {"text":"📖 How To Use","url":HOW_TO_USE_LINK}],
    [{"text":"🔙 Back","callback_data":"dashboard"}],
])

def kb_otp(digits: str): return kb([
    [{"text":f"🔢  {digits or '_ _ _ _ _'}","callback_data":"otp_noop"}],
    [{"text":"1","callback_data":"otp_1"},{"text":"2","callback_data":"otp_2"},{"text":"3","callback_data":"otp_3"}],
    [{"text":"4","callback_data":"otp_4"},{"text":"5","callback_data":"otp_5"},{"text":"6","callback_data":"otp_6"}],
    [{"text":"7","callback_data":"otp_7"},{"text":"8","callback_data":"otp_8"},{"text":"9","callback_data":"otp_9"}],
    [{"text":"⌫ Del","callback_data":"otp_back"},
     {"text":"0","callback_data":"otp_0"},
     {"text":"✅ Submit","callback_data":"otp_submit"}],
    [{"text":"❌ Cancel","callback_data":"cancel_login"}],
])

def kb_cancel(): return kb([[{"text":"❌ Cancel","callback_data":"cancel_login"}]])

# ── MESSAGE TEMPLATES ──────────────────────────────────────────────────────────
def txt_force_join(): return (
    "👋 <b>Welcome to Uzeron AdsBot!</b>\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "📢 <b>Join our channels to continue:</b>\n\n"
    f"  • <b>{CHANNEL_NAME}</b> — updates & announcements\n"
    f"  • <b>{COMMUNITY_NAME}</b> — tips & community\n\n"
    "1️⃣  Tap the <b>Join</b> buttons below\n"
    "2️⃣  Come back and tap <b>I've Joined</b>\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━"
)

def txt_dashboard(user, rt):
    phone  = f"<code>{user[1]}</code>" if user and user[1] else "❌  Not connected"
    msg_st = "✅  Set & Ready" if user and user[5] else "❌  Not set"
    camp   = "🟢  Running"    if user and user[6] else "🔴  Stopped"
    h_used = rt / 3600
    h_left = max(0.0, 8.0 - h_used)
    filled = min(10, int(h_used / 8 * 10))
    bar    = "█"*filled + "░"*(10-filled)
    return (
        "⚡ <b>UZERON ADSBOT  •  Free Plan</b>\n"
        "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
        f"📱  <b>Account</b>     {phone}\n"
        f"✉️   <b>Ad Message</b>  {msg_st}\n"
        f"⏱   <b>Delay</b>      60s  │  🔄 10m cycle\n"
        f"📡  <b>Campaign</b>   {camp}\n\n"
        f"⏳  <b>Runtime Today</b>\n"
        f"     [{bar}]  {h_used:.1f}h / 8h\n"
        f"     🕐 Time Left: <b>{h_left:.1f}h</b>\n\n"
        "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n"
        "⚠️  <i>Free Plan: 100 groups max · 8hr/day</i>"
    )

def txt_upgrade(): return (
    "💎 <b>UPGRADE TO PREMIUM</b>\n\n"
    "Unlock the full power of Uzeron!\n\n"
    "╔══════════════════════╗\n"
    "║  🚀  Unlimited Groups\n"
    "║  ⏱   Custom Delays (30/45/60s)\n"
    "║  🔀  Message Rotation (3 msgs)\n"
    "║  ⏰  Auto Schedule (IST)\n"
    "║  🏷   No Account Branding\n"
    "║  📊  Campaign Analytics\n"
    "║  🛡   24/7 Priority Support\n"
    "╚══════════════════════╝\n\n"
    "📦 <b>Plans:</b>\n"
    "  🥉  Starter — 7 Days\n"
    "  🥈  Growth  — 15 Days\n"
    "  🥇  Pro     — 30 Days\n\n"
    f"👤  Contact: <b>{CONTACT_USERNAME}</b>\n"
    f"🤖  Premium Bot: <b>{PREMIUM_BOT}</b>"
)

# ── DATABASE ───────────────────────────────────────────────────────────────────
class Database:
    def get_conn(self):
        return psycopg2.connect(DATABASE_URL, sslmode='require')

    def init_db(self):
        with self.get_conn() as conn:
            conn.cursor().execute('''
                CREATE TABLE IF NOT EXISTS free_users (
                    user_id BIGINT PRIMARY KEY, username TEXT,
                    phone TEXT, api_id INTEGER, api_hash TEXT, session_string TEXT,
                    promo_message TEXT, is_active INTEGER DEFAULT 0,
                    runtime_today INTEGER DEFAULT 0, last_reset TEXT,
                    warning_count INTEGER DEFAULT 0, is_banned INTEGER DEFAULT 0,
                    branding_set INTEGER DEFAULT 0, created_at TEXT
                )''')
            conn.commit()

    # indices: 0=uid 1=phone 2=api_id 3=api_hash 4=session 5=promo
    #          6=is_active 7=runtime 8=last_reset 9=warnings 10=banned 11=branding

    def get_user(self, uid):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('''SELECT user_id,phone,api_id,api_hash,session_string,
                                promo_message,is_active,runtime_today,last_reset,
                                warning_count,is_banned,branding_set
                         FROM free_users WHERE user_id=%s''',(uid,))
            return c.fetchone()

    def register_user(self, uid, username):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('SELECT 1 FROM free_users WHERE user_id=%s',(uid,))
            if not c.fetchone():
                c.execute('INSERT INTO free_users(user_id,username,created_at) VALUES(%s,%s,%s)',
                          (uid, username, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()

    def is_banned(self, uid):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('SELECT is_banned FROM free_users WHERE user_id=%s',(uid,))
            r = c.fetchone(); return bool(r and r[0])

    def save_session(self, uid, phone, session):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('UPDATE free_users SET phone=%s,api_id=%s,api_hash=%s,session_string=%s WHERE user_id=%s',
                      (phone, BOT_API_ID, BOT_API_HASH, session, uid))
            conn.commit()

    def set_promo(self, uid, msg):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('UPDATE free_users SET promo_message=%s WHERE user_id=%s',(msg,uid))
            conn.commit()

    def set_active(self, uid, v):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('UPDATE free_users SET is_active=%s WHERE user_id=%s',(v,uid))
            conn.commit()

    def get_runtime(self, uid):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('SELECT runtime_today,last_reset FROM free_users WHERE user_id=%s',(uid,))
            row = c.fetchone()
        if not row: return 0
        rt, lr = row
        today = datetime.now(IST).strftime('%Y-%m-%d')
        if lr != today:
            with self.get_conn() as conn:
                c = conn.cursor()
                c.execute('UPDATE free_users SET runtime_today=0,last_reset=%s WHERE user_id=%s',(today,uid))
                conn.commit()
            return 0
        return int(rt or 0)

    def add_runtime(self, uid, secs):
        today = datetime.now(IST).strftime('%Y-%m-%d')
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('UPDATE free_users SET runtime_today=COALESCE(runtime_today,0)+%s,last_reset=%s WHERE user_id=%s',
                      (secs, today, uid))
            conn.commit()

    def set_branding(self, uid, v):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('UPDATE free_users SET branding_set=%s WHERE user_id=%s',(v,uid))
            conn.commit()

    def add_warning(self, uid):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('UPDATE free_users SET warning_count=COALESCE(warning_count,0)+1 WHERE user_id=%s',(uid,))
            c.execute('SELECT warning_count FROM free_users WHERE user_id=%s',(uid,))
            n = c.fetchone()[0]
            if n >= FREE_WARNINGS_BEFORE_BAN:
                c.execute('UPDATE free_users SET is_banned=1 WHERE user_id=%s',(uid,))
            conn.commit()
        return n

    def ban_user(self, uid):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('UPDATE free_users SET is_banned=1 WHERE user_id=%s',(uid,))
            conn.commit()

    def logout_user(self, uid):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('UPDATE free_users SET phone=NULL,api_id=NULL,api_hash=NULL,'
                      'session_string=NULL,is_active=0,branding_set=0 WHERE user_id=%s',(uid,))
            conn.commit()

    def all_users(self):
        with self.get_conn() as conn:
            c = conn.cursor()
            c.execute('SELECT user_id,username FROM free_users WHERE is_banned=0')
            return c.fetchall()

# ── LOGGER ─────────────────────────────────────────────────────────────────────
class Logger:
    _url = f"https://api.telegram.org/bot{LOGGER_BOT_TOKEN}/sendMessage"
    def log(self, uid, text):
        try: requests.post(self._url, data={"chat_id":uid,"text":text,"parse_mode":"HTML"}, timeout=6)
        except Exception as e: print(f"[log] {e}")

# ── BOT ────────────────────────────────────────────────────────────────────────
class UzeronFreeBot:
    def __init__(self):
        self.bot   = TelegramClient(StringSession(os.getenv('BOT_SESSION_STRING','')), BOT_API_ID, BOT_API_HASH)
        self.db    = Database()
        self.log   = Logger()
        self.tasks       = {}   # uid → Task
        self.start_times = {}   # uid → datetime
        self.login_st    = {}   # uid → state dict
        self.pending_msg = set()

    # ── STARTUP ────────────────────────────────────────────────────────────────
    async def run(self):
        await self.bot.start(bot_token=FREE_BOT_TOKEN)
        sess = self.bot.session.save()
        if not os.getenv('BOT_SESSION_STRING'):
            print("="*60, "\nBOT_SESSION_STRING:\n", sess, "\n"+"="*60)
        self.db.init_db()
        self._reg()
        asyncio.create_task(self._brand_loop())
        print("✅ Uzeron Free Bot live!")
        await self.bot.run_until_disconnected()

    # ── BRANDING LOOP ─────────────────────────────────────────────────────────
    async def _brand_loop(self):
        while True:
            await asyncio.sleep(1800)
            try:
                for uid,_ in self.db.all_users():
                    u = self.db.get_user(uid)
                    if u and u[4] and u[11]:
                        asyncio.create_task(self._verify_brand(uid, u))
            except Exception as e: print(f"[brand_loop] {e}")

    async def _verify_brand(self, uid, user):
        cl = None
        try:
            cl = TelegramClient(StringSession(user[4]), BOT_API_ID, BOT_API_HASH)
            await cl.connect()
            if not await cl.is_user_authorized(): return
            me = await cl.get_me()
            if FREE_BRANDING_LASTNAME not in (me.last_name or ""):
                n    = self.db.add_warning(uid)
                left = FREE_WARNINGS_BEFORE_BAN - n
                if n >= FREE_WARNINGS_BEFORE_BAN:
                    self._stop_campaign(uid)
                    send_msg(uid,
                        "🚫 <b>Banned from Free Tier!</b>\n\n"
                        "You removed required branding 3 times.\n\n"
                        f"Upgrade to continue: {CONTACT_USERNAME}", kb_upgrade())
                    self.log.log(uid, f"🚫 Banned (branding) {uid}")
                else:
                    await self._apply_brand(cl, me)
                    send_msg(uid,
                        f"⚠️ <b>Branding Warning {n}/{FREE_WARNINGS_BEFORE_BAN}</b>\n\n"
                        "Branding was re-added automatically.\n"
                        f"⚠️ <b>{left} warning(s) left before ban!</b>", kb_upgrade())
        except Exception as e: print(f"[verify_brand {uid}] {e}")
        finally:
            if cl:
                try: await cl.disconnect()
                except: pass

    async def _apply_brand(self, cl, me=None):
        from telethon.tl.functions.account import UpdateProfileRequest
        if me is None: me = await cl.get_me()
        cur = me.last_name or ""
        if FREE_BRANDING_LASTNAME not in cur:
            await cl(UpdateProfileRequest(last_name=f"{cur} {FREE_BRANDING_LASTNAME}".strip(),
                                          about=FREE_BRANDING_BIO))

    async def _set_brand_for(self, uid, session) -> bool:
        cl = None
        try:
            cl = TelegramClient(StringSession(session), BOT_API_ID, BOT_API_HASH)
            await cl.connect()
            if not await cl.is_user_authorized(): return False
            await self._apply_brand(cl)
            self.db.set_branding(uid, 1)
            return True
        except Exception as e: print(f"[set_brand {uid}] {e}"); return False
        finally:
            if cl:
                try: await cl.disconnect()
                except: pass

    # ── STOP CAMPAIGN (sync safe) ──────────────────────────────────────────────
    def _stop_campaign(self, uid):
        if uid in self.tasks:
            self.tasks[uid].cancel()
            del self.tasks[uid]
        if uid in self.start_times:
            elapsed = int((datetime.now() - self.start_times[uid]).total_seconds())
            self.db.add_runtime(uid, elapsed)
            del self.start_times[uid]
        self.db.set_active(uid, 0)

    async def _abort_login(self, uid):
        st = self.login_st.pop(uid, None)
        if st and st.get('client'):
            try: await st['client'].disconnect()
            except: pass

    # ── REGISTER HANDLERS ──────────────────────────────────────────────────────
    def _reg(self):
        bot = self.bot

        # ── ADMIN ──────────────────────────────────────────────────────────────
        @bot.on(events.NewMessage(pattern='/ban'))
        async def cmd_ban(e):
            if e.sender_id not in ADMINS: return
            parts = e.message.text.split()
            if len(parts) < 2: await e.reply("Usage: /ban USER_ID"); return
            try:
                t = int(parts[1]); self.db.ban_user(t); self._stop_campaign(t)
                await e.reply(f"✅ Banned {t}")
                send_msg(t, f"🚫 <b>Banned from free tier.</b>\nContact {CONTACT_USERNAME}.", kb_upgrade())
            except Exception as ex: await e.reply(f"❌ {ex}")

        @bot.on(events.NewMessage(pattern='/users'))
        async def cmd_users(e):
            if e.sender_id not in ADMINS: return
            ul = self.db.all_users()
            lines = "\n".join(f"• {'@'+u if u else str(i)}" for i,u in ul)
            await e.reply(f"👥 <b>Users ({len(ul)}):</b>\n\n{lines}", parse_mode='html')

        @bot.on(events.NewMessage(pattern='/stats'))
        async def cmd_stats(e):
            if e.sender_id not in ADMINS: return
            await e.reply(f"📊 Users: {len(self.db.all_users())} | Running: {len(self.tasks)}", parse_mode='html')

        # ── /start ─────────────────────────────────────────────────────────────
        @bot.on(events.NewMessage(pattern='/start'))
        async def cmd_start(e):
            uid, uname = e.sender_id, e.sender.username
            if self.db.is_banned(uid):
                send_msg(uid, "🚫 <b>You are banned.</b>\nUpgrade to continue.", kb_upgrade()); return
            joined = await asyncio.get_event_loop().run_in_executor(None, check_joined_sync, uid)
            if not joined:
                send_msg(uid, txt_force_join(), kb_force_join()); return
            self.db.register_user(uid, uname)
            u = self.db.get_user(uid)
            send_msg(uid, txt_dashboard(u, self.db.get_runtime(uid)), kb_dashboard())

        # ── /cancel ────────────────────────────────────────────────────────────
        @bot.on(events.NewMessage(pattern='/cancel'))
        async def cmd_cancel(e):
            uid = e.sender_id
            self.pending_msg.discard(uid)
            await self._abort_login(uid)
            u = self.db.get_user(uid)
            send_msg(uid, txt_dashboard(u, self.db.get_runtime(uid) if u else 0), kb_dashboard())

        # ── CALLBACKS ──────────────────────────────────────────────────────────
        @bot.on(events.CallbackQuery())
        async def on_cb(event):
            uid  = event.sender_id
            data = event.data.decode()
            mid  = event.query.msg_id
            cbid = str(event.query.query_id)

            # Answer callback immediately (removes spinner) — non-blocking
            _tg("answerCallbackQuery", callback_query_id=cbid)

            if self.db.is_banned(uid):
                _tg("answerCallbackQuery", callback_query_id=cbid,
                    text="🚫 You are banned!", show_alert=True); return

            u  = self.db.get_user(uid)
            rt = self.db.get_runtime(uid) if u else 0

            # ── force-join check ────────────────────────────────────────────
            if data == 'check_join':
                joined = await asyncio.get_event_loop().run_in_executor(None, check_joined_sync, uid)
                if not joined:
                    edit_msg(uid, mid,
                        "❌ <b>Not joined yet!</b>\n\n"
                        "Please join <b>both</b> channels, then tap <b>I've Joined</b>.",
                        kb_force_join()); return
                self.db.register_user(uid, getattr(event.sender, 'username', None))
                u  = self.db.get_user(uid)
                rt = self.db.get_runtime(uid) if u else 0
                edit_msg(uid, mid, txt_dashboard(u, rt), kb_dashboard()); return

            # ── dashboard ────────────────────────────────────────────────────
            if   data == 'dashboard':
                edit_msg(uid, mid, txt_dashboard(u, rt), kb_dashboard())

            elif data == 'account':
                phone = u[1] if u and u[1] else "Not connected"
                conn  = "✅  Connected"  if u and u[4]  else "❌  Not connected"
                brand = "✅  Active"     if u and u[11] else "⏳  Pending"
                edit_msg(uid, mid,
                    "👤 <b>My Account</b>\n▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
                    f"📱  <b>Phone</b>     <code>{phone}</code>\n"
                    f"🔗  <b>Status</b>   {conn}\n"
                    f"🏷   <b>Branding</b> {brand}\n\n▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰",
                    kb([[{"text":"🔑 Login","callback_data":"login"},
                         {"text":"🚪 Logout","callback_data":"logout"}],
                        [{"text":"🏠 Back to Dashboard","callback_data":"dashboard"}]]))

            elif data == 'status':
                h_used = rt/3600
                filled = min(10, int(h_used/8*10))
                bar    = "█"*filled+"░"*(10-filled)
                s      = "🟢  Running" if u and u[6] else "🔴  Stopped"
                prev   = (u[5][:60]+"…" if u and u[5] and len(u[5])>60
                          else (u[5] if u and u[5] else "Not set"))
                edit_msg(uid, mid,
                    "📊 <b>Campaign Status</b>\n▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
                    f"📱  <b>Account</b>    <code>{u[1] if u and u[1] else 'Not set'}</code>\n"
                    f"✉️   <b>Message</b>   <i>{prev}</i>\n"
                    f"📡  <b>Status</b>    {s}\n"
                    f"🔢  <b>Max Groups</b> {FREE_MAX_GROUPS}\n\n"
                    f"⏳  <b>Runtime Today</b>\n     [{bar}]  {h_used:.1f}h / 8h\n\n"
                    "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰", kb_back())

            elif data == 'upgrade':
                edit_msg(uid, mid, txt_upgrade(), kb_upgrade())

            elif data == 'delay_info':
                _tg("answerCallbackQuery", callback_query_id=cbid,
                    text="⏱ 60s delay · 10min cycle\nUpgrade for custom delays!", show_alert=True)

            elif data == 'setmessage':
                self.pending_msg.add(uid)
                edit_msg(uid, mid,
                    "✍️ <b>Set Your Ad Message</b>\n▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
                    "Send your promotional message now.\n"
                    "It will be sent to all your joined groups.\n\n"
                    "💡 <i>Keep it short & punchy for best results</i>\n\n"
                    "Type /cancel to go back\n▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰",
                    kb([[{"text":"❌ Cancel","callback_data":"dashboard"}]]))

            elif data == 'startcampaign':
                if not u or not u[4]:
                    _tg("answerCallbackQuery",callback_query_id=cbid,text="❌ Login first!",show_alert=True); return
                if not u[5]:
                    _tg("answerCallbackQuery",callback_query_id=cbid,text="❌ Set your ad message first!",show_alert=True); return
                if uid in self.tasks:
                    _tg("answerCallbackQuery",callback_query_id=cbid,text="⚠️ Already running!",show_alert=True); return
                if rt >= FREE_MAX_RUNTIME:
                    edit_msg(uid, mid,
                        "⏰ <b>Daily Limit Reached!</b>\n\nUpgrade for unlimited runtime!", kb_upgrade()); return
                self.db.set_active(uid, 1)
                self.start_times[uid] = datetime.now()
                self.tasks[uid] = asyncio.create_task(self._campaign(uid))
                self.log.log(uid, f"🆓 Campaign start: {u[1]}")
                edit_msg(uid, mid, txt_dashboard(self.db.get_user(uid), rt), kb_dashboard())
                send_msg(uid,
                    "🚀 <b>Campaign Started!</b>\n▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
                    f"🔢  Groups:       <b>{FREE_MAX_GROUPS} max</b>\n"
                    f"⏱   Msg Delay:  <b>{FREE_MSG_DELAY}s</b>\n"
                    f"🔄  Cycle:          <b>{FREE_CYCLE_DELAY//60}m</b>\n"
                    f"⏳  Daily Limit: <b>8 hours</b>\n\n"
                    "▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n💎 <i>Upgrade for unlimited!</i>")

            elif data == 'stopcampaign':
                if uid not in self.tasks:
                    _tg("answerCallbackQuery",callback_query_id=cbid,text="⚠️ No campaign running!",show_alert=True); return
                self._stop_campaign(uid)
                send_msg(uid, "🛑 <b>Campaign Stopped!</b>")
                edit_msg(uid, mid, txt_dashboard(self.db.get_user(uid), self.db.get_runtime(uid)), kb_dashboard())

            elif data == 'login':
                if u and u[4]:
                    _tg("answerCallbackQuery",callback_query_id=cbid,text="✅ Already logged in!",show_alert=True); return
                self.login_st[uid] = {'step':'phone'}
                edit_msg(uid, mid,
                    "🔑 <b>Login to Your Telegram Account</b>\n▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
                    "📱 Send your phone number with country code:\n"
                    "Example: <code>+917239879045</code>\n\n"
                    "Type /cancel to go back\n▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰", kb_cancel())

            elif data == 'cancel_login':
                await self._abort_login(uid)
                edit_msg(uid, mid, txt_dashboard(u, rt), kb_dashboard())

            elif data == 'logout':
                self._stop_campaign(uid)
                self.db.logout_user(uid)
                send_msg(uid, "✅ <b>Logged out successfully!</b>")
                edit_msg(uid, mid, txt_dashboard(self.db.get_user(uid), 0), kb_dashboard())

            # ── OTP keypad ───────────────────────────────────────────────────
            elif data == 'otp_noop': pass

            elif data.startswith('otp_'):
                await self._otp_tap(event, uid, mid, cbid, data)

        # ── TEXT HANDLER ───────────────────────────────────────────────────────
        @bot.on(events.NewMessage())
        async def on_text(event):
            uid  = event.sender_id
            text = (event.message.text or "").strip()
            if not text or text.startswith('/'): return
            if self.db.is_banned(uid): return

            if uid in self.pending_msg:
                self.pending_msg.discard(uid)
                self.db.set_promo(uid, text)
                prev = text[:100]+("…" if len(text)>100 else "")
                send_msg(uid,
                    f"✅ <b>Ad Message Saved!</b>\n\n📝 Preview:\n<i>{prev}</i>",
                    kb([[{"text":"🚀 Start Campaign","callback_data":"startcampaign"}],
                        [{"text":"🏠 Dashboard","callback_data":"dashboard"}]])); return

            if uid in self.login_st:
                await self._login_text(uid, text)

    # ── OTP KEYPAD ─────────────────────────────────────────────────────────────
    async def _otp_tap(self, event, uid, mid, cbid, data):
        st = self.login_st.get(uid)
        if not st or st.get('step') != 'otp': return
        digits = st.setdefault('digits', [])

        if data == 'otp_back':
            if digits: digits.pop()
        elif data == 'otp_submit':
            code = ''.join(digits)
            if not code:
                _tg("answerCallbackQuery", callback_query_id=cbid,
                    text="⚠️ Enter the OTP first!", show_alert=True); return
            await self._submit_otp(uid, mid, st, code); return
        else:
            d = data.split('_',1)[1]
            if len(digits) < 6: digits.append(d)

        edit_msg(uid, mid,
            "📨 <b>Enter Your OTP</b>\n\n"
            "Tap the digits shown in your Telegram app:\n\n"
            "<i>✅ Submit when done  •  /cancel to abort</i>",
            kb_otp(''.join(digits)))

    async def _submit_otp(self, uid, mid, st, code):
        try:
            await st['client'].sign_in(st['phone'], code)
            await self._finish_login(uid, mid, st)
        except SessionPasswordNeededError:
            st['step'] = '2fa'; st['digits'] = []
            edit_msg(uid, mid,
                "🔐 <b>2FA Required</b>\n\n"
                "Your account has 2FA enabled.\n"
                "<b>Type and send</b> your 2FA password:\n\n"
                "Type /cancel to abort", kb_cancel())
        except Exception as e:
            st['digits'] = []
            edit_msg(uid, mid, f"❌ <b>Wrong OTP!</b>\n<code>{e}</code>\n\nTry again:", kb_otp(''))

    # ── LOGIN TEXT STEPS ───────────────────────────────────────────────────────
    async def _login_text(self, uid, text):
        st = self.login_st.get(uid)
        if not st: return
        step = st['step']

        if step == 'phone':
            phone = text.replace(' ','')
            if not phone.startswith('+'):
                send_msg(uid, "❌ Include country code.\nExample: <code>+917239879045</code>", kb_cancel()); return
            try:
                cl = TelegramClient(StringSession(), BOT_API_ID, BOT_API_HASH)
                await cl.connect()
                await cl.send_code_request(phone)
                st.update({'client':cl,'phone':phone,'step':'otp','digits':[]})
                send_msg(uid,
                    "📨 <b>OTP Sent!</b>\n\n"
                    "Use the keypad to enter your verification code:\n\n"
                    "<i>✅ Submit when done  •  /cancel to abort</i>",
                    kb_otp(''))
            except Exception as e:
                send_msg(uid, f"❌ Failed to send OTP: <code>{e}</code>", kb_cancel())
                self.login_st.pop(uid, None)

        elif step == '2fa':
            try:
                await st['client'].sign_in(password=text)
                await self._finish_login(uid, None, st)
            except Exception as e:
                send_msg(uid, f"❌ 2FA failed: <code>{e}</code>\n\nTry again or /cancel.", kb_cancel())
                await self._abort_login(uid)

    # ── COMPLETE LOGIN ─────────────────────────────────────────────────────────
    async def _finish_login(self, uid, mid, st):
        session = st['client'].session.save()
        phone   = st['phone']
        try: await st['client'].disconnect()
        except: pass
        self.login_st.pop(uid, None)
        self.db.save_session(uid, phone, session)
        self.log.log(uid, f"✅ Login: {phone}")

        notice = (f"✅ <b>Login Successful!</b>\n\n📱 <code>{phone}</code>\n\n"
                  "🏷️ Setting up required branding…")
        if mid: edit_msg(uid, mid, notice)
        else:   send_msg(uid, notice)

        ok = await self._set_brand_for(uid, session)
        if ok:
            send_msg(uid,
                "✅ <b>Account Setup Complete!</b>\n\n"
                f"🏷️ Branding added: <code>{FREE_BRANDING_LASTNAME}</code>\n\n"
                "⚠️ <b>Do NOT remove this branding!</b>\n"
                "3 removals = permanent ban from free tier.\n\n"
                "💎 Upgrade to remove branding requirement!",
                kb([[{"text":"✍️ Set Ad Message","callback_data":"setmessage"}],
                    [{"text":"🏠 Dashboard","callback_data":"dashboard"}]]))
        else:
            send_msg(uid,
                "✅ <b>Login Successful!</b>\n\n"
                f"⚠️ Add manually to last name:\n<code>{FREE_BRANDING_LASTNAME}</code>", kb_back())

    # ── CAMPAIGN ENGINE ────────────────────────────────────────────────────────
    async def _campaign(self, uid):
        cl = None
        try:
            u     = self.db.get_user(uid)
            phone = u[1]
            cl    = TelegramClient(StringSession(u[4]), BOT_API_ID, BOT_API_HASH)
            await cl.connect()

            if not await cl.is_user_authorized():
                send_msg(uid, "❌ <b>Session expired!</b> Logout and login again.", kb_back())
                self.db.set_active(uid, 0); return

            dialogs = await cl.get_dialogs()
            groups  = [d for d in dialogs if d.is_group][:FREE_MAX_GROUPS]

            if not groups:
                send_msg(uid, "❌ <b>No groups found!</b> Join some groups first.", kb_back())
                self.db.set_active(uid, 0); return

            send_msg(uid,
                f"📊 <b>Campaign Ready!</b>\n▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
                f"✅  Groups:      <b>{len(groups)}</b> / {FREE_MAX_GROUPS}\n"
                f"⏱   Msg Delay: <b>{FREE_MSG_DELAY}s</b>\n"
                f"🔄  Cycle:        <b>{FREE_CYCLE_DELAY//60}m</b>\n\n🚀 Starting…")

            t0    = datetime.now()
            round = 0

            while True:
                cur = self.db.get_user(uid)
                if not cur or not cur[6]: break

                saved   = self.db.get_runtime(uid)
                elapsed = (datetime.now() - t0).total_seconds()
                total   = saved + elapsed

                if total >= FREE_MAX_RUNTIME:
                    self.db.add_runtime(uid, int(elapsed))
                    self.start_times.pop(uid, None)
                    self.db.set_active(uid, 0)
                    self.tasks.pop(uid, None)
                    send_msg(uid,
                        "⏰ <b>Daily Limit Reached!</b>\n\n"
                        "8hr free limit used. Resumes tomorrow.\n\n"
                        "💎 Upgrade for unlimited runtime!", kb_upgrade())
                    self.log.log(uid, f"⏰ Limit reached: {phone}")
                    return

                round += 1
                sent, failed = 0, 0
                msg = self.db.get_user(uid)[5]   # refresh message each round

                for g in groups:
                    if not self.db.get_user(uid)[6]: break
                    # per-group runtime check (accurate)
                    if saved + (datetime.now()-t0).total_seconds() >= FREE_MAX_RUNTIME: break
                    try:
                        await cl.send_message(g.entity, msg)
                        sent += 1
                        self.log.log(uid, f"✓ {phone} → {g.name}")
                        await asyncio.sleep(FREE_MSG_DELAY)
                    except FloodWaitError as fe:
                        send_msg(uid, f"⚠️ FloodWait — pausing {fe.seconds}s…")
                        await asyncio.sleep(fe.seconds)
                    except Exception as ex:
                        failed += 1
                        print(f"[send {uid} {g.name}] {ex}")
                        await asyncio.sleep(5)

                elapsed = (datetime.now()-t0).total_seconds()
                h_left  = max(0.0, 8.0-(saved+elapsed)/3600)
                filled  = min(10, int((8.0-h_left)/8.0*10))
                bar     = "█"*filled+"░"*(10-filled)

                send_msg(uid,
                    f"✅ <b>Round {round} Complete!</b>\n▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n\n"
                    f"📤  Sent:    <b>{sent}</b>\n❌  Failed: <b>{failed}</b>\n\n"
                    f"⏳  Runtime Left\n     [{bar}]  {h_left:.1f}h\n\n"
                    f"🔄  Next round in <b>{FREE_CYCLE_DELAY//60}m</b>\n"
                    f"▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰▰\n💎 <i>Upgrade for unlimited!</i>",
                    kb([[{"text":"🛑 Stop Campaign","callback_data":"stopcampaign"}],
                        [{"text":"💎 Go Premium","callback_data":"upgrade"}]]))

                await asyncio.sleep(FREE_CYCLE_DELAY)

        except asyncio.CancelledError:
            print(f"[campaign {uid}] cancelled")
            # runtime already saved by _stop_campaign

        except Exception as e:
            print(f"[campaign {uid}] fatal: {e}")
            self.db.set_active(uid, 0)
            self.tasks.pop(uid, None)
            send_msg(uid, f"❌ <b>Campaign crashed:</b>\n<code>{e}</code>", kb_back())

        finally:
            if cl:
                try: await cl.disconnect()
                except: pass
            self.tasks.pop(uid, None)

# ── MAIN ───────────────────────────────────────────────────────────────────────
async def main():
    print("="*50, "\n  ⚡ UZERON ADSBOT — Free Tier\n"+"="*50)
    miss = [v for v in ['API_ID','API_HASH','FREE_BOT_TOKEN','LOGGER_BOT_TOKEN','ADMIN_IDS','DATABASE_URL']
            if not os.getenv(v)]
    if miss: print(f"❌ Missing: {', '.join(miss)}"); sys.exit(1)
    print("✅ All env vars loaded")
    await UzeronFreeBot().run()

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: print("\nStopped.")
    except Exception as e: print(f"Fatal: {e}"); sys.exit(1)
