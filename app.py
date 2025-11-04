import streamlit as st
import yfinance as yf  ### MODIFIÉ : Import yfinance
import pandas as pd
import pandas_ta as ta
import datetime
import matplotlib.pyplot as plt
import numpy as np 

# --- 1. Custom CSS pour un Design "Fintech Moderne" ---
# (CSS Inchangé)
CUSTOM_CSS = """
<style>
/* Thème : "Fintech Moderne"
    - Palette sombre avec des accents "électriques" (bleu/cyan).
    - Cartes flottantes sans bordures.
    - Typographie plus nette.
*/

/* Police de base et fond général de l'application */
.stApp {
    font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', sans-serif;
    background-color: #1a1a1a; /* Fond principal (très sombre) */
    color: #f0f0f0; /* Texte clair par défaut */
}

/* Conteneurs de données (Metrics) */
[data-testid="stMetric"] > div {
    border: none; /* Suppression de la bordure */
    border-radius: 12px;
    padding: 18px;
    background-color: #2b2b2b; /* Fond de la carte (plus clair) */
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.35); /* Ombre plus douce */
    transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
}

/* Effet de survol pour les cartes */
[data-testid="stMetric"] > div:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 24px rgba(0, 0, 0, 0.45);
}

/* Étiquettes des métriques (ex: "Prix Actuel") */
[data-testid="stMetric"] label {
    color: #aaaaaa;
    font-weight: 500;
}

/* Valeur principale des métriques (le chiffre) */
[data-testid="stMetric"] p {
    color: #ffffff;
    font-weight: 600;
}

/* Titre principal (H1) avec dégradé */
h1 {
    background: -webkit-linear-gradient(45deg, #00A3FF, #00FFC2 80%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    padding-bottom: 0.5rem;
}

/* Titres de section (H2, H3) */
h2, h3 {
    color: #00A3FF; /* Accent bleu vif pour les sections */
    border-bottom: 1px solid #333;
    padding-bottom: 5px;
    margin-top: 1rem;
}

/* Barre latérale (Sidebar) */
.css-1d3w5iq, .css-1dp5x4y {
    background-color: #151515 !important; /* Plus sombre que le fond pour la séparation */
}

/* Boutons */
.stButton>button {
    border-radius: 8px;
    border: none;
    color: white;
    font-weight: 600;
    padding: 0.5rem 1rem;
    background: linear-gradient(45deg, #007BFF, #00A3FF);
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(0, 163, 255, 0.3);
}
.stButton>button:hover {
    background: linear-gradient(45deg, #00A3FF, #007BFF);
    box-shadow: 0 4px 12px rgba(0, 163, 255, 0.5);
    transform: translateY(-2px);
}

/* Style personnalisé pour les signaux (Succès, Erreur, Avertissement) */
[data-testid="stSuccess"] {
    background-color: rgba(0, 255, 194, 0.1);
    border: 1px solid #00FFC2;
    border-radius: 8px;
    color: #00FFC2; /* Texte Cyan/Vert */
}
[data-testid="stError"] {
    background-color: rgba(255, 71, 71, 0.1);
    border: 1px solid #FF4747;
    border-radius: 8px;
    color: #FF4747; /* Texte Rouge Vif */
}
[data-testid="stWarning"] {
    background-color: rgba(255, 179, 0, 0.1);
    border: 1px solid #FFB300;
    border-radius: 8px;
    color: #FFD700; /* Texte Or/Jaune */
}

/* Masquer le pied de page 'Made with Streamlit' */
footer { visibility: hidden; }
</style>
"""

# --- Configuration et Constantes ---

### MODIFIÉ : Dictionnaire de recherche flexible ###
SEARCH_MAP = {
    # Cryptos (nom complet -> Ticker YFinance)
    "BITCOIN": "BTC-USD",
    "ETHEREUM": "ETH-USD",
    "SOLANA": "SOL-USD",
    "BNB": "BNB-USD",
    "RIPPLE": "XRP-USD",
    "CARDANO": "ADA-USD",
    "DOGECOIN": "DOGE-USD",
    "CHAINLINK": "LINK-USD",
    
    # Actions (nom compagnie -> Ticker YFinance)
    "APPLE": "AAPL",
    "MICROSOFT": "MSFT",
    "GOOGLE": "GOOGL",
    "ALPHABET": "GOOGL",
    "AMAZON": "AMZN",
    "NVIDIA": "NVDA",
    "TESLA": "TSLA",
    "META": "META",
    "FACEBOOK": "META",
    "CAC 40": "^FCHI", # Indice
    "LVMH": "MC.PA", # Ticker Paris
    "TOTAL": "TTE.PA"
}

