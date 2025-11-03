import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import datetime
import matplotlib.pyplot as plt

# --- 1. Custom CSS for Minimalist Design ---
CUSTOM_CSS = """
<style>
/* Personnalisation Minimaliste 
    - Couleurs claires, coins arrondis, ombres subtiles 
*/

/* Corps de l'application et fond */
.stApp {
    background-color: #f0f2f6; /* Gris tres clair */
}

/* Conteneurs de donnees (Metrics) */
[data-testid="stMetric"] > div {
    border: 1px solid #e0e0e0;
    border-radius: 12px; /* Coins arrondis plus prononces */
    padding: 15px;
    background-color: white;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); /* Ombre legere */
    transition: transform 0.2s;
}

/* Style des boutons de rafraichissement */
.stButton>button {
    border-radius: 8px;
    border: none;
    color: white;
    background-color: #1f77b4; /* Bleu Streamlit standard */
    transition: all 0.2s;
    font-weight: 600;
}
.stButton>button:hover {
    background-color: #1a5e8e;
}

/* Masquer le pied de page 'Made with Streamlit' (optional for clean look) */
footer { visibility: hidden; }

/* Ajuster l'espacement autour des titres */
h1, h2, h3 {
    padding-top: 0.5rem;
    padding-bottom: 0.5rem;
}
</style>
"""

# --- Configuration et Constantes ---
# Liste des paires que vous souhaitez analyser
AVAILABLE_SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 
    'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'LINK/USDT'
]

# CORRECTION: L'identifiant 'coinbasepro' a ete renomme en 'coinbase' dans ccxt.
EXCHANGE = ccxt.coinbase() 
RSI_PERIOD = 14
INITIAL_BALANCE = 1000  # Capital de depart pour le Backtesting

@st.cache_data(ttl=60*5) # Mise en cache des donnees pour 5 minutes
def get_ohlcv_data(symbol, timeframe):
    """Recupere les donnees OHLCV de l'exchange."""
    st.info(f"Connexion a l'exchange pour charger les donnees {symbol}...")
    try:
        # Recupere 500 dernieres bougies
        ohlcv = EXCHANGE.fetch_ohlcv(symbol, timeframe, limit=500)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        return df
    except Exception as e:
        st.error(f"Erreur de connexion a l'exchange ou de recuperation des donnees : {e}")
        st.error("Impossible de charger les données. Veuillez vérifier l'exchange ou la paire selectionnee.")
        return pd.DataFrame()

def calculate_indicators(df):
    """Calcule le RSI et d'autres indicateurs necessaires."""
    if not df.empty:
        df['RSI'] = ta.rsi(df['close'], length=RSI_PERIOD)
        df = df.dropna()
    return df

def check_trading_signal(df, rsi_oversold, rsi_overbought):
    """Analyse la derniere ligne du DataFrame pour generer un signal en temps reel."""
    if df.empty:
        return 'ERREUR', 0.0, 0.0
        
    last_row = df.iloc[-1]
    last_rsi = last_row['RSI']
    close_price = last_row['close']
    
    signal = 'NEUTRE'

    if last_rsi < rsi_oversold:
        signal = 'ACHAT FORT'
    elif last_rsi > rsi_overbought:
        signal = 'VENTE/CLÔTURE'
    
    return signal, close_price, last_rsi

def run_backtest(df, rsi_oversold, rsi_overbought):
    """Simule la strategie RSI sur les donnees historiques."""
    if df.empty:
        return pd.DataFrame(), 0.0, 0.0, 0
    
    # 1. Generer les signaux historiques
    df['Signal'] = 0  # 0: Hold
    df.loc[df['RSI'] < rsi_oversold, 'Signal'] = 1  # 1: Acheter (Survente)
    df.loc[df['RSI'] > rsi_overbought, 'Signal'] = -1  # -1: Vendre (Surachat)
    
    # 2. Simulation de trading
    balance = INITIAL_BALANCE
    position = 0.0 # Quantite de crypto possedee
    trade_count = 0
    
    backtest_df = pd.DataFrame(columns=['Date', 'Type', 'Prix', 'Quantité', 'Capital'])

    for index, row in df.iterrows():
        # LOGIQUE D'ACHAT
        if row['Signal'] == 1 and position == 0:
            amount_to_buy = balance * 0.98 / row['close'] 
            balance -= amount_to_buy * row['close']
            position += amount_to_buy
            trade_count += 1
            backtest_df.loc[len(backtest_df)] = [index.strftime('%Y-%m-%d %H:%M'), 'ACHAT', f"{row['close']:.2f}", amount_to_buy, f"{balance:.2f}"]
            
        # LOGIQUE DE VENTE
        elif row['Signal'] == -1 and position > 0:
            balance += position * row['close']
            position = 0.0
            trade_count += 1
            backtest_df.loc[len(backtest_df)] = [index.strftime('%Y-%m-%d %H:%M'), 'VENTE', f"{row['close']:.2f}", 0, f"{balance:.2f}"]

    # 3. Calcul du resultat final
    final_value = balance + (position * df['close'].iloc[-1])
    profit_percent = ((final_value - INITIAL_BALANCE) / INITIAL_BALANCE) * 100
    
    return backtest_df, final_value, profit_percent, trade_count

