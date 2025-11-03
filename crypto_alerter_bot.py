# -*- coding: utf-8 -*-
import ccxt
import pandas as pd
import pandas_ta as ta
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Configuration du Bot Telegram ---
# REMPLACER 'VOTRE_TOKEN_TELEGRAM_ICI' PAR LE VRAI TOKEN OBTENU VIA BOTFATHER
BOT_TOKEN = "8360316491:AAGr91BYzrxOBN0w2h2Zp-bWwQOnvZ2ZhCI" 

# Configurer le logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- Configuration de l'Alerte Automatique ---
# IMPORTANT : Remplacez par l'ID de votre chat/groupe
# Utilisez la commande /getid dans le bot pour trouver votre ID apres le lancement
TARGET_CHAT_ID = "VOTRE_CHAT_ID_ICI" 
WATCH_SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT']
ALERT_TIMEFRAME = '15m' # Verification toutes les 15 minutes

# --- Configuration et Constantes Crypto ---
EXCHANGE = ccxt.coinbase() 
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# --- Fonctions d'Analyse (Adaptees du Streamlit App) ---

def get_ohlcv_data(symbol, timeframe):
    """Fetches OHLCV data from the exchange (max 500 candles)."""
    try:
        # Fetch 500 latest candles
        ohlcv = EXCHANGE.fetch_ohlcv(symbol, timeframe, limit=500)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        return df
    except Exception as e:
        logging.error(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()

def calculate_indicators(df):
    """Calculates RSI and drops NaN values."""
    if not df.empty:
        df['RSI'] = ta.rsi(df['close'], length=RSI_PERIOD)
        df = df.dropna()
    return df

def check_trading_signal(df):
    """Analyzes the last row of the DataFrame to generate a real-time signal."""
    if df.empty:
        return 'ERREUR', 0.0, 0.0
        
    last_row = df.iloc[-1]
    last_rsi = last_row['RSI']
    close_price = last_row['close']
    
    signal = 'NEUTRE'

    if last_rsi < RSI_OVERSOLD:
        signal = 'ACHAT FORT'
    elif last_rsi > RSI_OVERBOUGHT:
        signal = 'VENTE/CLÔTURE'
    
    return signal, close_price, last_rsi

# --- Job d'Alerte Automatique ---

async def send_alerts_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Vérifie périodiquement les signaux de trading et envoie une alerte si nécessaire."""
    # Correction pour s'assurer que TARGET_CHAT_ID est un entier ou une string valide avant l'envoi
    if TARGET_CHAT_ID == "VOTRE_CHAT_ID_ICI" or not TARGET_CHAT_ID:
        logging.warning("Alerte non envoyee: TARGET_CHAT_ID n'est pas configure.")
        return

    logging.info(f"Execution de la tâche d'alerte automatique ({ALERT_TIMEFRAME})...")
    
    for symbol in WATCH_SYMBOLS:
        df = get_ohlcv_data(symbol, ALERT_TIMEFRAME)
        if df.empty:
            continue
            
        df = calculate_indicators(df)
        signal, price, last_rsi = check_trading_signal(df)

        if signal in ['ACHAT FORT', 'VENTE/CLÔTURE']:
            
            # Preparation du message
            emoji = '🟢' if signal == 'ACHAT FORT' else '🔴'
            
            alert_message = (
                f"{emoji} **ALERTE {signal}** sur {symbol} ({ALERT_TIMEFRAME})"
                f"\n\n**Prix :** ${price:.2f}"
                f"\n**RSI ({RSI_PERIOD}) :** {last_rsi:.2f}"
            )
            
            # Envoi du message au chat cible
            await context.bot.send_message(
                chat_id=TARGET_CHAT_ID, 
                text=alert_message, 
                parse_mode='Markdown'
            )
            logging.info(f"Alerte envoyee pour {symbol}: {signal}")

# --- Gestionnaires de Commandes Telegram ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command."""
    await update.message.reply_text(
        'Bienvenue sur le Bot Analyste Crypto !'
        '\n\nUtilisez la commande /analyse <symbole> <intervalle> pour obtenir un signal RSI.'
        '\nExemple : `/analyse BTC/USDT 4h`'
        '\nIntervalles : 15m, 30m, 1h, 4h, 1d.'
        '\n\nPour configurer les alertes automatiques, utilisez `/getid`.'
    )

async def analyse_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /analyse command and performs the crypto analysis."""
    args = context.args
    
    if len(args) != 2:
        await update.message.reply_text(
            "Format incorrect. Utilisez : `/analyse <symbole> <intervalle>`\nExemple : `/analyse BTC/USDT 4h`"
        )
        return

    symbol = args[0].upper()
    timeframe = args[1].lower()

    await update.message.reply_text(f"Analyse en cours pour **{symbol}** sur **{timeframe}**...", parse_mode='Markdown')

    # 1. Recuperation des donnees
    df = get_ohlcv_data(symbol, timeframe)

    if df.empty:
        await update.message.reply_text(f"❌ Impossible de charger les données pour {symbol} sur {timeframe}. Vérifiez la paire.")
        return
    
    # 2. Calcul et Signal
    df = calculate_indicators(df)
    signal, price, last_rsi = check_trading_signal(df)

    # 3. Formatage de la reponse
    if signal == 'ERREUR':
        response_text = "Une erreur est survenue lors du calcul du signal."
    else:
        # Preparation du message
        if signal == 'ACHAT FORT':
            emoji = '🟢'
        elif signal == 'VENTE/CLÔTURE':
            emoji = '🔴'
        else:
            emoji = '🟡'

        response_text = (
            f"--- **ANALYSE {symbol} ({timeframe})** ---"
            f"\n\n**Prix Actuel :** ${price:.2f}"
            f"\n**RSI ({RSI_PERIOD}) :** {last_rsi:.2f}"
            f"\n\n**Signal de Trading :** {emoji} **{signal}**"
            f"\n\n*Seuil d'Achat (Survente) :* RSI < {RSI_OVERSOLD}"
            f"\n*Seuil de Vente (Surachat) :* RSI > {RSI_OVERBOUGHT}"
        )

    await update.message.reply_text(response_text, parse_mode='Markdown')

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Aide l'utilisateur a trouver l'ID du chat pour les alertes automatiques."""
    chat_id = update.message.chat_id
    await update.message.reply_text(
        f"Votre ID de chat est : `{chat_id}`\n\n"
        "Veuillez copier cet ID et remplacer `VOTRE_CHAT_ID_ICI` dans la variable `TARGET_CHAT_ID` "
        "dans le script Python pour recevoir les alertes automatiques.",
        parse_mode='Markdown'
    )

# --- Fonction Principale (Main) ---

def main() -> None:
    """Start the bot and the job queue."""
    if BOT_TOKEN == "VOTRE_TOKEN_TELEGRAM_ICI":
        logging.error("Veuillez remplacer 'VOTRE_TOKEN_TELEGRAM_ICI' par votre vrai jeton de bot.")
        return

    # 1. Creation de l'Application et passage du token
    application = Application.builder().token(BOT_TOKEN).build()
    job_queue = application.job_queue # Recuperation de la file d'attente

    # 2. Ajout des gestionnaires de commandes
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("analyse", analyse_command))
    application.add_handler(CommandHandler("getid", get_chat_id))

    # 3. Planification de la tâche d'alerte automatique
    # Execute la fonction send_alerts_job toutes les 300 secondes (5 minutes)
    job_queue.run_repeating(send_alerts_job, interval=300, first=0)
    
    # 4. Demarrer le bot (mode polling pour une execution simple)
    logging.info("Le Bot Telegram est en cours d'execution (Polling) avec Alertes Automatiques...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