### MODIFIÉ : Liste pour le Scanner (Mix Actions/Crypto) ###
SCAN_LIST = [
    # Cryptos
    'BTC-USD', 'ETH-USD', 'SOL-USD', 'XRP-USD', 
    'ADA-USD', 'DOGE-USD', 'LINK-USD',
    # Actions US
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META',
    # Actions FR (Indices)
    'MC.PA', 'TTE.PA', '^FCHI'
]

RSI_PERIOD = 14

### MODIFIÉ : Fonction de récupération des données (utilise yfinance) ###
@st.cache_data(ttl=60*5)
def get_ohlcv_data(symbol, timeframe, verbose=True):
    """Récupère les données OHLCV depuis Yahoo Finance."""
    if verbose:
        st.info(f"Connexion à Yahoo Finance pour charger les données {symbol}...")
    
    try:
        ticker_obj = yf.Ticker(symbol)
        
        # Définir la période en fonction de l'intervalle
        # YFinance a des limites de période pour les données intraday
        if 'm' in timeframe or 'h' in timeframe:
            # 15m, 30m, 1h -> 60 derniers jours
            period = '60d'
        else:
            # '1d' -> 2 dernières années
            period = '2y'
            
        df = ticker_obj.history(period=period, interval=timeframe)

        if df.empty:
            if verbose:
                st.error(f"Aucune donnée trouvée pour {symbol} avec l'intervalle {timeframe}.")
                st.error("Essayez un autre symbole (ex: 'AAPL', 'BTC-USD') ou un intervalle ('1d').")
            return pd.DataFrame()

        # Renommage des colonnes (YFinance utilise des majuscules)
        df = df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        
        # S'assurer que les colonnes nécessaires sont présentes
        df = df[['open', 'high', 'low', 'close', 'volume']]
        
        return df
        
    except Exception as e:
        if verbose:
            st.error(f"Erreur de connexion à YFinance ou de récupération des données : {e}")
            st.error("Impossible de charger les données. Vérifiez le symbole (ticker).")
        return pd.DataFrame()
### FIN MODIFIÉ ###


def calculate_indicators(df):
    """Calcule les indicateurs techniques (RSI) pour le DataFrame."""
    if not df.empty:
        df['RSI'] = ta.rsi(df['close'], length=RSI_PERIOD)
        df = df.dropna()
    return df

def check_trading_signal(df, rsi_oversold, rsi_overbought):
    """Vérifie le dernier signal de trading basé sur le RSI."""
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

### MODIFIÉ : Scan_market utilise la nouvelle fonction get_ohlcv_data ###
@st.cache_data(ttl=60*5)
def scan_market(symbols, timeframe, rsi_oversold, rsi_overbought):
    """
    Scanne toutes les paires dans SCAN_LIST pour trouver des signaux.
    """
    st.info(f"Scan en cours de {len(symbols)} symboles (Actions & Cryptos) sur l'intervalle {timeframe}...")
    market_data = []
    
    progress_bar = st.progress(0)
    total_symbols = len(symbols)
    
    for i, symbol in enumerate(symbols):
        # Récupère les données (verbose=False pour éviter les messages en boucle)
        df = get_ohlcv_data(symbol, timeframe, verbose=False) 
        df = calculate_indicators(df)
        
        if not df.empty:
            signal, price, last_rsi = check_trading_signal(df, rsi_oversold, rsi_overbought)
            market_data.append({
                'Symbole': symbol,
                'Prix Actuel': price,
                'RSI': last_rsi,
                'Signal': signal
            })
        else:
            market_data.append({
                'Symbole': symbol,
                'Prix Actuel': 0.0,
                'RSI': 0.0,
                'Signal': 'ERREUR DATA'
            })
        
        progress_bar.progress((i + 1) / total_symbols)
    
    progress_bar.empty() # Cache la barre de progression
    
    # Conversion en DataFrame
    market_df = pd.DataFrame(market_data)
    
    # Tri par RSI (croissant)
    market_df = market_df.sort_values(by='RSI', ascending=True)
    
    return market_df
