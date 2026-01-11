import streamlit as st
import pandas as pd
import os
import dropbox
from datetime import datetime

# --- 1. CONFIGURAZIONE SICUREZZA E DROPBOX ---
# Sostituisci con il tuo Token o usa st.secrets per maggiore sicurezza
DROPBOX_TOKEN = st.secrets["DROPBOX_TOKEN"]
PASSWORD_OFFICINA = "Agapiru2012" # Cambiala!

def salva_su_dropbox(file_locali):
    """Invia i file al tuo Dropbox"""
    try:
        dbx = dropbox.Dropbox(DROPBOX_TOKEN)
        for percorso_locale in file_locali:
            if os.path.exists(percorso_locale):
                nome_file_dbx = "/" + os.path.basename(percorso_locale)
                with open(percorso_locale, "rb") as f:
                    dbx.files_upload(f.read(), nome_file_dbx, mode=dropbox.files.WriteMode.overwrite)
        return True
    except Exception as e:
        st.error(f"Errore sincronizzazione Dropbox: {e}")
        return False

# --- 2. PROTEZIONE ACCESSO ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        with st.container():
            st.title("🛠 ELETTROBAR WEB")
            pwd = st.text_input("Inserisci Password Officina", type="password")
            if st.button("Accedi"):
                if pwd == PASSWORD_OFFICINA:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("Password errata")
        return False
    return True

if check_password():
    # --- 3. CONFIGURAZIONE AMBIENTE ---
    st.set_page_config(page_title="ELETTROBAR 1.0", layout="wide")
    DB_NOME = "diario_officina.csv"
    ALLEGATI_DIR = "allegati"

    if not os.path.exists(ALLEGATI_DIR): os.makedirs(ALLEGATI_DIR)
    if not os.path.exists(DB_NOME):
        pd.DataFrame(columns=['Data', 'Brand', 'Modello', 'Motore', 'Sintomo', 'Diagnosi', 'Soluzione', 'Note', 'Allegato']).to_csv(DB_NOME, index=False)

    st.sidebar.title("MENU")
    menu = st.sidebar.radio("Vai a:", ["Nuovo Intervento", "Archivio Storico"])

    # --- 4. NUOVO INTERVENTO ---
    if menu == "Nuovo Intervento":
        st.header("📝 Nuova Scheda Tecnica")
        with st.form("form_lavoro", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            brand = c1.text_input("Brand").upper()
            modello = c2.text_input("Modello")
            motore = c3.text_input("Codice Motore")
            
            sintomo = st.text_area("Sintomo / Difetto")
            soluzione = st.text_area("Soluzione")
            file = st.file_uploader("Allega foto", type=['png', 'jpg', 'jpeg'])
            
            if st.form_submit_button("SALVA E SINCRONIZZA"):
                if brand and modello:
                    path_file = ""
                    if file:
                        path_file = os.path.join(ALLEGATI_DIR, file.name)
                        with open(path_file, "wb") as f:
                            f.write(file.getbuffer())
                    
                    nuovo = pd.DataFrame([{
                        'Data': datetime.now().strftime("%d/%m/%Y %H:%M"),
                        'Brand': brand, 'Modello': modello, 'Motore': motore,
                        'Sintomo': sintomo, 'Soluzione': soluzione, 'Allegato': path_file
                    }])
                    
                    df = pd.read_csv(DB_NOME)
                    df = pd.concat([df, nuovo], ignore_index=True)
                    df.to_csv(DB_NOME, index=False)
                    
                    # Sincronizzazione Dropbox
                    file_da_caricare = [DB_NOME]
                    if path_file: file_da_caricare.append(path_file)
                    
                    if salva_su_dropbox(file_da_caricare):
                        st.success("✅ Salvato e Sincronizzato su Dropbox!")
                else:
                    st.warning("Brand e Modello obbligatori.")

    # --- 5. ARCHIVIO ---
    else:
        st.header("🔍 Archivio Storico")
        df = pd.read_csv(DB_NOME)
        
        search = st.text_input("Cerca per Brand, Modello o Sintomo...")
        if search:
            df = df[df.apply(lambda r: search.lower() in r.astype(str).str.lower().values, axis=1)]

        # Visualizziamo dal più recente
        for i, row in df.sort_index(ascending=False).iterrows():
            with st.expander(f"📝 {row['Brand']} {row['Modello']} - {row['Data']}"):
                
                # CREIAMO IL FORM DI MODIFICA
                with st.form(f"form_edit_{i}"):
                    st.subheader("Modifica Intervento")
                    c1, c2, c3 = st.columns(3)
                    new_brand = c1.text_input("Brand", value=row['Brand']).upper()
                    new_modello = c2.text_input("Modello", value=row['Modello'])
                    new_motore = c3.text_input("Motore", value=row['Motore'])
                    
                    new_sintomo = st.text_area("Sintomo / Difetto", value=row['Sintomo'])
                    new_soluzione = st.text_area("Soluzione Tecninca", value=row['Soluzione'])
                    
                    # Bottone per salvare le modifiche
                    if st.form_submit_button("💾 SALVA MODIFICHE"):
                        df.at[i, 'Brand'] = new_brand
                        df.at[i, 'Modello'] = new_modello
                        df.at[i, 'Motore'] = new_motore
                        df.at[i, 'Sintomo'] = new_sintomo
                        df.at[i, 'Soluzione'] = new_soluzione
                        
                        df.to_csv(DB_NOME, index=False)
                        salva_su_dropbox([DB_NOME])
                        st.success("Modifica salvata!")
                        st.rerun()

                # Visualizzazione Foto e tasto Elimina (fuori dal form di modifica)
                st.write("---")
                col_foto, col_del = st.columns([3, 1])
                
                with col_foto:
                    if row['Allegato'] and os.path.exists(row['Allegato']):
                        with open(row['Allegato'], "rb") as f:
                            st.image(f.read(), caption="Foto allegata", width=300)
                
                with col_del:
                    if st.button("🗑️ ELIMINA RECORD", key=f"del_{i}"):
                        df = df.drop(i)
                        df.to_csv(DB_NOME, index=False)
                        salva_su_dropbox([DB_NOME])
                        st.warning("Record eliminato.")
                        st.rerun()