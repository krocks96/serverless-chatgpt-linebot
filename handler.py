import json
import os
from shutil import ExecError
import time
import uuid
import openai
import boto3
from boto3.dynamodb.conditions import Key
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 環境変数から必要な情報を取得
OPENAI_API_KEY = os.environ['OPENAI_API_KEY']
LINE_CHANNEL_SECRET = os.environ['LINE_CHANNEL_SECRET']
LINE_CHANNEL_ACCESS_TOKEN = os.environ['LINE_CHANNEL_ACCESS_TOKEN']
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']

openai.api_key = OPENAI_API_KEY
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DYNAMODB_TABLE)

def webhook(event, context):
    print("Webhook called")
    signature = event["headers"].get("x-line-signature") or event["headers"].get("X-Line-Signature")
    body = event['body']

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Invalid signature'})
        }

    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'OK'})
    }

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    send_timestamp = int(time.time() * 1000)
    print("Handling message")
    user_id = event.source.user_id
    user_message = event.message.text
    user_message_obj = {"role": "user", "content": user_message}
    print(f"User message: {user_message}")
    # 履歴の取得
    message_history = get_message_history(user_id)
    # 履歴の順序を変えて最新のメッセージを追加
    messages = [{"role": item["message"]["role"], "content": item["message"]["content"]} for item in reversed(message_history)]
    messages.append(user_message_obj)
    print(f"Message history: {messages}")
    # API呼び出し
    try:
        openai_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            request_timeout=20
        )
    except Exception as e:
        print(f"Error generating AI response: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="エラーが発生しました。AIからの応答の生成に失敗しました。"))
        return
    # レスポンスの取得
    ai_message = openai_response.choices[0].message.content
    ai_message_obj = {"role": "assistant", "content": ai_message}
    receive_timestamp = int(time.time() * 1000)
    print(f"AI message: {ai_message}")
    # LINEへの返答
    try:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ai_message))
    except LineBotApiError as e:
        print(f"Error sending AI response: {e}")
        return
    # ユーザー発言の保存
    try:
        save_message_to_history(user_id, user_message_obj, send_timestamp)
    except Exception as e:
        print(f"Error saving user message: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="エラーが発生しました。メッセージの保存に失敗しました。"))
        return
    # AI発言の保存
    try:
        save_message_to_history(user_id, ai_message_obj , receive_timestamp)
    except Exception as e:
        print(f"Error saving AI message: {e}")
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="エラーが発生しました。メッセージの保存に失敗しました。"))

def get_message_history(user_id, limit=10):
    print(f"Getting message history for user: {user_id}")
    response = table.query(
        KeyConditionExpression=Key('user_id').eq(user_id),
        Limit=limit,
        ScanIndexForward=False
    )
    return response['Items']

def save_message_to_history(user_id, message, timestamp):
    print(f"Saving message to history: {message}")
    table.put_item(
        Item={
            'user_id': user_id,
            'timestamp': timestamp,
            'message': message
        }
    )
