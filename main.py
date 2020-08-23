#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser
import os

import mailparser
from imapclient import IMAPClient
from telebot import TeleBot

message_breakers = ["\n", ", "]


def get_emails(
    host: str, username: str, password: str, msg_type: str = "UNSEEN", last_uid: int = 0, read_only: bool = False
) -> int:
    """Получение писем

    :param host: Адрес IMAP сервера
    :param username: Имя пользователя (почтовый ящик)
    :param password: Пароль
    :param msg_type: Критерий для поиска писем (по умолчанию возвращаются только непрочитанные письма)
    :param last_uid: ID последнего прочитанного письма
    :param read_only: Не помечать письма прочитанными?

    :rtype: int
    :returns: Возвращает ID последнего прочитанного письма
    """
    try:
        os.chdir("INBOX")
    except FileNotFoundError:
        os.mkdir("INBOX")
        os.chdir("INBOX")

    with IMAPClient(host) as server:
        server.login(username, password)
        server.select_folder("INBOX", readonly=read_only)

        mails = server.search(msg_type)
        for uid, message_data in server.fetch(mails, "RFC822").items():
            if uid <= last_uid:
                continue
            mail = mailparser.parse_from_bytes(message_data[b"RFC822"])

            subject = mail.subject
            from_ = " ".join(mail.from_[0])

            dir_name = "{} от {}".format(subject, from_)

            os.mkdir(dir_name)
            os.chdir(dir_name)

            if mail.text_plain:
                text_plain = "\n".join(mail.text_plain)
                with open("text_plain.txt", "w") as f:
                    f.write("{}\n\n{}".format(dir_name, text_plain))

            if mail.text_html:
                text_html = "\n".join(mail.text_html)
                with open("text_html.html", "w") as f:
                    f.write(text_html)

            if mail.attachments:
                mail.write_attachments("attachments")

            os.chdir("../")

    os.chdir("../")
    return mails[-1] if mails else last_uid


def send_emails_telegram(bot: TeleBot, chat_id: str):
    os.chdir("INBOX")  # Переход в папку с сохраненными письмами
    for mail in os.listdir("."):  # Получаем список папок, в которых лежит само письмо и его вложения
        os.chdir(mail)  # Переходим в папку с письмом

        if os.path.exists("text_plain.txt"):  # Если существует текстовая версия письма
            with open("text_plain.txt") as f:
                message = split(f.read())
            bot.send_message(chat_id, message[0])  # Отправляем ее первые 4092 символа
            if len(message) >= 2:  # И высылаем файл письма целиком (если письмо содержит более 4092 символов)
                bot.send_document(chat_id, open("text_plain.txt", "rb"), caption="Продолжение письма")
            os.remove("text_plain.txt")  # Удаляем отправленный файл

        if os.path.exists("text_html.html"):  # Если существует веб версия письма, то отправляем ее файлом
            bot.send_document(chat_id, open("text_html.html", "rb"), caption="{} (веб версия письма)".format(mail))
            os.remove("text_html.html")  # Удаляем отправленный файл

        if os.path.exists("attachments"):  # Если есть вложения в письме, то отправляем и их.
            for file in os.listdir("attachments"):
                bot.send_document(chat_id, open(file, "rb"))
                os.remove(file)  # Удаляем отправленный файл
            os.rmdir("attachments")  # Удаляем пустую папку

        os.chdir("../")  # Выходим из папки с письмом
        os.rmdir(mail)  # И удаляем ее, так как она пуста
    os.chdir("../")  # Выходим из папки с сохраненными письмами


def split(text: str, max_message_length: int = 4091) -> list:
    """ Разделение текста на части

    :param text: Разбиваемый текст
    :param max_message_length: Максимальная длина разбитой части текста
    """
    if len(text) >= max_message_length:
        last_index = max(map(lambda separator: text.rfind(separator, 0, max_message_length), message_breakers))
        good_part = text[:last_index]
        bad_part = text[last_index + 1:]
        return [good_part] + split(bad_part, max_message_length)
    else:
        return [text]


if __name__ == "__main__":
    # Инициализация и чтение конфигурации из файла config.ini
    config = configparser.ConfigParser()
    config.read("config.ini")
    host = config.get("email", "host")
    login = config.get("email", "login")
    password = config.get("email", "password")
    last_uid = config.getint("email", "last_uid")
    bot_token = config.get("telegram", "token")
    chat = config.get("telegram", "chat_id")
    bot = TeleBot(bot_token)
    # Получение непрочитанных писем
    last_uid = get_emails(host, login, password, last_uid=last_uid)
    config.set("email", "last_uid", str(last_uid))
    config.write(open("config.ini", "w"))
    # Отправка писем в Telegram
    send_emails_telegram(bot, chat)