### FIN MODIFIÉ ###


def run_backtest(df, rsi_oversold, rsi_overbought, start_balance):
    """Exécute un backtest simple basé sur la stratégie RSI."""
    if df.empty:
        return pd.DataFrame(), 0.0, 0.0, 0
    
    df['Signal'] = 0
    df.loc[df['RSI'] < rsi_oversold, 'Signal'] = 1
    df.loc[df['RSI'] > rsi_overbought, 'Signal'] = -1
    
    balance = start_balance 
    position = 0.0
    trade_count = 0
    
    backtest_df = pd.DataFrame(columns=['Date', 'Type', 'Prix', 'Quantité', 'Capital'])

    for index, row in df.iterrows():
        if row['Signal'] == 1 and position == 0:
            amount_to_buy = balance * 0.98 / row['close'] 
            balance -= amount_to_buy * row['close']
            position += amount_to_buy
            trade_count += 1
            backtest_df.loc[len(backtest_df)] = [index.strftime('%Y-%m-%d %H:%M'), 'ACHAT', f"{row['close']:.2f}", amount_to_buy, f"{balance:.2f}"]
            
        elif row['Signal'] == -1 and position > 0:
            balance += position * row['close']
            position = 0.0
            trade_count += 1
            backtest_df.loc[len(backtest_df)] = [index.strftime('%Y-%m-%d %H:%M'), 'VENTE', f"{row['close']:.2f}", 0, f"{balance:.2f}"]

    final_value = balance + (position * df['close'].iloc[-1])
    
    if start_balance > 0:
        profit_percent = ((final_value - start_balance) / start_balance) * 100
    else:
        profit_percent = 0.0
    
    return backtest_df, final_value, profit_percent, trade_count

# --- Interface Streamlit ---

st.set_page_config(layout="wide", page_title="Mon Bot Analyste (Actions & Crypto)", initial_sidebar_state="expanded")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
plt.style.use('dark_background') 

