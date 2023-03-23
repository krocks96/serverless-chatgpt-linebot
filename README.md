# Serverless ChatGPT LineBot
Serverless Frameworkを使ってLineBot用のバックエンドを構築します

## 構成
- Python 3.9
- AWS
  - Lambda
  - API Gateway
  - DynamoDB

## デプロイ手順
以下の手順でデプロイします。
事前にAWSのプロファイルを設定が必要です。
> $ aws configure --profile profile_sample

1. .env.sampleを参考に.envファイルを作成して設定
    > $ cp .env.sample .env
2. プラグインのインストール
    > $ sls plugin install -n serverless-python-requirements
3. デプロイ
    > $ sls deploy --aws-profile profile_sample --stage dev

デプロイ後に発行されたエンドポイントをLineMessagingAPIのWebhook URLに設定してください

## 削除手順

作成したリソースを削除する場合はsls removeを使用してください。

> $ sls remove --aws-profile profile_sample --stage dev
