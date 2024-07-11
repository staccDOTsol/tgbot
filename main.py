import voyageai
import numpy as np
import requests
import json
import anthropic
from telegram.ext import Application, CommandHandler, MessageHandler, filters


with open ("train_data.jsonl", "r") as f:
    documents = f.read().splitlines()
with open ("val_data.jsonl", "r") as f:
    documents = documents + f.read().splitlines()
import json
# Embed the documents in batches of 128
with open ('doc_embeds.json','r') as f:
    doc_embds = json.loads(f.read())
vo = voyageai.Client("pa-ZDlzKmYctTq0VQoiIssXbwqkv0SNcqH1Ivhc-bRdPCs")

# ... existing code for loading documents and doc_embds ...

def fetch_latest_data(token_ca):
    url = f"https://frontend-api.pump.fun/coins/{token_ca}"
    response = requests.get(url)
    if response.status_code == 200:
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            print("Error: Unable to parse JSON response")
            return None
    else:
        print(f"Error: Received status code {response.status_code}")
        return None

# Initialize Anthropic client
client = anthropic.Client(api_key="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")

def predict_score(token_ca):
    import base58

    def is_valid_solana_publickey(token_ca):
        try:
            # Attempt to decode the base58 string
            decoded = base58.b58decode(token_ca)
            # Check if the decoded length is 32 bytes (256 bits)
            return len(decoded) == 32
        except:
            return False

    if not is_valid_solana_publickey(token_ca):
        return "Error: Invalid Solana public key"
    latest_data = fetch_latest_data(token_ca)
    if latest_data:
        
        to_feed_openai = json.dumps({"prompt": "This is a memecoin on a memecoin launchpad. Your role is to determine the likelihood the coin gets to neither koth nor raydium (rate 0% value), king-of-the-hill which is medium value (rate 50%) or further onto raydium which is highest value (rate 100%). You are rating your confidence. You have all the context you need. You are rating the % chance this does well vs the other tokens you know about. Provide a single % value, where 0% is neither, 50% is koth, 100% is raydium.\n\nHere is the coin data:" + json.dumps({
            "mint": latest_data["mint"],
            "name": latest_data["name"],
            "symbol": latest_data["symbol"],
            "description": latest_data["description"],
            "image_uri": latest_data["image_uri"],
            "metadata_uri": latest_data["metadata_uri"],
            "twitter": latest_data["twitter"],
            "telegram": latest_data["telegram"],
            "creator": latest_data["creator"]}) + "."})
        query_embd = vo.embed([json.dumps(to_feed_openai)], model="voyage-2", input_type="query").embeddings[0]
        similarities = np.dot(doc_embds, query_embd)
        top_10_indices = np.argsort(similarities)[-10:][::-1]
        
        messages = []
        for idx in top_10_indices:
            messages.append({"role": "user", "content": json.loads(documents[idx])["prompt"]})
            messages.append({"role": "assistant", "content": json.loads(documents[idx])["completion"]})
        messages.append({"role": "user", "content": f"\nCurrent latest coin data:\n{json.dumps(to_feed_openai, indent=2)}\n"})
        
        completion = client.messages.create(model="claude-3-opus-20240229", max_tokens=1000, messages=messages)
        score = completion.content[0].text
        return score
    else:
        return "Error fetching data"

async def start(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome to the Pump Fun Prediction Bot! Send me a token CA to get a prediction.")

async def predict(update, context):
    token_ca = update.message.text.strip()
    score = predict_score(token_ca)
    if 'Error' in score:
        return
    print(f"(if this is simply a number from 0-100 then 0=bad 100=good) Prediction for token {token_ca}: {score}")
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"(if this is simply a number from 0-100 then 0=bad 100=good) Prediction for token {token_ca}: {score}")

def main():
    application = Application.builder().token('7319764650:AAEhe37YqceKBwrc1HOlsb8T1SE8CteahVc').build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, predict))
    application.run_polling()

if __name__ == '__main__':
    main()