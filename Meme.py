# main.py - Your Solana Meme Coin Bot
import os
import telebot
import requests
import time
from flask import Flask, request
import json
from datetime import datetime

# Configuration
BOT_TOKEN = "YOUR_BOT_TOKEN"  # Get from @BotFather
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# Free Data Sources
DEXSCREENER_API = "https://api.dexscreener.com/latest"
BIRDEYE_API = "https://public-api.birdeye.so"  # Free tier

# Meme coin keywords
MEME_KEYWORDS = ['dog', 'cat', 'pepe', 'woof', 'bonk', 'shib', 'doge', 
                 'samoyed', 'husky', 'floki', 'babydoge', 'saitama']

def get_trending_meme_coins():
    """Fetch trending Solana meme coins"""
    try:
        # Get Solana pairs from DexScreener
        url = f"{DEXSCREENER_API}/dex/search?q=solana"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        meme_coins = []
        for pair in data.get('pairs', [])[:50]:  # Check top 50
            token_name = pair.get('baseToken', {}).get('name', '').lower()
            token_symbol = pair.get('baseToken', {}).get('symbol', '').lower()
            
            # Check if it's a meme coin
            if any(keyword in token_name or keyword in token_symbol 
                   for keyword in MEME_KEYWORDS):
                
                # Calculate safety score
                liquidity = float(pair.get('liquidity', {}).get('usd', 0))
                volume = float(pair.get('volume', {}).get('h24', 0))
                age = pair.get('pairCreatedAt', 0)
                
                # Basic scam detection
                is_safe = True
                risk_factors = []
                
                if liquidity < 10000:
                    is_safe = False
                    risk_factors.append("💀 Low liquidity")
                
                if volume < 1000:
                    is_safe = False
                    risk_factors.append("📉 No volume")
                
                coin_data = {
                    'name': pair.get('baseToken', {}).get('name', 'Unknown'),
                    'symbol': pair.get('baseToken', {}).get('symbol', 'Unknown'),
                    'price': float(pair.get('priceUsd', 0)),
                    'volume_24h': volume,
                    'liquidity': liquidity,
                    'price_change_24h': float(pair.get('priceChange', {}).get('h24', 0)),
                    'price_change_1h': float(pair.get('priceChange', {}).get('h1', 0)),
                    'dex': pair.get('dexId', 'Unknown'),
                    'url': f"https://dexscreener.com/solana/{pair.get('pairAddress', '')}",
                    'address': pair.get('pairAddress', ''),
                    'is_safe': is_safe,
                    'risk_factors': risk_factors,
                    'age': age
                }
                meme_coins.append(coin_data)
        
        # Sort by volume and safety
        safe_coins = [c for c in meme_coins if c['is_safe']]
        risky_coins = [c for c in meme_coins if not c['is_safe']]
        
        return {
            'safe': sorted(safe_coins, key=lambda x: x['volume_24h'], reverse=True)[:10],
            'risky': sorted(risky_coins, key=lambda x: x['volume_24h'], reverse=True)[:5]
        }
        
    except Exception as e:
        print(f"Error: {e}")
        return {'safe': [], 'risky': []}

def ai_analysis(coin):
    """Simple AI scoring (0-100)"""
    score = 50  # Base score
    
    # Volume score (up to 20 points)
    if coin['volume_24h'] > 1000000:
        score += 20
    elif coin['volume_24h'] > 500000:
        score += 15
    elif coin['volume_24h'] > 100000:
        score += 10
    elif coin['volume_24h'] > 50000:
        score += 5
    
    # Liquidity score (up to 20 points)
    if coin['liquidity'] > 500000:
        score += 20
    elif coin['liquidity'] > 200000:
        score += 15
    elif coin['liquidity'] > 100000:
        score += 10
    elif coin['liquidity'] > 50000:
        score += 5
    
    # Momentum score (up to 10 points)
    if coin['price_change_1h'] > 5:
        score += 10
    elif coin['price_change_1h'] > 2:
        score += 5
    elif coin['price_change_1h'] < -5:
        score -= 10
    
    # Risk penalties
    score -= len(coin['risk_factors']) * 10
    
    # Final score capped between 0-100
    return max(0, min(100, score))

def get_recommendation(score):
    """Convert score to recommendation"""
    if score >= 80:
        return "🚀 STRONG BUY", "High volume and liquidity, strong momentum"
    elif score >= 60:
        return "✅ BUY", "Good metrics, consider entering"
    elif score >= 40:
        return "👀 WATCH", "Decent but wait for confirmation"
    elif score >= 20:
        return "⚠️ CAUTION", "High risk, small position only"
    else:
        return "❌ AVOID", "Too risky, look elsewhere"

# Telegram Commands
@app.route('/', methods=['GET'])
def home():
    return "Bot is running!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return "OK", 200

@bot.message_handler(commands=['start'])
def start(message):
    welcome = """
🚀 *Solana Meme Coin Bot* 🚀

*Free Commands:*
/trending - Top 10 safe meme coins
/moonshots - High risk high reward
/check [symbol] - Analyze any coin
/alerts - Set price alerts (coming soon)
/learn - Meme coin safety tips

*Safety First!* Always DYOR
    """
    bot.reply_to(message, welcome, parse_mode="Markdown")

