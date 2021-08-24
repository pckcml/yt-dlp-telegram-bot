#!/usr/bin/env python3
# coding: utf-8
import os
import shlex, logging, json
from subprocess import run, CalledProcessError
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, CallbackQueryHandler, CallbackContext, Updater, CommandHandler, RegexHandler, Filters

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

with open('settings.json') as f:
    settings = json.load(f)

TOKEN = settings['TOKEN']
AUTHORIZED_USERS = settings['AUTHORIZED_USERS']
YTDLP_PATH = settings['YTDLP_PATH']
DOWNLOAD_DIR = settings['DOWNLOAD_DIR']

def restricted(func):
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        username = update.effective_user.username
        if username not in AUTHORIZED_USERS:
            response = "User {} is not authorized to use this bot.".format(username)
            logging.info(response)
            update.message.reply_text(response)
            return
        return func(update, context)
    return wrapped

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user.first_name
    response = "Hi {}. Type /help for more information about this bot.".format(user)
    update.message.reply_text(response)

@restricted
def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    response = 'To use this bot, just send a link of the YouTube video you would like to download, and it will be sent as a file to you.\n\ne.g. just send "https://www.youtube.com/watch?v=E3Pv4c4Qz9w" (without quotes) and I will show you the options.'
    update.message.reply_text(response)

def get_download_keyboard():
    keyboard = []
    options = ["audio", 360, 480, 720, 1080, 1440, "max"]

    for i in options:
        if type(i) is int:
            description = "Up to " + str(i) + "p 📺"
            data = "{} | {}".format(i, description)
        elif i == "audio":
            description = "Audio only 🎵"
            data = "{} | {}".format(i, description)
        else:
            description = "Maximum resolution available 📺"
            data = "{} | {}".format(i, description)

        keyboard.append([InlineKeyboardButton(description, callback_data=data)])

    return keyboard

def download(context) -> None:
    job = context.job
    link = job.context['link']
    message_id = job.context['message_id']
    user_id = job.context['user_id']
    option = job.context['option']

    logging.info('Job triggered')
    context.bot.send_message(
        user_id,
        "Working on it...",
        reply_to_message_id=message_id,
    )

    options = {
        "audio": "-f 'ba*[ext=mp3] / ba' -S 'ext'",
        "360": "-f 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv*+ba/b' -S 'res:360'",
        "480": "-f 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv*+ba/b' -S 'res:480'",
        "720": "-f 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv*+ba/b' -S 'res:720'",
        "1080": "-f 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv*+ba/b' -S 'res:1080'",
        "1440": "-f 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv*+ba/b' -S 'res:1440'",
        "max": "-f 'bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4] / bv*+ba/b'"
    }

    arg = options.get(option)

    # beware shell injections! shlex.quote should escape them
    # and the regex of the regexhandler should exclude other stuff
    command = "{} {} -o '%(title)s.%(resolution)s.%(ext)s' {} -P {} --restrict-filenames --exec echo".format(YTDLP_PATH, shlex.quote(link), arg, DOWNLOAD_DIR)

    try:
        result = run(command, shell=True, capture_output=True, check=True, cwd=DOWNLOAD_DIR)
        context.bot.send_message(
            user_id,
            "Download completed. Sending the file to you...",
            reply_to_message_id=message_id,
        )

        shell_output = result.stdout.decode('utf-8')
        path = shell_output.splitlines()[-1]

        if option == "audio":
            context.bot.send_audio(
                user_id,
                audio=open(path, "rb"),
                reply_to_message_id=message_id,
                timeout=15
            )
        else:
            context.bot.send_video(
                user_id,
                video=open(path, "rb"),
                reply_to_message_id=message_id,
                supports_streaming=True,
                timeout=15
            )
    except CalledProcessError as err:
        context.bot.send_message(
            user_id,
            "process exited with code {} ```{}```".format(err.returncode, err.output),
            reply_to_message_id=message_id,
        )


@restricted
def text_handler(update: Update, context: CallbackContext) -> None:
    response = "I'm sorry, but I couldn't find a valid YouTube URL here."
    update.message.reply_text(response, quote=True)

@restricted
def url_handler(update: Update, context: CallbackContext) -> None:
    context.user_data["link"] = update.message.text
    context.user_data["message_id"] = update.message.message_id
    context.user_data["user_id"] = update.effective_user.id

    keyboard = get_download_keyboard()
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('Please choose an option:', reply_markup=reply_markup)

def call_download_job(update: Update, context: CallbackContext) -> None:
    link = context.user_data["link"]
    message_id = context.user_data["message_id"]
    user_id = context.user_data["user_id"]
    option = context.user_data["option"]

    context.job_queue.run_once(download, 0, context={'link': link, 'message_id': message_id, 'user_id': user_id, 'option': option})

def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    option, description = query.data.split(" | ")
    query.edit_message_text(text="Selected option: {}".format(description))

    context.user_data["option"] = option

    call_download_job(update, context)

def get_logs_command() -> None:
    #cat log file, maybe last 10 lines or by date
    a = 1

def main() -> None:
    """Start the bot."""
    updater = Updater(TOKEN)

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("getLogs", get_logs_command))

    regex = 'https?://(www\.)?youtu(\.)?be(\.com)?/(?(3)watch\?v=|)?(?!playlist)[a-zA-Z0-9\-_]{4,15}'
    dispatcher.add_handler(MessageHandler(Filters.regex(regex), url_handler))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.regex(regex), text_handler))

    dispatcher.add_handler(CallbackQueryHandler(button))

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()