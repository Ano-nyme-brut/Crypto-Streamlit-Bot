import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import datetime
import os
import json # Necessaire pour gerer l'etat multi-symbole

# --- 1. CONFIGURATION OBLIGATOIRE ---
# VOTRE CHAT ID ET TOKEN SONT MAINTENANT ENREGISTRES
TELEGRAM_TOKEN = "8360316491:AAGr91BYzrxOBN0w2h2Zp-bWwQOnvZ2ZhCI" 
TELEGRAM_CHAT_ID = "5200662478" 

# Parametres de trading pour l'alerte
EXCHANGE_ID = 'binance' # Utilisez 'coinbasepro' pour Coinbase ou 'bitpanda'
TIMEFRAME = '1h' # Periode d'analyse. Changez a '15m' pour des signaux plus rapides (mais plus de bruit).
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
RSI_PERIOD = 14

# --- LISTE DES SYMBOLES A SURVEILLER (MODIFIABLE) ---
# Le bot va boucler sur cette liste. Ajoutez ou retirez les paires de votre choix.
SYMBOLS_TO_CHECK = [
    'BTC/USDT', 
    'ETH/USDT', 
    'SOL/USDT', 
    'BNB/USDT', 
    # Ajoutez ici d'autres symboles de l'exchange choisi (ex: 'DOT/USDT')
]

# Fichier pour stocker le dernier signal envoye pour CHAQUE symbole
LAST_SIGNAL_FILE = 'last_signals.json'

# --- 2. Fonctions de Gestion de l'Etat et Telegram ---

def get_last_sent_signals():
    """Recupere les derniers signaux envoyes pour toutes les paires depuis le fichier JSON."""
    if os.path.exists(LAST_SIGNAL_FILE):
        try:
            with open(LAST_SIGNAL_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Erreur de lecture du fichier JSON des signaux. Reinitialisation.")
            return {}
    return {}

def save_last_sent_signals(signals_state):
    """Sauvegarde l'etat actuel des signaux dans le fichier JSON."""
    with open(LAST_SIGNAL_FILE, 'w') as f:
        json.dump(signals_state, f, indent=4)

def send_telegram_message(message):
    """Envoie le message a Telegram via l'API."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    
    try:
        requests.post(url, data=payload)
        # response.raise_for_status() # Non necessaire pour une simple notification
        # print("Alerte Telegram envoyee.")
    except requests.exceptions.RequestException as e:
        print(f"Erreur lors de l'envoi a Telegram: {e}")

# --- 3. Fonctions d'Analyse ---

def get_ohlcv_data(exchange_id, symbol, timeframe):
    """Recupere les donnees OHLCV pour un symbole unique."""
    try:
        exchange = getattr(ccxt, exchange_id)()
        # Utilise l'option de gestion des limites de CCXT
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=500)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        df['RSI'] = ta.rsi(df['close'], length=RSI_PERIOD)
        return df.dropna().iloc[-1]
    except Exception as e:
        # print(f"Erreur lors de la recuperation des donnees pour {symbol}: {e}")
        return None

def get_current_signal(last_row):
    """Determine le signal actuel."""
    if last_row is None:
        return 'ERREUR', 0.0, 0.0
    
    last_rsi = last_row['RSI']
    close_price = last_row['close']
    
    signal = 'NEUTRE'

    if last_rsi < RSI_OVERSOLD:
        signal = 'ACHAT FORT'
    elif last_rsi > RSI_OVERBOUGHT:
        signal = 'VENTE/CLÔTURE'
    
    return signal, close_price, last_rsi

def get_available_usdt_symbols(exchange_id):
    """Affiche la liste des paires USDT disponibles pour que l'utilisateur puisse copier-coller."""
    try:
        exchange = getattr(ccxt, exchange_id)()
        exchange.load_markets()
        usdt_symbols = [symbol for symbol in exchange.symbols if symbol.endswith('/USDT')]
        print(f"\n--- Symboles USDT disponibles sur {exchange_id.capitalize()} (pour la liste SYMBOLS_TO_CHECK) ---")
        for symbol in usdt_symbols:
            print(symbol)
        print("--------------------------------------------------------------------")
    except Exception as e:
        print(f"Impossible de recuperer la liste des symboles: {e}")

# --- 4. EXECUTION PRINCIPALE ---

if __name__ == "__main__":
    
    # 4.1. Recupere l'etat precedent des signaux
    signals_state = get_last_sent_signals()
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 4.2. Boucle sur tous les symboles a surveiller
    print(f"[{timestamp}] Checking {len(SYMBOLS_TO_CHECK)} symbols on {EXCHANGE_ID.capitalize()}...")
    
    for symbol in SYMBOLS_TO_CHECK:
        
        last_row = get_ohlcv_data(EXCHANGE_ID, symbol, TIMEFRAME)
        if last_row is None:
            # print(f"Skipping {symbol}...")
            continue
            
        signal, price, rsi = get_current_signal(last_row)
        last_sent_signal = signals_state.get(symbol, 'NONE') # Recupere le dernier signal pour cette paire
        
        # 4.3. Logique d'envoi d'alerte
        if signal in ['ACHAT FORT', 'VENTE/CLÔTURE']:
            
            if signal != last_sent_signal:
                
                # Formater le message Telegram
                if signal == 'ACHAT FORT':
                    icon = "🟢"
                    title = f"{icon} *ALERTE ACHAT FORT* {icon}"
                    color = "vert"
                else: # VENTE/CLÔTURE
                    icon = "🔴"
                    title = f"{icon} *ALERTE VENTE/CLÔTURE* {icon}"
                    color = "rouge"
                
                message = f"{title}\nPaire: `{symbol}` ({TIMEFRAME})\nExchange: {EXCHANGE_ID.capitalize()}\n"
                message += f"Prix: *{price:.2f}$*\nRSI ({RSI_PERIOD}): *{rsi:.2f}* (Zone {color})"
                
                send_telegram_message(message)
                signals_state[symbol] = signal # Mise a jour de l'etat
                print(f"   -> SENT: {symbol} is {signal}")
            else:
                # print(f"   -> NO CHANGE: {symbol} is still {signal}")
                pass
        
        elif signal == 'NEUTRE':
            # Si nous passons d'un signal fort a NEUTRE, on met a jour l'etat
            if last_sent_signal != 'NEUTRE':
                signals_state[symbol] = 'NEUTRE'
                # print(f"   -> STATE RESET: {symbol} reset to NEUTRE")
            
    # 4.4. Sauvegarde l'etat mis a jour
    save_last_sent_signals(signals_state)
    print(f"Total symbols checked: {len(SYMBOLS_TO_CHECK)}. State saved to {LAST_SIGNAL_FILE}.")
    
    # Aide pour l'utilisateur
    get_available_usdt_symbols(EXCHANGE_ID)