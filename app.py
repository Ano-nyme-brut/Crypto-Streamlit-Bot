import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import datetime
import matplotlib.pyplot as plt
import numpy as np 

# --- 1. Custom CSS for Minimalist Design (Dark Theme) ---
CUSTOM_CSS = """
<style>
/* Personnalisation Minimaliste 
    - Thème Sombre (Dark Theme) pour un meilleur confort visuel.
*/

/* Corps de l'application et fond */
.stApp {
    background-color: #1a1a1a; /* Gris tres fonce / Noir */
    color: #f0f0f0; /* Texte clair */
}

/* Conteneurs de donnees (Metrics), Titres, et Sidebar */
[data-testid="stMetric"] > div {
    border: 1px solid #333333; /* Bordure sombre */
    border-radius: 12px; /* Coins arrondis */
    padding: 15px;
    background-color: #2b2b2b; /* Fond du conteneur légèrement plus clair que l'app */
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4); /* Ombre plus marquee */
    transition: transform 0.2s;
    color: #f0f0f0; /* Assurer que le texte dans les conteneurs est clair */
}
[data-testid="stMetric"] label {
    color: #aaaaaa; /* Etiquettes en gris clair */
}

/* Texte general (Titres et sous-titres) */
h1, h2, h3, h4, h5, h6, .st-b5, .st-b6, .st-b7 {
    color: #ffffff; /* Titres en blanc */
}

/* Sidebar */
.css-1d3w5iq, .css-1dp5x4y {
    background-color: #1a1a1a !important; /* Fond de la sidebar en noir */
    color: #f0f0f0 !important;
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
# <<< MODIFICATION : Le capital initial est maintenant défini par l'utilisateur
# INITIAL_BALANCE = 1000  <-- Supprimé

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

# <<< MODIFICATION : La fonction accepte maintenant 'start_balance' en argument
def run_backtest(df, rsi_oversold, rsi_overbought, start_balance):
    """Simule la strategie RSI sur les donnees historiques."""
    if df.empty:
        return pd.DataFrame(), 0.0, 0.0, 0
    
    # 1. Generer les signaux historiques
    df['Signal'] = 0  # 0: Hold
    df.loc[df['RSI'] < rsi_oversold, 'Signal'] = 1  # 1: Acheter (Survente)
    df.loc[df['RSI'] > rsi_overbought, 'Signal'] = -1  # -1: Vendre (Surachat)
    
    # 2. Simulation de trading
    # <<< MODIFICATION : Utilise le 'start_balance' fourni par l'utilisateur
    balance = start_balance 
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
    
    # <<< MODIFICATION : Calcule le profit en % basé sur 'start_balance'
    if start_balance > 0:
        profit_percent = ((final_value - start_balance) / start_balance) * 100
    else:
        profit_percent = 0.0
    
    return backtest_df, final_value, profit_percent, trade_count

# --- Interface Streamlit ---

# Configuration de la page et injection du CSS
st.set_page_config(layout="wide", page_title="Mon Bot Analyste Crypto", initial_sidebar_state="expanded")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True) # Injecte le CSS personnalise

# Changement de style Matplotlib pour correspondre au theme sombre
plt.style.use('dark_background') 

st.title("💰 Bot d'Analyse Crypto (RSI) & Backtest")
st.caption(f"Dernière mise à jour : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# --- 1. Barre Latérale de Configuration ---
st.sidebar.header("⚙️ Paramètres")
selected_symbol = st.sidebar.selectbox("Paire Crypto", AVAILABLE_SYMBOLS)
selected_timeframe = st.sidebar.selectbox("Intervalle", ['15m', '30m', '1h', '4h', '1d']) 

st.sidebar.markdown("---")

# <<< MODIFICATION : Ajout de la case pour le "prix à mettre" (capital)
st.sidebar.subheader("💰 Capital (Prix à mettre)")
user_capital = st.sidebar.number_input(
    "Capital de départ (USDT)", 
    min_value=10.0,  # Minimum 10 USDT
    value=1000.0,    # Valeur par défaut
    step=50.0,       # Incrément
    help="Entrez le montant que vous souhaitez simuler pour le backtest."
)
# <<< FIN MODIFICATION

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
    
    # <<< MODIFICATION : Passe 'user_capital' à la fonction de backtest
    backtest_df, final_value, profit_percent, trade_count = run_backtest(
        df.copy(), 
        rsi_oversold, 
        rsi_overbought, 
        user_capital # Utilise le capital de l'utilisateur
    )
    
    # Calcul de la durée du backtest en heures
    start_date = df.index.min()
    end_date = df.index.max()
    duration_timedelta = end_date - start_date
    total_hours = duration_timedelta.total_seconds() / 3600

    # <<< MODIFICATION : Calcule le profit total basé sur 'user_capital'
    total_profit = final_value - user_capital
    
    # Éviter la division par zéro si total_hours est 0
    avg_hourly_gain = total_profit / total_hours if total_hours > 0 else 0.0
    
    # <<< MODIFICATION : Passage de 4 à 5 colonnes pour la nouvelle case
    col_a, col_b, col_c, col_d, col_e = st.columns(5)
    
    # Affiche le capital initial entré par l'utilisateur
    col_a.metric("Capital Initial", f"${user_capital:.2f}") 
    col_b.metric("Valeur Finale", f"${final_value:.2f}", delta=f"{profit_percent:.2f}%")
    
    # <<< MODIFICATION : Ajout de la case "Potentiel de Gain"
    gain_delta_color = "normal"
    if total_profit < 0:
        gain_delta_color = "inverse"
        
    col_c.metric(
        "Potentiel de Gain (USD)", 
        f"${total_profit:.2f}", 
        delta_color=gain_delta_color,
        help="Ceci est le gain (ou la perte) net en dollars sur la période de simulation."
    )
    # <<< FIN MODIFICATION
    
    col_d.metric("Nombre de Trades", trade_count)
    col_e.metric(
        "Gain Moyen / Heure", 
        f"${avg_hourly_gain:.4f}", 
        help=f"Basé sur un gain total de ${total_profit:.2f} sur une période de {total_hours:.1f} heures."
    )

    st.subheader("Historique des Transactions")
    st.dataframe(backtest_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # --- 4. Visualisation Graphique (Mise a jour avec Matplotlib explicite et Volume) ---
    st.header(f"Graphiques d'Analyse Technique pour {selected_symbol}")
    
    # 4.1 Graphique du Prix
    fig_price, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(df.index, df['close'], label='Prix de Cloture', color='#4CAF50') # Ligne verte
    ax1.set_title(f"Prix de Clôture ({selected_timeframe})", fontsize=14, color='white')
    ax1.set_ylabel("Prix (USDT)", color='white')
    ax1.tick_params(axis='y', labelcolor='white')
    ax1.tick_params(axis='x', labelcolor='white')
    ax1.grid(True, color='#444444')
    st.pyplot(fig_price) # Affiche le graphique dans Streamlit
    plt.close(fig_price) # Ferme la figure pour liberer de la memoire
    
    # 4.2 Graphique du RSI
    fig_rsi, ax2 = plt.subplots(figsize=(10, 3))
    ax2.plot(df.index, df['RSI'], label='RSI (14)', color='cyan') # Ligne cyan
    ax2.axhline(rsi_overbought, color='red', linestyle='--', label=f'Surachat ({rsi_overbought})')
    ax2.axhline(rsi_oversold, color='green', linestyle='--', label=f'Survente ({rsi_oversold})')
    ax2.set_title("Indice de Force Relative (RSI)", fontsize=14, color='white')
    ax2.set_ylim(0, 100) # Fixer l'axe Y du RSI de 0 a 100
    ax2.legend(loc='lower left', frameon=True, facecolor='#2b2b2b', edgecolor='none', labelcolor='white')
    ax2.tick_params(axis='y', labelcolor='white')
    ax2.tick_params(axis='x', labelcolor='white')
    ax2.grid(True, color='#444444')
    st.pyplot(fig_rsi)
    plt.close(fig_rsi)

    # 4.3 Graphique du Volume
    fig_volume, ax3 = plt.subplots(figsize=(10, 3))
    # Utiliser une couleur differente pour le volume
    ax3.bar(df.index, df['volume'], color='#FFA500', alpha=0.6) # Barres oranges
    ax3.set_title("Volume de Trading", fontsize=14, color='white')
    ax3.set_ylabel("Volume", color='white')
    ax3.tick_params(axis='y', labelcolor='white')
    ax3.tick_params(axis='x', labelcolor='white')
    ax3.grid(True, color='#444444')
    st.pyplot(fig_volume)
    plt.close(fig_volume)

    # 4.4 Graphique de pronostic
    st.header(f"Pronostic du Prix pour {selected_symbol}")

    fig_forecast, ax_forecast = plt.subplots(figsize=(10, 5))
    
    # Tracer le prix de clôture historique
    ax_forecast.plot(df.index, df['close'], label='Prix de Clôture Historique', color='#4CAF50', alpha=0.7)

    # Préparer les données pour le pronostic
    last_close = df['close'].iloc[-1]
    last_timestamp = df.index[-1]

    # Déterminer la durée de la projection (par exemple, 10 futures bougies)
    if 'm' in selected_timeframe:
        delta_unit = int(selected_timeframe.replace('m', ''))
        time_delta = datetime.timedelta(minutes=delta_unit)
    elif 'h' in selected_timeframe:
        delta_unit = int(selected_timeframe.replace('h', ''))
        time_delta = datetime.timedelta(hours=delta_unit)
    elif 'd' in selected_timeframe:
        delta_unit = int(selected_timeframe.replace('d', ''))
        time_delta = datetime.timedelta(days=delta_unit)
    else: # Fallback au cas où
        time_delta = datetime.timedelta(hours=1) 
    
    future_timestamps = [last_timestamp + (time_delta * (i + 1)) for i in range(10)] # 10 bougies futures
    forecast_prices = [last_close] # Le premier point de la projection est le dernier prix actuel

    if signal == 'ACHAT FORT':
        # Projection haussiere
        for i in range(10):
            forecast_prices.append(forecast_prices[-1] * (1 + 0.001 * (1 + i/20))) 
        forecast_color = 'magenta'
        forecast_label = 'Pronostic : Hausse'
    elif signal == 'VENTE/CLÔTURE':
        # Projection baissiere
        for i in range(10):
            forecast_prices.append(forecast_prices[-1] * (1 - 0.001 * (1 + i/20))) 
        forecast_color = 'magenta'
        forecast_label = 'Pronostic : Baisse'
    else: # NEUTRE
        # Projection plate
        forecast_prices.extend([last_close] * 10)
        forecast_color = 'yellow'
        forecast_label = 'Pronostic : Neutre'

    # Concaténer le dernier timestamp historique avec les timestamps futurs pour le tracé
    plot_timestamps = [last_timestamp] + future_timestamps
    
    ax_forecast.plot(plot_timestamps, forecast_prices, 
                     label=forecast_label, 
                     color=forecast_color, 
                     linestyle='--', 
                     marker='o', 
                     markersize=4) 
    
    # Marquer le point de départ du pronostic
    ax_forecast.plot(last_timestamp, last_close, 'o', color='white', markersize=6, label='Point de départ du pronostic')

    ax_forecast.set_title("Pronostic du Prix basés sur le RSI", fontsize=14, color='white')
    ax_forecast.set_ylabel("Prix (USDT)", color='white')
    ax_forecast.tick_params(axis='y', labelcolor='white')
    ax_forecast.tick_params(axis='x', labelcolor='white')
    ax_forecast.grid(True, color='#444444')
    ax_forecast.legend(loc='upper left', frameon=True, facecolor='#2b2b2b', edgecolor='none', labelcolor='white')
    st.pyplot(fig_forecast)
    plt.close(fig_forecast)


else:
    st.error("Impossible de charger les données. Veuillez vérifier votre connexion ou les paramètres.")

if st.button('🔄 Rafraîchir les Données'):
    st.cache_data.clear()
    st.rerun()
