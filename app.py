# -*- coding: utf-8 -*-

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

from __future__ import unicode_literals

import os
import sys
from argparse import ArgumentParser

from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookParser
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    FlexSendMessage, BubbleContainer, ImageComponent, BoxComponent,
    TextComponent, IconComponent, ButtonComponent,
    SeparatorComponent, QuickReply, QuickReplyButton,
    ImageSendMessage, URIAction, PostbackAction, MessageAction, PostbackEvent,
    UnfollowEvent, FollowEvent,
)

from kbbi import KBBI, AutentikasiKBBI
import psycopg2

app = Flask(__name__)

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
parser = WebhookParser(channel_secret)

userKBBI = os.getenv('USERNAME_KBBI', None)
passKBBI = os.getenv('PASSWORD_KBBI', None)
authKBBI = AutentikasiKBBI(userKBBI, passKBBI)

db_database = os.getenv('DB_DATABASE', None)
db_username = os.getenv('DB_USERNAME', None)
db_password = os.getenv('DB_PASSWORD', None)
db_host = os.getenv('DB_HOST')
db_port = os.getenv('DB_PORT')

def saveUserLog(user_id, event):
    conn = psycopg2.connect(database = db_database, user = db_username, password = db_password, host = db_host, port = db_port)
    cur = conn.cursor()
    sql = "INSERT INTO userLog(user_id,events) VALUES ('{0}','{1}')".format(user_id,event)
    cur.execute(sql)
    conn.commit()
    conn.close()

def getLastEventUserLog(user_id):
    conn = psycopg2.connect(database = db_database, user = db_username, password = db_password, host = db_host, port = db_port)
    cur = conn.cursor()
    sql = "SELECT events FROM userLog WHERE user_id='{0}' ORDER BY time_stamp DESC LIMIT 1".format(user_id)
    cur.execute(sql)
    rows = cur.fetchall()
    conn.close()
    if len(rows) > 0:
        return rows[0][0]
    else:
        return 'null'

def removeAllUserLog(user_id):
    conn = psycopg2.connect(database = db_database, user = db_username, password = db_password, host = db_host, port = db_port)
    cur = conn.cursor()
    sql = "DELETE FROM userLog WHERE user_id='{0}'".format(user_id)
    cur.execute(sql)
    conn.commit()
    conn.close()      

mulai_bubble = BubbleContainer(
    header=BoxComponent(
            layout="vertical",
            contents=[
                TextComponent(text="Line Bot KBBI",size="xl",weight="bold")
            ]
        ),
        body=BoxComponent(
            layout="vertical",
            contents=[
                TextComponent(text="Kamus Besar Bahasa Indonesia (KBBI) versi Line Bot", size="md", color="#c9302c"),
                TextComponent(text="Ini adalah Line Bot untuk melakukan pencarian kata pada KBBI yang juga dapat diakses melalui laman https://kbbi.kemendikbud.go.id",size="sm",wrap=True)
            ]
        ),
        footer=BoxComponent(
            layout="vertical",
            spacing="sm",
            contents=[
                ButtonComponent(
                    style="primary",
                    height="md",
                    action=PostbackAction(label="Cari Kata", data="action=start", displayText="start")
                )
            ]
        )
    )
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # parse webhook body
    try:
        events = parser.parse(body, signature)
    except InvalidSignatureError:
        abort(400)

    # if event is MessageEvent and message is TextMessage, then echo text
    for event in events:
        if not isinstance(event, MessageEvent):
            #continue
            if isinstance(event, PostbackEvent):
                postback_data = str(event.postback.data)
                lst_postback_data = postback_data.split()
                if len(lst_postback_data) == 1:
                    dat = lst_postback_data[0].split("=")[1]
                    if 'start' in dat:
                        saveUserLog(event.source.user_id, 'start')
                        txt_cari = "Silahkan ketikkan kata / frasa yang ingin anda cari"
                        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=txt_cari))
                elif len(lst_postback_data) == 2:
                    continue
            elif isinstance(event, FollowEvent):
                saveUserLog(event.source.user_id, 'mulai')
                message = FlexSendMessage(alt_text="Flex Mulai", contents=mulai_bubble)
                line_bot_api.reply_message(event.reply_token, message)
            elif isinstance(event, UnfollowEvent):
                removeAllUserLog(event.source.user_id)
        if not isinstance(event.message, TextMessage):
            continue

        text = str(event.message.text)

        if 'mulai' in text.lower():
            last_event = getLastEventUserLog(event.source.user_id)
            if 'start' in last_event:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text='memulai pencarian A'))
            else:
                saveUserLog(event.source.user_id, 'mulai')
                message = FlexSendMessage(alt_text="Flex Mulai", contents=mulai_bubble)
                line_bot_api.reply_message(event.reply_token, message)
        else:
            last_event = getLastEventUserLog(event.source.user_id)
            if 'start' in last_event:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text='memulai pencarian'))
            else:
                keterangan = "Perintah tidak dikenali. Untuk memulai silahkan ketik \"Mulai\""
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=keterangan))

    return 'OK'


if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', default=8000, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    app.run(debug=options.debug, port=options.port)
