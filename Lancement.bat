@echo off
ECHO Lancement du Bot d'Analyse Crypto (Streamlit)...
ECHO Ceci va ouvrir une fenetre de navigateur web.

REM --- COMMANDE DE LANCEMENT DU BOT ---
REM Nous utilisons la methode par module, la plus fiable sur Windows.
python -m streamlit run app.py

ECHO Lancement terminé. Fermez cette fenetre pour arreter le bot.
PAUSE