st.title("📈 Bot d'Analyse (Actions & Crypto) & Backtest")
st.caption(f"Données via Yahoo Finance | Dernière mise à jour : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# --- 1. Barre Latérale de Configuration ---
st.sidebar.header("⚙️ Paramètres")

### MODIFIÉ : Barre de recherche ###
st.sidebar.markdown("### 1. Recherche de Symbole")
user_input = st.sidebar.text_input(
    "Rechercher (Nom ou Ticker)", 
    "Bitcoin",
    help="Ex: 'Bitcoin', 'Apple', 'AAPL', 'BTC-USD', 'MC.PA' (LVMH)"
)
# Logique de recherche flexible
# 1. Met en majuscule, 2. Cherche dans le dictionnaire, 3. Si non trouvé, utilise l'input (en majuscule)
selected_symbol = SEARCH_MAP.get(user_input.upper(), user_input.upper())
st.sidebar.info(f"Ticker sélectionné : **{selected_symbol}**")
### FIN MODIFIÉ ###


st.sidebar.markdown("### 2. Paramètres d'Analyse")
# Note : YFinance a des intervalles différents de CCXT
# '15m', '30m', '1h', '1d' sont compatibles
selected_timeframe = st.sidebar.selectbox("Intervalle", ['1h', '1d', '15m', '30m', '4h']) 

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Capital (Prix à mettre)")
user_capital = st.sidebar.number_input(
    "Capital de départ ($/€)", 
    min_value=10.0, 
    value=1000.0, 
    step=50.0,
    help="Entrez le montant que vous souhaitez simuler pour le backtest."
)
st.sidebar.markdown("---")

st.sidebar.subheader("Stratégie RSI")
rsi_oversold = st.sidebar.slider("RSI Survente (Achat)", 10, 40, 30)
rsi_overbought = st.sidebar.slider("RSI Surachat (Vente)", 60, 90, 70)
st.sidebar.info(f"**Achat :** RSI < {rsi_oversold} | **Vente :** RSI > {rsi_overbought}")

# --- 2. Récupération et Analyse ---
df = get_ohlcv_data(selected_symbol, selected_timeframe, verbose=True) 
df = calculate_indicators(df)

if not df.empty:
    signal, price, last_rsi = check_trading_signal(df, rsi_oversold, rsi_overbought)
    
    st.header(f"Analyse Détaillée : {selected_symbol}")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Symbole / Intervalle", f"{selected_symbol} / {selected_timeframe}")
    col2.metric("Prix Actuel", f"${price:,.2f}") ### MODIFIÉ : Formatage prix
    col3.metric(f"RSI ({RSI_PERIOD})", f"{last_rsi:.2f}")
    
    if signal == 'ACHAT FORT':
        col4.success(f"SIGNAL : {signal}")
    elif signal == 'VENTE/CLÔTURE':
        col4.error(f"SIGNAL : {signal}")
    else:
        col4.warning(f"SIGNAL : {signal}")
        
    st.markdown("---")
    
    ### MODIFIÉ : Section Scanner (utilise SCAN_LIST) ###
    st.header("🔍 Pronostic du Marché (Scanner)")
    st.caption(f"Analyse de {len(SCAN_LIST)} symboles (Actions & Cryptos) sur l'intervalle {selected_timeframe}.")

    market_scan_df = scan_market(
        SCAN_LIST, 
        selected_timeframe, 
        rsi_oversold, 
        rsi_overbought
    )
    
    formatted_scan_df = market_scan_df.copy()
    formatted_scan_df['Prix Actuel'] = formatted_scan_df['Prix Actuel'].map('${:,.2f}'.format)
    formatted_scan_df['RSI'] = formatted_scan_df['RSI'].map('{:.2f}'.format)
    
    st.dataframe(
        formatted_scan_df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Symbole": st.column_config.TextColumn("Symbole", width="small"),
            "Prix Actuel": st.column_config.TextColumn("Prix Actuel", width="medium"),
            "RSI": st.column_config.TextColumn("RSI", width="small"),
            "Signal": st.column_config.TextColumn("Signal", width="medium"),
        }
    )
    st.markdown("---")
    ### FIN MODIFIÉ ###

    # --- 3. Backtesting et Performance (pour l'actif sélectionné) ---
    st.header(f"Backtesting de la Stratégie sur {selected_symbol}")
    
    backtest_df, final_value, profit_percent, trade_count = run_backtest(
        df.copy(), 
        rsi_oversold, 
        rsi_overbought, 
        user_capital
    )
    
    start_date = df.index.min()
    end_date = df.index.max()
    duration_timedelta = end_date - start_date
    total_hours = duration_timedelta.total_seconds() / 3600
    total_profit = final_value - user_capital
    avg_hourly_gain = total_profit / total_hours if total_hours > 0 else 0.0
    
    col_a, col_b, col_c, col_d, col_e = st.columns(5)
    
    col_a.metric("Capital Initial", f"${user_capital:,.2f}") 
    col_b.metric("Valeur Finale", f"${final_value:,.2f}", delta=f"{profit_percent:.2f}%")
    
    gain_delta_color = "normal"
    if total_profit < 0:
        gain_delta_color = "inverse"
        
    col_c.metric(
        "Potentiel de Gain (Net)", 
        f"${total_profit:,.2f}", 
        delta_color=gain_delta_color,
        help="Ceci est le gain (ou la perte) net en dollars/euros sur la période de simulation."
    )
    
    col_d.metric("Nombre de Trades", trade_count)
    col_e.metric(
        "Gain Moyen / Heure", 
        f"${avg_hourly_gain:.4f}", 
        help=f"Basé sur un gain total de ${total_profit:.2f} sur une période de {total_hours:.1f} heures."
    )

    st.subheader("Historique des Transactions")
    st.dataframe(backtest_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # --- 4. Visualisation Graphique (pour l'actif sélectionné) ---
    st.header(f"Graphiques d'Analyse Technique pour {selected_symbol}")
    
    # 4.1 Graphique du Prix
    fig_price, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(df.index, df['close'], label='Prix de Clôture', color='#4CAF50') 
    ax1.set_title(f"Prix de Clôture ({selected_timeframe})", fontsize=14, color='white')
    ax1.set_ylabel("Prix ($/€)", color='white') ### MODIFIÉ : Label Y
    ax1.tick_params(axis='y', labelcolor='white')
    ax1.tick_params(axis='x', labelcolor='white')
    ax1.grid(True, color='#444444')
    st.pyplot(fig_price)
    plt.close(fig_price)
    
    # 4.2 Graphique du RSI (Inchangé)
    fig_rsi, ax2 = plt.subplots(figsize=(10, 3))
    ax2.plot(df.index, df['RSI'], label='RSI (14)', color='cyan')
    ax2.axhline(rsi_overbought, color='red', linestyle='--', label=f'Surachat ({rsi_overbought})')
    ax2.axhline(rsi_oversold, color='green', linestyle='--', label=f'Survente ({rsi_oversold})')
    ax2.set_title("Indice de Force Relative (RSI)", fontsize=14, color='white')
    ax2.set_ylim(0, 100)
    ax2.legend(loc='lower left', frameon=True, facecolor='#2b2b2b', edgecolor='none', labelcolor='white')
    ax2.tick_params(axis='y', labelcolor='white')
    ax2.tick_params(axis='x', labelcolor='white')
    ax2.grid(True, color='#444444')
    st.pyplot(fig_rsi)
    plt.close(fig_rsi)

    # 4.3 Graphique du Volume (Inchangé)
    fig_volume, ax3 = plt.subplots(figsize=(10, 3))
    ax3.bar(df.index, df['volume'], color='#FFA500', alpha=0.6) 
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
    
    ax_forecast.plot(df.index, df['close'], label='Prix de Clôture Historique', color='#4CAF50', alpha=0.7)

    last_close = df['close'].iloc[-1]
    last_timestamp = df.index[-1]

    # Logique de delta temps (doit gérer les DataFrames YFinance)
    try:
        # Tente de déduire la fréquence (meilleure méthode)
        time_delta = pd.to_timedelta(pd.infer_freq(df.index))
    except (TypeError, ValueError):
        # Si échec (intervalles irréguliers ?), utilise la différence moyenne
        if len(df.index) > 1:
            time_delta = (df.index[-1] - df.index[0]) / (len(df.index) - 1)
        else:
            # Fallback si 1 seule donnée
             time_delta = datetime.timedelta(hours=1)
    
    future_timestamps = [last_timestamp + (time_delta * (i + 1)) for i in range(10)]
    forecast_prices = [last_close]

    # Le pronostic est basé sur une simple extrapolation, à ne pas prendre comme conseil financier
    if signal == 'ACHAT FORT':
        change_factor = 1 + (last_rsi / 10000) # Petite hausse
        forecast_color = 'magenta'
        forecast_label = 'Pronostic : Hausse'
    elif signal == 'VENTE/CLÔTURE':
        change_factor = 1 - ((100-last_rsi) / 10000) # Petite baisse
        forecast_color = 'magenta'
        forecast_label = 'Pronostic : Baisse'
    else: # NEUTRE
        change_factor = 1.0
        forecast_color = 'yellow'
        forecast_label = 'Pronostic : Neutre'

    for i in range(10):
        # Simule une légère variation basée sur le signal
        forecast_prices.append(forecast_prices[-1] * (change_factor + np.random.normal(0, 0.0001)))

    plot_timestamps = [last_timestamp] + future_timestamps
    
    ax_forecast.plot(plot_timestamps, forecast_prices, 
                     label=forecast_label, 
                     color=forecast_color, 
                     linestyle='--', 
                     marker='o', 
                     markersize=4) 
    
    ax_forecast.plot(last_timestamp, last_close, 'o', color='white', markersize=6, label='Point de départ du pronostic')

    ax_forecast.set_title("Pronostic du Prix basés sur le RSI", fontsize=14, color='white')
    ax_forecast.set_ylabel("Prix ($/€)", color='white')
    ax_forecast.tick_params(axis='y', labelcolor='white')
    ax_forecast.tick_params(axis='x', labelcolor='white')
    ax_forecast.grid(True, color='#444444')
    ax_forecast.legend(loc='upper left', frameon=True, facecolor='#2b2b2b', edgecolor='none', labelcolor='white')
    st.pyplot(fig_forecast)
    plt.close(fig_forecast)

else:
    st.error("Impossible de charger les données pour le symbole sélectionné. Vérifiez votre saisie ou l'intervalle.")

if st.button('🔄 Rafraîchir les Données'):
    st.cache_data.clear()
    st.rerun()

