import telebot

bot = telebot.TeleBot("387338626:AAHdxjE8IjMpVMqMZD2CLUav2Qrae4Av-Dg")


@bot.message_handler(commands=['start', 'get_id'])
def send_welcome(message):
    bot.reply_to(message, "Chat ID is: {}".format(message.chat.id))


bot.polling()
