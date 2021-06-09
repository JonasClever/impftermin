import datetime
import json
from datetime import datetime
import requests

from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram import Update
import logging

STOREFILE = "contacts.txt"
bot_token = ':)'
chat_id_message_id = []
UPDATE_INTERVAL = 30  # seconds


def request(context: CallbackContext) -> None:
    now = datetime.now()
    chat_id = None
    pinned_message_id = None
    for entity in chat_id_message_id:
        chat_id = entity[0]
        pinned_message_id = entity[1]
        if context.job.name == str(chat_id):
            break
    if chat_id == None:
        print("Error: Chat_ID not found in request.")
        return
    r = requests.get("https://www.doctolib.de/availabilities.json",
                     data=
                     {
                         'start_date': now.strftime("%Y-%m-%d"),
                         'visit_motive_ids': '2736075',
                         'agenda_ids': '435743-460713-379939-432243',
                         'insurance_sector': 'public',
                         'practice_ids': '150739',
                         'limit': '3'
                     },
                     cookies={
                         "__cf_bm": "1c015d297d0084ecce33285b89d790c1dd288def-1622109295-1800-AbRcNYYNeehd7jlfZR7vX0fsTq/Hf0ly2S/kVqVZZFOW5qX4ouWUuvBZ2omgiJptI1W/UJsnupN0i73K0Op8azM="
                     },
                     headers={
                         "Host": "www.doctolib.de",
                         "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36",
                     })
    print(r.status_code, r.reason)
    if r.status_code == 200:
        print(json.dumps(r.json(), indent=4, sort_keys=True))
        if r.json() and r.json()["total"] > 0:
            text = ""
            text += "Impftermine: " + str(r.json()["total"]) + "\n"
            for availability in r.json()["availabilities"]:
                text += str(availability) + "\n"
            text += "https://www.doctolib.de/praxis/hueckelhoven/covid-testzentrum-heinsberg \n"  # direct link for notification text
            context.bot.send_message(chat_id=chat_id, text=text, disable_web_page_preview=True)

        context.bot.editMessageText(text=now.strftime("Stand: %H:%M:%S %d/%m/%Y"), chat_id=chat_id,
                                    message_id=pinned_message_id)
    else:
        context.bot.editMessageText(text=now.strftime("ERROR: %H:%M:%S %d/%m/%Y"), chat_id=chat_id,
                                    message_id=pinned_message_id)


# ----------------------------------------------------------------------


# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def start(update: Update, context: CallbackContext) -> None:
    global chat_id_message_id
    bot_chatID = update.message.chat_id
    already_added = False
    for entity in chat_id_message_id:
        chat_id = entity[0]
        if chat_id == bot_chatID:
            chat_id_message_id.remove(entity)
            pinned_message_id = context.bot.send_message(chat_id=bot_chatID, text="Started")["message_id"]
            context.bot.pinChatMessage(chat_id=bot_chatID, message_id=pinned_message_id)
            chat_id_message_id.append([bot_chatID, pinned_message_id])
            already_added = True
            break
    if already_added == False:
        pinned_message_id = context.bot.send_message(chat_id=bot_chatID, text="Start...")["message_id"]
        context.bot.pinChatMessage(chat_id=bot_chatID, message_id=pinned_message_id)
        chat_id_message_id.append([bot_chatID, pinned_message_id])
        context.job_queue.run_repeating(request, UPDATE_INTERVAL, context=bot_chatID, name=str(bot_chatID))
        user = update.message.from_user
        print('Add user {} and his user ID: {} '.format(user['username'], user['id']))
    with open(STOREFILE, 'w') as filehandle:
        json.dump(chat_id_message_id, filehandle)


def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


def stop(update: Update, context: CallbackContext) -> None:
    global chat_id_message_id
    remove_job_if_exists(str(update.message.chat_id), context)
    for entity in chat_id_message_id:
        chat_id = entity[0]
        if chat_id == update.message.chat_id:
            chat_id_message_id.remove(entity)
            with open(STOREFILE, 'w') as filehandle:
                json.dump(chat_id_message_id, filehandle)
            break
    context.bot.send_message(chat_id=update.message.chat_id, text="Service gestoppt.")


def main() -> None:
    global chat_id_message_id
    updater = Updater(bot_token)
    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('stop', stop))
    updater.start_polling()

    try:
        with open(STOREFILE, 'r') as filehandle:
            chat_id_message_id = json.load(filehandle)
        for entity in chat_id_message_id:
            updater.dispatcher.job_queue.run_repeating(request, UPDATE_INTERVAL, context=entity[0], name=str(entity[0]))
    except FileNotFoundError:
        pass
    updater.idle()


if __name__ == '__main__':
    main()
