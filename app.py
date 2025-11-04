import streamlit as st
import ccxt
import pandas as pd
import pandas_ta as ta
import datetime
import matplotlib.pyplot as plt
import numpy as np 

# --- 1. Custom CSS pour un Design "Fintech Moderne" ---
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
AVAILABLE_SYMBOLS = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 
    'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'LINK/USDT'
]
EXCHANGE = ccxt.coinbase() 
RSI_PERIOD = 14

@st.cache_data(ttl=60*5)
def get_ohlcv_data(symbol, timeframe):
    st.info(f"Connexion à l'exchange pour charger les données {symbol}...")
    try:
        ohlcv = EXCHANGE.fetch_ohlcv(symbol, timeframe, limit=500)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df = df.set_index('timestamp')
        return df
    except Exception as e:
        st.error(f"Erreur de connexion à l'exchange ou de récupération des données : {e}")
        st.error("Impossible de charger les données. Veuillez vérifier l'exchange ou la paire sélectionnée.")
        return pd.DataFrame()

def calculate_indicators(df):
    if not df.empty:
        df['RSI'] = ta.rsi(df['close'], length=RSI_PERIOD)
        df = df.dropna()
    return df

def check_trading_signal(df, rsi_oversold, rsi_overbought):
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

def run_backtest(df, rsi_oversold, rsi_overbought, start_balance):
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

st.set_page_config(layout="wide", page_title="Mon Bot Analyste Crypto", initial_sidebar_state="expanded")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True) # Injecte le CSS personnalisé

# Changement de style Matplotlib pour correspondre au thème sombre
plt.style.use('dark_background') 

st.title("💰 Bot d'Analyse Crypto (RSI) & Backtest")
st.caption(f"Dernière mise à jour : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# --- 1. Barre Latérale de Configuration ---
st.sidebar.header("⚙️ Paramètres")
selected_symbol = st.sidebar.selectbox("Paire Crypto", AVAILABLE_SYMBOLS)
selected_timeframe = st.sidebar.selectbox("Intervalle", ['15m', '30m', '1h', '4h', '1d']) 

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Capital (Prix à mettre)")
user_capital = st.sidebar.number_input(
    "Capital de départ (USDT)", 
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
df = get_ohlcv_data(selected_symbol, selected_timeframe)
df = calculate_indicators(df)

if not df.empty:
    signal, price, last_rsi = check_trading_signal(df, rsi_oversold, rsi_overbought)
    
    st.header("Analyse en Temps Réel")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Paire / Intervalle", f"{selected_symbol} / {selected_timeframe}")
    col2.metric("Prix Actuel", f"${price:.2f}")
    col3.metric(f"RSI ({RSI_PERIOD})", f"{last_rsi:.2f}")
    
    # Affichage du Signal (utilise les styles CSS personnalisés)
    if signal == 'ACHAT FORT':
        col4.success(f"SIGNAL : {signal}")
    elif signal == 'VENTE/CLÔTURE':
        col4.error(f"SIGNAL : {signal}")
    else:
        col4.warning(f"SIGNAL : {signal}")
        
    st.markdown("---")
    
    # --- 3. Backtesting et Performance ---
    st.header("Backtesting de la Stratégie")
    
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
    
    col_a.metric("Capital Initial", f"${user_capital:.2f}") 
    col_b.metric("Valeur Finale", f"${final_value:.2f}", delta=f"{profit_percent:.2f}%")
    
    gain_delta_color = "normal"
    if total_profit < 0:
        gain_delta_color = "inverse"
        
    col_c.metric(
        "Potentiel de Gain (USD)", 
        f"${total_profit:.2f}", 
        delta_color=gain_delta_color,
        help="Ceci est le gain (ou la perte) net en dollars sur la période de simulation."
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

    # --- 4. Visualisation Graphique ---
    st.header(f"Graphiques d'Analyse Technique pour {selected_symbol}")
    
    # 4.1 Graphique du Prix
    fig_price, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(df.index, df['close'], label='Prix de Clôture', color='#4CAF50') # Vert
    ax1.set_title(f"Prix de Clôture ({selected_timeframe})", fontsize=14, color='white')
    ax1.set_ylabel("Prix (USDT)", color='white')
    ax1.tick_params(axis='y', labelcolor='white')
    ax1.tick_params(axis='x', labelcolor='white')
    ax1.grid(True, color='#444444')
    st.pyplot(fig_price)
    plt.close(fig_price)
    
    # 4.2 Graphique du RSI
    fig_rsi, ax2 = plt.subplots(figsize=(10, 3))
    ax2.plot(df.index, df['RSI'], label='RSI (14)', color='cyan') # Cyan
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

    # 4.3 Graphique du Volume
    fig_volume, ax3 = plt.subplots(figsize=(10, 3))
    ax3.bar(df.index, df['volume'], color='#FFA500', alpha=0.6) # Orange
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

    if 'm' in selected_timeframe:
        delta_unit = int(selected_timeframe.replace('m', ''))
        time_delta = datetime.timedelta(minutes=delta_unit)
    elif 'h' in selected_timeframe:
        delta_unit = int(selected_timeframe.replace('h', ''))
        time_delta = datetime.timedelta(hours=delta_unit)
    elif 'd' in selected_timeframe:
        delta_unit = int(selected_timeframe.replace('d', ''))
        time_delta = datetime.timedelta(days=delta_unit)
    else:
        time_delta = datetime.timedelta(hours=1) 
    
    future_timestamps = [last_timestamp + (time_delta * (i + 1)) for i in range(10)]
    forecast_prices = [last_close]

    if signal == 'ACHAT FORT':
        for i in range(10):
            forecast_prices.append(forecast_prices[-1] * (1 + 0.001 * (1 + i/20))) 
        forecast_color = 'magenta'
        forecast_label = 'Pronostic : Hausse'
    elif signal == 'VENTE/CLÔTURE':
        for i in range(10):
            forecast_prices.append(forecast_prices[-1] * (1 - 0.001 * (1 + i/20))) 
        forecast_color = 'magenta'
        forecast_label = 'Pronostic : Baisse'
    else: # NEUTRE
        forecast_prices.extend([last_close] * 10)
        forecast_color = 'yellow'
        forecast_label = 'Pronostic : Neutre'

    plot_timestamps = [last_timestamp] + future_timestamps
    
    ax_forecast.plot(plot_timestamps, forecast_prices, 
                     label=forecast_label, 
                     color=forecast_color, 
                     linestyle='--', 
                     marker='o', 
                     markersize=4) 
    
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