import static_ffmpeg
static_ffmpeg.add_paths()
import telebot
import yt_dlp
import os
import threading
import time
import uuid
import sqlite3
from telebot import types

# --- CONFIG ---
TOKEN = '8568112501:AAECoFsLJAdcjaE5RlmyzXH3JFodr4sbshE'
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

BASE_DIR = os.getcwd()
DB_PATH = os.path.join(BASE_DIR, "titan_supreme_v7.db")

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("CREATE TABLE IF NOT EXISTS maps (mid TEXT PRIMARY KEY, url TEXT, title TEXT)")
    conn.commit()
    return conn

db = init_db()

def save_media(url, title):
    mid = str(uuid.uuid4().hex)[:10]
    cursor = db.cursor()
    cursor.execute("INSERT INTO maps (mid, url, title) VALUES (?, ?, ?)", (mid, url, title))
    db.commit()
    return mid

def get_media(mid):
    cursor = db.cursor()
    cursor.execute("SELECT url, title FROM maps WHERE mid = ?", (mid,))
    return cursor.fetchone()

# --- SNAKE PROGRESS BAR ---
def make_progress_bar(percent):
    done = int(percent / 5)
    remain = 20 - done
    bar = "▰" * (done - 1) + "🐍" + "▱" * remain
    return bar

def progress_hook(d, chat_id, msg_id, last_update_time):
    if d['status'] == 'downloading':
        try:
            p_raw = d.get('_percent_str', '0%').replace('%', '').strip()
            percent = float(p_raw)
            current_time = time.time()
            if current_time - last_update_time[0] > 4:
                bar = make_progress_bar(percent)
                speed = d.get('_speed_str', 'N/A')
                text = (
                    f"<b>📥 TITAN PROCESSING...</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━\n"
                    f"<code>{bar}</code> {percent}%\n\n"
                    f"⚡ <b>Speed:</b> <code>{speed}</code>"
                )
                bot.edit_message_text(text, chat_id, msg_id)
                last_update_time[0] = current_time
        except: pass

# --- DOWNLOAD ENGINE ---
def titan_worker(chat_id, url, mode, quality, status_id):
    last_update = [0]
    try:
        file_id = f"TITAN_{int(time.time())}"
        save_tmpl = os.path.join(BASE_DIR, f"{file_id}.%(ext)s")
        ydl_opts = {
            'outtmpl': save_tmpl, 'quiet': True, 'no_warnings': True,
            'progress_hooks': [lambda d: progress_hook(d, chat_id, status_id, last_update)],
        }
        if mode == 'AUDIO':
            ydl_opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '320'}]})
        else:
            ydl_opts.update({'format': f'bestvideo[height<={quality}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'})

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            f_path = ydl.prepare_filename(info)
            if mode == 'AUDIO': f_path = os.path.splitext(f_path)[0] + ".mp3"

        bot.edit_message_text("<b>📤 TITAN UPLOADING...</b>", chat_id, status_id)
        with open(f_path, 'rb') as f:
            if mode == 'AUDIO': bot.send_audio(chat_id, f, caption=f"🎵 <b>{info['title']}</b>\n🚀 @TitanDownloaderBot")
            else: bot.send_video(chat_id, f, caption=f"🎥 <b>{info['title']}</b>\n🚀 @TitanDownloaderBot", supports_streaming=True)
        bot.delete_message(chat_id, status_id)
    except Exception as e:
        bot.edit_message_text(f"<b>❌ Error:</b> <code>{str(e)[:100]}</code>", chat_id, status_id)

# --- COMMAND HANDLERS ---

@bot.message_handler(commands=['start'])
def welcome(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🛠 Commands", callback_data="show_cmds"),
        types.InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/your_handle")
    )
    welcome_text = (
        "<b>🔱 TITAN SUPREME v7.0 🔱</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "Main duniya ka sabse fast search aur download engine hoon.\n\n"
        "✨ <b>Kya naya hai?</b>\n"
        "• High Quality MP3 (320kbps)\n"
        "• Snake Progress Bar 🐍\n"
        "• No Admin Required\n\n"
        "<b>👇 Bas kisi gaane ka naam likh kar bhejein!</b>"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

@bot.message_handler(commands=['cmds', 'help'])
def show_commands(message):
    cmd_text = (
        "<b>📜 TITAN BOT COMMANDS 📜</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🔹 /start - Bot ko restart/shuru karne ke liye.\n"
        "🔹 /cmds - Saari commands dekhne ke liye.\n"
        "🔹 /help - Help aur instructions ke liye.\n\n"
        "💡 <b>Tip:</b> Direct gaane ka naam likh kar search karein, ye sabse fast tarika hai!"
    )
    bot.send_message(message.chat.id, cmd_text)

@bot.message_handler(func=lambda m: True)
def search(message):
    query = message.text
    if query.startswith("/"): return
    s_msg = bot.reply_to(message, "🔍 <b>Titan is searching...</b>")
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
            res = ydl.extract_info(f"ytsearch8:{query}", download=False).get('entries', [])
        if not res: return bot.edit_message_text("❌ Kuch nahi mila!", message.chat.id, s_msg.message_id)

        markup = types.InlineKeyboardMarkup(row_width=1)
        for e in res:
            mid = save_media(e['url'], e['title'])
            markup.add(
                types.InlineKeyboardButton(f"🎵 Gana: {e['title'][:30]}...", callback_data=f"AUD|{mid}"),
                types.InlineKeyboardButton(f"🎥 Video: {e['title'][:30]}...", callback_data=f"VQS|{mid}")
            )
        bot.edit_message_text("<b>✅ Search Results Found!</b>", message.chat.id, s_msg.message_id, reply_markup=markup)
    except Exception as e: bot.edit_message_text(f"Error: {e}", message.chat.id, s_msg.message_id)

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    if call.data == "show_cmds":
        show_commands(call.message)
        return
    p = call.data.split('|')
    action, mid = p[0], p[1]
    data = get_media(mid)
    if not data: return
    url, title = data

    if action == "VQS":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("720p", callback_data=f"DL|720|{mid}"),
                   types.InlineKeyboardButton("1080p", callback_data=f"DL|1080|{mid}"))
        bot.edit_message_text(f"🎬 <b>Select Quality:</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)
    elif action == "AUD":
        threading.Thread(target=titan_worker, args=(call.message.chat.id, url, 'AUDIO', None, call.message.message_id)).start()
    elif action == "DL":
        quality, r_mid = p[1], p[2]
        r_url, _ = get_media(r_mid)
        threading.Thread(target=titan_worker, args=(call.message.chat.id, r_url, 'VIDEO', quality, call.message.message_id)).start()

if __name__ == "__main__":
    print("🚀 TITAN SUPREME v7.0 ONLINE")
    bot.infinity_polling()
              