# --- Interface Streamlit ---

# Configuration de la page et injection du CSS
st.set_page_config(layout="wide", page_title="Mon Bot Analyste Crypto", initial_sidebar_state="expanded")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True) # Injecte le CSS personnalise
plt.style.use('ggplot') # Utilise un style Matplotlib propre et moderne

st.title("💰 Bot d'Analyse Crypto (RSI) & Backtest")
st.caption(f"Dernière mise à jour : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# --- 1. Barre Latérale de Configuration ---
st.sidebar.header("⚙️ Paramètres")
selected_symbol = st.sidebar.selectbox("Paire Crypto", AVAILABLE_SYMBOLS)

# MODIFICATION : Ajout des intervalles en minutes
selected_timeframe = st.sidebar.selectbox("Intervalle", ['15m', '30m', '1h', '4h', '1d']) 

st.sidebar.markdown("---")
st.sidebar.subheader("Stratégie RSI")
rsi_oversold = st.sidebar.slider("RSI Survente (Achat)", 10, 40, 30)
rsi_overbought = st.sidebar.slider("RSI Surachat (Vente)", 60, 90, 70)
st.sidebar.info(f"**Achat :** RSI < {rsi_oversold} | **Vente :** RSI > {rsi_overbought}")

# --- 2. Récupération et Analyse ---
df = get_ohlcv_data(selected_symbol, selected_timeframe)
df = calculate_indicators(df)

if not df.empty:
    # Analyse en temps reel
    signal, price, last_rsi = check_trading_signal(df, rsi_oversold, rsi_overbought)
    
    st.header("Analyse en Temps Réel")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Paire / Intervalle", f"{selected_symbol} / {selected_timeframe}")
    col2.metric("Prix Actuel", f"${price:.2f}")
    col3.metric(f"RSI ({RSI_PERIOD})", f"{last_rsi:.2f}")
    
    # Affichage du Signal
    if signal == 'ACHAT FORT':
        col4.success(f"SIGNAL : {signal}")
    elif signal == 'VENTE/CLÔTURE':
        col4.error(f"SIGNAL : {signal}")
    else:
        col4.warning(f"SIGNAL : {signal}")
        
    st.markdown("---")
    
    # --- 3. Backtesting et Performance ---
    st.header("Backtesting de la Stratégie")
    
    backtest_df, final_value, profit_percent, trade_count = run_backtest(df.copy(), rsi_oversold, rsi_overbought)
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Capital Initial", f"${INITIAL_BALANCE:.2f}")
    col_b.metric("Valeur Finale", f"${final_value:.2f}", delta=f"{profit_percent:.2f}%")
    col_c.metric("Nombre de Trades", trade_count)

    st.subheader("Historique des Transactions")
    st.dataframe(backtest_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # --- 4. Visualisation Graphique (Mise a jour avec Matplotlib explicite et Volume) ---
    st.header(f"Graphiques d'Analyse Technique pour {selected_symbol}")
    
    # 4.1 Graphique du Prix
    fig_price, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(df.index, df['close'], label='Prix de Cloture', color='blue')
    ax1.set_title(f"Prix de Clôture ({selected_timeframe})", fontsize=14)
    ax1.set_ylabel("Prix (USDT)", color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    ax1.grid(True)
    st.pyplot(fig_price) # Affiche le graphique dans Streamlit
    plt.close(fig_price) # Ferme la figure pour liberer de la memoire
    
    # 4.2 Graphique du RSI
    fig_rsi, ax2 = plt.subplots(figsize=(10, 3))
    ax2.plot(df.index, df['RSI'], label='RSI (14)', color='purple')
    ax2.axhline(rsi_overbought, color='red', linestyle='--', label=f'Surachat ({rsi_overbought})')
    ax2.axhline(rsi_oversold, color='green', linestyle='--', label=f'Survente ({rsi_oversold})')
    ax2.set_title("Indice de Force Relative (RSI)", fontsize=14)
    ax2.set_ylim(0, 100) # Fixer l'axe Y du RSI de 0 a 100
    ax2.legend(loc='lower left')
    ax2.grid(True)
    st.pyplot(fig_rsi)
    plt.close(fig_rsi)

    # 4.3 Graphique du Volume
    fig_volume, ax3 = plt.subplots(figsize=(10, 3))
    # Utiliser une couleur differente pour le volume
    ax3.bar(df.index, df['volume'], color='gray', alpha=0.6)
    ax3.set_title("Volume de Trading", fontsize=14)
    ax3.set_ylabel("Volume", color='gray')
    ax3.tick_params(axis='y', labelcolor='gray')
    ax3.grid(True)
    st.pyplot(fig_volume)
    plt.close(fig_volume)


else:
    st.error("Impossible de charger les données. Veuillez vérifier votre connexion ou les paramètres.")

if st.button('🔄 Rafraîchir les Données'):
    st.cache_data.clear()
    st.experimental_rerun()
