import pandas as pd
import os
import streamlit as st

CSV_FILE = "casos.csv"

@st.cache_data
def carregar_csv():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    return pd.DataFrame(columns=[
        "Exemplos de ocorridos nos reports (Falas/Chats)",
        "Punição aplicada",
        "Assinante?"
    ])

def salvar_feedback(texto, punicao):
    arquivo_treino = "treinamento.csv"
    novo_dado = pd.DataFrame([{
        "Exemplos de ocorridos nos reports (Falas/Chats)": texto,
        "Punição aplicada": punicao
    }])
    if os.path.exists(arquivo_treino):
        novo_dado.to_csv(arquivo_treino, mode='a', header=False, index=False)
    else:
        novo_dado.to_csv(arquivo_treino, index=False)