#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import configparser
import io
import os
import tempfile
import time
from typing import Tuple

import mailparser
from imapclient import IMAPClient
from telebot import TeleBot

message_breakers = ["\n", ", "]


def get_emails(
    host: str,
    login: str,
    password: str,
    msg_type: str = "UNSEEN",
    last_uid: int = 0,
    read_only: bool = False,
) -> Tuple[mailparser.MailParser, int]:
    """Получение писем

    :param host: Адрес IMAP сервера
    :param login: Имя пользователя (почтовый ящик)
    :param password: Пароль
    :param msg_type: Критерий для поиска писем (по умолчанию возвращаются только непрочитанные письма)
    :param last_uid: ID последнего прочитанного письма
    :param read_only: Не помечать письма прочитанными?

    :rtype: Tuple[mailparser.MailParser, int]
    :returns: Возвращает объект письма и его ID
    """
    with IMAPClient(host) as server:
        server.login(login, password)
        server.select_folder("INBOX", readonly=read_only)

        mails = server.search(msg_type)
        for uid, message_data in server.fetch(mails, "RFC822").items():
            if uid <= last_uid:
                continue
            try:
                mail = mailparser.parse_from_bytes(message_data[b"RFC822"])
            except TypeError:  # TODO Некоторые письма вызывают эту ошибку при парсинге библиотекой mailparser
                pass
            else:
                yield mail, uid


def send_email_telegram(bot: TeleBot, chat_id: str, mail: mailparser.MailParser):
    subject = mail.subject
    from_ = " ".join(mail.from_[0])
    mail_name = "{} от {}".format(subject, from_)

    if mail.text_plain:  # Если существует текстовая версия письма
        message = "\n".join(mail.text_plain)
        bot.send_message(
            chat_id, split(message)[0]
        )  # Отправляем ее первые 4092 символа
        # И высылаем файл письма целиком (если письмо содержит более 4092 символов)
        if len(message) >= 2:
            f = io.BytesIO("{}\n\n{}".format(mail_name, message).encode())
            f.name = mail_name + ".txt"
            bot.send_document(chat_id, f, caption="Полный текст письма")

    if mail.text_html:  # Если существует веб версия письма, то отправляем ее файлом
        text_html = "\n".join(mail.text_html)
        f = io.BytesIO(text_html.encode())
        f.name = mail_name + ".html"
        bot.send_document(
            chat_id,
            f,
            caption="{} (веб версия письма)".format("{} от {}".format(subject, from_)),
        )

    if mail.attachments:  # Если есть вложения в письме, то отправляем и их.
        with tempfile.TemporaryDirectory() as tmp_dir:  # Создание временной директории для хранения вложений
            mail.write_attachments(tmp_dir)  # Сохраняем вложения
            for file in os.listdir(tmp_dir):
                bot.send_document(
                    chat_id, open(os.path.join(tmp_dir, file), "rb")
                )  # Отправляем вложения


def split(text: str, max_message_length: int = 4091) -> list:
    """ Разделение текста на части

    :param text: Разбиваемый текст
    :param max_message_length: Максимальная длина разбитой части текста
    """
    if len(text) >= max_message_length:
        last_index = max(
            map(
                lambda separator: text.rfind(separator, 0, max_message_length),
                message_breakers,
            )
        )
        good_part = text[:last_index]
        bad_part = text[last_index + 1:]
        return [good_part] + split(bad_part, max_message_length)
    else:
        return [text]


if __name__ == "__main__":
    # Инициализация и чтение конфигурации из файла config.ini
    config = configparser.ConfigParser()
    config.read("config.ini")
    imap_host = config.get("email", "host")
    username = config.get("email", "login")
    pass_ = config.get("email", "password")
    last_id = config.getint("email", "last_uid", fallback=0)
    read_only = config.getboolean("email", "read_only", fallback=False)
    mail_type = config.get("email", "criteria", fallback="UNSEEN")
    bot_token = config.get("telegram", "token")
    chat = config.get("telegram", "chat_id")
    bot_ = TeleBot(bot_token)
    # Получение непрочитанных писем
    for email, mail_id in get_emails(
        imap_host, username, pass_, mail_type, last_id, read_only
    ):
        # Отправка письма в Telegram
        send_email_telegram(bot_, chat, email)
        config.set("email", "last_uid", str(mail_id))
        config.write(open("config.ini", "w"))
        time.sleep(5)
