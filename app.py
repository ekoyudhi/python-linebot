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
    ImageSendMessage, URIAction, PostbackAction
)

from kbbi import KBBI, AutentikasiKBBI

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
            continue
        if not isinstance(event.message, TextMessage):
            continue

        txt = str(event.message.text)
        if '/help' in txt:
            txt_start = 'Ini Line Bot untuk pencarian kata pada Kamus Besar Bahasa Indonesia.\nUntuk memmulai pencarian ketik perintah /kbbi kata_yang_dicari'
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=txt_start))
        elif '/kbbi' in txt:
            lst_txt = txt.split()
            if len(lst_txt) == 2:
                if '/kbbi' in lst_txt[0]:
                    #txt_kbbi_cari = "Pencarian kata "+lst_txt[1]+" ditemukan"
                    hasil = ""
                    try:
                        kata = KBBI(lst_txt[1], authKBBI)
                        hasil = str(kata)
                    except:
                        hasil = "Error / Tidak ditemukan"
                    bubble = BubbleContainer(
                        header=BoxComponent(
                            layout="vertical",
                            contents=[
                                TextComponent(text="Line Bot KBBI", size="xl", weight="bold")
                            ]
                        ),
                        hero=ImageComponent(
                            url="https://kantorbahasagorontalo.kemdikbud.go.id/wp-content/uploads/2020/02/KBBI.png",
                            size="full",
                            aspectRatio="4:3",
                            aspectMode="cover"
                        ),
                        body=BoxComponent(
                            layout="vertical",
                            contents=[
                                TextComponent(
                                    text="Kata yang dicari :",
                                    size="sm",
                                    color="#c9302c"
                                ),
                                TextComponent(
                                    text=lst_txt[1],
                                    size="sm",
                                    color="#c9302c",
                                    weight="bold"
                                ),
                                TextComponent(
                                    text=hasil,
                                    size="sm",
                                    wrap=True,
                                    margin="lg"
                                )
                            ]
                        ),
                        footer=BoxComponent(
                            layout="vertical",
                            contents=[
                                ButtonComponent(
                                    actions=[
                                        PostbackAction(
                                            label="cari_kata_lain",
                                            display_text="Cari Kata Lain",
                                            data="cari_kata_lain"
                                        )
                                    ]
                                )
                            ]
                        )
                    )
                    message = FlexSendMessage(alt_text="Ini Flex Message", contents=bubble)
                    line_bot_api.reply_message(event.reply_token, message)
            else:
                txt_kbbi_salah = "Perintah yang benar adalah /kbbi kata_yang_dicari"
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=txt_kbbi_salah))
        else:
            txt_not = 'Perintah tidak dimengerti.\nSilahkan ketik perintah /help'
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=txt_not))

    return 'OK'


if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', default=8000, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    app.run(debug=options.debug, port=options.port)