@bot.message_handler(commands=['trending'])
def trending(message):
    msg = bot.reply_to(message, "🔍 Scanning Solana for safe meme coins...")
    
    data = get_trending_meme_coins()
    safe_coins = data['safe']
    
    if not safe_coins:
        bot.edit_message_text("❌ No safe coins found right now", 
                            message.chat.id, msg.message_id)
        return
    
    response = "*📊 Top Safe Meme Coins*\n\n"
    
    for i, coin in enumerate(safe_coins[:5], 1):
        score = ai_analysis(coin)
        recommendation, reason = get_recommendation(score)
        
        response += f"{i}. *{coin['symbol']}*\n"
        response += f"💰 ${coin['price']:.8f}\n"
        response += f"📊 24h: {coin['price_change_24h']:.1f}%\n"
        response += f"💧 Liq: ${coin['liquidity']:,.0f}\n"
        response += f"🎯 Score: {score:.0f}/100 - {recommendation}\n"
        response += f"[View]({coin['url']}) | `{coin['address'][:8]}...`\n\n"
    
    bot.edit_message_text(response, message.chat.id, msg.message_id,
                         parse_mode="Markdown", disable_web_page_preview=True)

@bot.message_handler(commands=['moonshots'])
def moonshots(message):
    msg = bot.reply_to(message, "🔍 Finding high risk opportunities...")
    
    data = get_trending_meme_coins()
    risky_coins = data['risky']
    
    if not risky_coins:
        bot.edit_message_text("❌ No moonshots found right now", 
                            message.chat.id, msg.message_id)
        return
    
    response = "*🌙 Moonshot Opportunities (High Risk)*\n\n"
    
    for i, coin in enumerate(risky_coins[:3], 1):
        response += f"{i}. *{coin['symbol']}*\n"
        response += f"💰 ${coin['price']:.10f}\n"
        response += f"📊 Vol: ${coin['volume_24h']:,.0f}\n"
        response += f"⚠️ Risk: {', '.join(coin['risk_factors'])}\n"
        response += f"[View]({coin['url']})\n\n"
    
    response += "\n*⚠️ Warning: These are extremely risky!*"
    
    bot.edit_message_text(response, message.chat.id, msg.message_id,
                         parse_mode="Markdown", disable_web_page_preview=True)

@bot.message_handler(commands=['check'])
def check_coin(message):
    try:
        symbol = message.text.split()[1].upper()
        msg = bot.reply_to(message, f"🔍 Analyzing {symbol}...")
        
        # Search for coin
        url = f"https://api.dexscreener.com/latest/dex/search?q={symbol}"
        response = requests.get(url)
        data = response.json()
        
        # Find Solana pair
        sol_pair = None
        for pair in data.get('pairs', []):
            if pair.get('chainId') == 'solana':
                sol_pair = pair
                break
        
        if not sol_pair:
            bot.edit_message_text(f"❌ No Solana pair found for {symbol}", 
                                message.chat.id, msg.message_id)
            return
        
        # Create coin dict
        coin = {
            'name': sol_pair.get('baseToken', {}).get('name', 'Unknown'),
            'symbol': sol_pair.get('baseToken', {}).get('symbol', 'Unknown'),
            'price': float(sol_pair.get('priceUsd', 0)),
            'volume_24h': float(sol_pair.get('volume', {}).get('h24', 0)),
            'liquidity': float(sol_pair.get('liquidity', {}).get('usd', 0)),
            'price_change_24h': float(sol_pair.get('priceChange', {}).get('h24', 0)),
            'price_change_1h': float(sol_pair.get('priceChange', {}).get('h1', 0)),
            'dex': sol_pair.get('dexId', 'Unknown'),
            'url': f"https://dexscreener.com/solana/{sol_pair.get('pairAddress', '')}",
            'address': sol_pair.get('pairAddress', ''),
            'risk_factors': []
        }
        
        # Check risks
        if coin['liquidity'] < 10000:
            coin['risk_factors'].append("Low liquidity")
        if coin['volume_24h'] < 1000:
            coin['risk_factors'].append("Low volume")
        
        # Calculate score
        score = ai_analysis(coin)
        recommendation, reason = get_recommendation(score)
        
        response = f"""
*📈 Analysis: {coin['symbol']}*

💰 Price: ${coin['price']:.8f}
📊 24h Volume: ${coin['volume_24h']:,.0f}
💧 Liquidity: ${coin['liquidity']:,.0f}
📈 24h Change: {coin['price_change_24h']:.1f}%
🔄 DEX: {coin['dex']}

*AI Score: {score:.0f}/100*
{recommendation}
📝 {reason}

🔗 [View Chart]({coin['url']})
        """
        
        if coin['risk_factors']:
            response += f"\n⚠️ Risks: {', '.join(coin['risk_factors'])}"
        
        bot.edit_message_text(response, message.chat.id, msg.message_id,
                            parse_mode="Markdown", disable_web_page_preview=True)
        
    except IndexError:
        bot.reply_to(message, "Usage: /check BONK")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['learn'])
def learn(message):
    tips = """
*📚 Meme Coin Safety Tips*

1. *Check Liquidity*
   - Minimum $50k for safety
   - Locked liquidity is better

2. *Verify Contract*
   - Use Rugcheck.xyz
   - Check if mint function is disabled

3. *Look at Holders*
   - Top 10 holders < 20%
   - Avoid if one wallet has >10%

4. *Check Socials*
   - Active Twitter/Discord
   - No bots in comments

5. *Start Small*
   - Never invest more than you can lose
   - Take profits early

*Free Tools:*
🔍 Rugcheck.xyz
📊 DexScreener.com
👥 Solscan.io
    """
    bot.reply_to(message, tips, parse_mode="Markdown")

# Webhook setup
@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    webhook_url = request.url_root.rstrip('/') + '/webhook'
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return f"Webhook set to {webhook_url}", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
