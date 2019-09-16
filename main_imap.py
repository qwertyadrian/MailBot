#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from imapclient import IMAPClient
import email
import configparser
import re
import base64
import os
import zipfile
import telebot
import binascii

regex = r'=\?UTF-8\?B\?'
regex1 = r'=\?KOI8-R\?B\?'


def payload_parser(payload, uid, archive):
    mimetype = payload.get_content_type()
    filename = payload.get_filename()

    if (mimetype == 'text/html') and not filename:
        filename = str(uid) + '.html'
        payload_writer(payload, filename, archive)
    elif filename:
        result = decode_text(r"=\?koi8-r\?B\?(.*)\?=", filename, regex1)
        if result:
            filename = base64.decodebytes(bytes(result, 'koi8-r')).decode('koi8-r')
        payload_writer(payload, filename, archive)
    elif mimetype == 'text/plain':
        filename = str(uid) + '.txt'
        payload_writer(payload, filename, archive)


def decode_text(reg, text, global_reg=regex):
    matches = re.finditer(reg, text, re.IGNORECASE | re.MULTILINE)
    for matchNum, match in enumerate(matches):
        return regexer(global_reg, match.group())


def regexer(reg, text):
    return re.sub(reg, '', text, flags=re.MULTILINE | re.IGNORECASE).replace('?=', '')


def payload_writer(payload, filename, archive):
    with open(filename, 'wb') as file:
        file.write(payload.get_payload(decode=True))
    archive.write(filename)
    os.remove(filename)


def get_emails(host, username, pass_, msg_type='UNSEEN'):
    try:
        os.chdir('INBOX')
    except FileNotFoundError:
        os.mkdir('INBOX')
        os.chdir('INBOX')

    with IMAPClient(host) as server:
        server.login(username, pass_)
        server.select_folder('INBOX', readonly=False)

        messages = server.search(msg_type)
        for uid, message_data in server.fetch(messages, 'RFC822').items():
            email_message = email.message_from_bytes(message_data[b'RFC822'])

            subject = email_message.get('Subject')
            subject = regexer(regex, subject)
            subject = regexer(regex1, subject)
            try:
                subject = base64.decodebytes(bytes(subject, 'utf-8')).decode()
            except (binascii.Error, UnicodeDecodeError):
                subject = base64.decodebytes(bytes(subject, 'koi8-r')).decode('koi8-r')

            from_ = email_message.get('From')

            result = decode_text(r"=\?utf-8\?B\?(.*)\?=", from_)
            if result:
                from_ = result

            result = decode_text(r"=\?koi8-r\?B\?(.*)\?=", from_)
            if result:
                from_ = result

            try:
                subject = subject + ' от ' + base64.decodebytes(bytes(from_, 'utf-8')).decode()
            except binascii.Error:
                subject = subject + ' от ' + from_
            except TypeError:
                pass

            archive = zipfile.ZipFile(file=subject + '.zip', mode='w', compression=zipfile.ZIP_DEFLATED)

            if email_message.is_multipart():
                for payload in email_message.get_payload():
                    payloads = payload.get_payload()
                    if type(payloads) is list:
                        for i in payloads:
                            payload_parser(i, uid, archive)
                    else:
                        payload_parser(payload, uid, archive)
            else:
                payload_parser(email_message, uid, archive)

            archive.close()


def send_emails_telegram(token, chat_id):
    bot = telebot.TeleBot(token)
    for file in os.listdir('.'):
        bot.send_document(chat_id, open(file, 'rb'), caption=file)
        os.remove(file)


def send_emails_vk(session, chat_id):
    raise NotImplementedError


if __name__ == '__main__':
    # Инициализация и чтение конфигурации из файла config.ini
    config = configparser.ConfigParser()
    config.read('config.ini')

    imap_host = config.get('email', 'host')
    login = config.get('email', 'login')
    password = config.get('email', 'password')
    bot_token = config.get('telegram', 'token')
    chat = config.get('telegram', 'chat_id')
    # Получение непрочитанных писем
    get_emails(imap_host, login, password)
    # Если не выполняется отладка, то отправка писем в Telegram
    if not __debug__:
        send_emails_telegram(bot_token, chat)
