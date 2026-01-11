import streamlit as st
import pandas as pd
import os
from datetime import datetime

# --- 1. PROTEZIONE ACCESSO ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "Agapiru2012": # Cambiala con una tua
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Inserisci Password Officina", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password errata, riprova", type="password", on_change=password_entered, key="password")
        st.error("😕 Password non corretta")
        return False
    else:
        return True

if check_password():
    # --- 2. CONFIGURAZIONE E SETUP ---
    st.set_page_config(page_title="OFFICINA DIGITALE 1.3", layout="wide")
    DB_NOME = "diario_officina.csv"
    ALLEGATI_DIR = "allegati"

    if not os.path.exists(ALLEGATI_DIR):
        os.makedirs(ALLEGATI_DIR)

    if not os.path.exists(DB_NOME):
        df = pd.DataFrame(columns=['Data', 'Brand', 'Modello', 'Motore', 'Sintomo', 'Diagnosi', 'Soluzione', 'Note', 'Allegato'])
        df.to_csv(DB_NOME, index=False)

    # --- 3. BARRA LATERALE ---
    st.sidebar.title("🛠 DIARIO OFFICINA")
    menu = st.sidebar.radio("Navigazione", ["Inserisci Intervento", "Archivio Storico"])

    # --- 4. LOGICA INSERIMENTO ---
    if menu == "Inserisci Intervento":
        st.header("📝 Nuova Scheda Tecnica")
        with st.form("form_lavoro", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            brand = c1.text_input("Brand").upper()
            modello = c2.text_input("Modello")
            motore = c3.text_input("Codice Motore")
            
            sintomo = st.text_area("Sintomo / Difetto riscontrato")
            diagnosi = st.text_area("Diagnosi")
            soluzione = st.text_area("Riparazione / Soluzione")
            note = st.text_area("Note Extra")
            
            file = st.file_uploader("Allega foto o documenti", type=['png', 'jpg', 'jpeg', 'pdf'])
            
            if st.form_submit_button("SALVA IN ARCHIVIO"):
                if brand and modello:
                    path_file = ""
                    if file:
                        path_file = os.path.join(ALLEGATI_DIR, file.name)
                        with open(path_file, "wb") as f:
                            f.write(file.getbuffer())
                    
                    nuovo = pd.DataFrame([{
                        'Data': datetime.now().strftime("%d/%m/%Y %H:%M"),
                        'Brand': brand, 'Modello': modello, 'Motore': motore,
                        'Sintomo': sintomo, 'Diagnosi': diagnosi, 'Soluzione': soluzione,
                        'Note': note, 'Allegato': path_file
                    }])
                    
                    df = pd.read_csv(DB_NOME)
                    df = pd.concat([df, nuovo], ignore_index=True)
                    df.to_csv(DB_NOME, index=False)
                    st.success(f"Intervento su {brand} salvato correttamente!")
                else:
                    st.warning("Brand e Modello sono necessari.")

    # --- 5. LOGICA RICERCA E MODIFICA ---
    else:
        st.header("🔍 Consulta Archivio")
        df = pd.read_csv(DB_NOME)
        
        search = st.text_input("Cerca parola chiave...")
        if search:
            mask = df.apply(lambda r: search.lower() in r.astype(str).str.lower().values, axis=1)
            df_display = df[mask]
        else:
            df_display = df

        for i, row in df_display.sort_index(ascending=False).iterrows():
            with st.expander(f"🚗 {row['Brand']} {row['Modello']} - {row['Data']}"):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    st.write(f"**Motore:** {row['Motore']}")
                    st.write(f"**Sintomo:** {row['Sintomo']}")
                    st.success(f"**Soluzione:** {row['Soluzione']}")
                    st.write(f"*Note:* {row['Note']}")
                with col_b:
                    if row['Allegato'] and os.path.exists(row['Allegato']):
                        st.image(row['Allegato']) # Se è una foto la vedi subito
                    
                    # Tasto per eliminare (attenzione!)
                    if st.button("Elimina Record", key=f"del_{i}"):
                        df = df.drop(i)
                        df.to_csv(DB_NOME, index=False)
                        st.rerun()