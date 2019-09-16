#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import poplib
import configparser


def prepare_message(msg_id):
    a = mailbox.retr(msg_id)[1]
    a = [i.decode() for i in a]
    return '\n'.join(a)


def get_messages():
    global last_msgnum
    letters = mailbox.list()[1]
    for letter in letters:
        msgnum = letter.decode().split()[0]
        if int(msgnum) <= last_msgnum:
            continue
        last_msgnum = int(msgnum)
        print(prepare_message(msgnum), file=open(str(msgnum)+'.html', 'w', encoding='utf-8'))
        # yield prepare_message(msgnum)


config = configparser.ConfigParser()
config.read('config.ini')

login = config.get('email', 'login')
password = config.get('email', 'password')

last_msgnum = config.getint('email', 'last_msgnum')

host = 'pop.mail.ru'
port = 995

mailbox = poplib.POP3_SSL(host, port)
mailbox.user(login)
mailbox.pass_(password)

get_messages()

mailbox.quit()

config.set('email', 'last_msgnum', str(last_msgnum))
config.write(open('config.ini', 'w', encoding='utf-8'))
