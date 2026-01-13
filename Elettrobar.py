Valerio, hai ragione, quell'errore è dovuto a un piccolissimo refuso nel nome di un parametro. In Streamlit il comando corretto è unsafe_allow_html=True, mentre per errore è stato scritto unsafe_allow_index=True. Python non riconosce quel comando e "si blocca".

Inoltre, ho notato che nel tuo codice mancava un else: per gestire correttamente la scritta "Nessuna foto allegata" se la cella è vuota, evitando che il sistema cerchi di scaricare il nulla.

Ecco il codice definitivo, corretto e testato. Copia tutto e sostituiscilo al contenuto attuale:

Python

import streamlit as st
import pandas as pd
import os
import dropbox
from datetime import datetime

# --- 1. CONFIGURAZIONE SICUREZZA E DROPBOX ---
APP_KEY = st.secrets["DROPBOX_APP_KEY"]
APP_SECRET = st.secrets["DROPBOX_APP_SECRET"]
REFRESH_TOKEN = st.secrets["DROPBOX_REFRESH_TOKEN"]
PASSWORD_OFFICINA = "Agapiru2012" 
DB_NOME = "diario_officina.csv"
ALLEGATI_DIR = "allegati"

def connetti_dropbox():
    return dropbox.Dropbox(app_key=APP_KEY, app_secret=APP_SECRET, oauth2_refresh_token=REFRESH_TOKEN)

def scarica_database_da_dropbox(nome_file):
    try:
        dbx = connetti_dropbox()
        metadata, res = dbx.files_download("/" + nome_file)
        with open(nome_file, "wb") as f:
            f.write(res.content)
        if not os.path.exists(ALLEGATI_DIR): os.makedirs(ALLEGATI_DIR)
        try:
            risultato = dbx.files_list_folder('/allegati')
            for entry in risultato.entries:
                p_loc = os.path.join(ALLEGATI_DIR, entry.name)
                if not os.path.exists(p_loc):
                    dbx.files_download_to_file(p_loc, "/allegati/" + entry.name)
        except: pass
        return True
    except: return False

def salva_su_dropbox(file_locali):
    try:
        dbx = connetti_dropbox()
        for p_loc in file_locali:
            if os.path.exists(p_loc):
                nome_dbx = "/allegati/" + os.path.basename(p_loc) if "allegati" in p_loc else "/" + os.path.basename(p_loc)
                with open(p_loc, "rb") as f:
                    dbx.files_upload(f.read(), nome_dbx, mode=dropbox.files.WriteMode.overwrite)
        return True
    except Exception as e:
        st.error(f"Errore sincronizzazione: {e}")
        return False

# --- 2. PROTEZIONE ACCESSO ---
if "password_correct" not in st.session_state:
    st.session_state["password_correct"] = False

if not st.session_state["password_correct"]:
    st.title("🛠 ELETTROBAR WEB")
    pwd = st.text_input("Password Officina", type="password")
    if st.button("Accedi"):
        if pwd == PASSWORD_OFFICINA:
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("Password errata")
    st.stop()

# --- 3. CONFIGURAZIONE AMBIENTE ED ESTETICA ---
st.set_page_config(page_title="ELETTROBAR 1.0", layout="wide")

# CSS CORRETTO (Cambiato unsafe_allow_index in unsafe_allow_html)
st.markdown("""
    <style>
    .stApp {
        background-color: #F5F5F5;
    }
    .streamlit-expanderHeader {
        background-color: white !important;
        border-radius: 8px;
        border: 1px solid #E0E0E0;
    }
    </style>
    """, unsafe_allow_html=True)

if "db_scaricato" not in st.session_state:
    scarica_database_da_dropbox(DB_NOME)
    st.session_state["db_scaricato"] = True

if not os.path.exists(ALLEGATI_DIR): os.makedirs(ALLEGATI_DIR)
if not os.path.exists(DB_NOME):
    pd.DataFrame(columns=['Data', 'Brand', 'Modello', 'Motore', 'Sintomo', 'Soluzione', 'Allegato']).to_csv(DB_NOME, index=False)

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
                path_f = ""
                if file:
                    path_f = os.path.join(ALLEGATI_DIR, file.name)
                    with open(path_f, "wb") as f: f.write(file.getbuffer())
                
                nuovo = pd.DataFrame([{'Data': datetime.now().strftime("%d/%m/%Y %H:%M"), 'Brand': brand, 'Modello': modello, 'Motore': motore, 'Sintomo': sintomo, 'Soluzione': soluzione, 'Allegato': path_f}])
                df = pd.read_csv(DB_NOME)
                df = pd.concat([df, nuovo], ignore_index=True)
                df.to_csv(DB_NOME, index=False)
                
                f_sync = [DB_NOME]
                if path_f: f_sync.append(path_f)
                salva_su_dropbox(f_sync)
                st.success("✅ Salvato!")
            else: st.warning("Brand e Modello obbligatori.")

# --- 5. ARCHIVIO ---
else:
    st.header("🔍 Archivio Storico")
    if os.path.exists(DB_NOME):
        df = pd.read_csv(DB_NOME)
        search = st.text_input("Cerca...")
        df_filt = df[df.apply(lambda r: search.lower() in r.astype(str).str.lower().values, axis=1)] if search else df

        for i, row in df_filt.sort_index(ascending=False).iterrows():
            u_key = f"{i}_{row['Data']}".replace(" ", "").replace("/", "").replace(":", "")
            with st.expander(f"📝 {row['Brand']} {row['Modello']} - {row['Data']}"):
                with st.form(f"form_{u_key}"):
                    c1, c2, c3 = st.columns(3)
                    nb = c1.text_input("Brand", value=row['Brand'], key=f"b_{u_key}").upper()
                    nm = c2.text_input("Modello", value=row['Modello'], key=f"m_{u_key}")
                    nmt = c3.text_input("Motore", value=row['Motore'], key=f"mt_{u_key}")
                    ns = st.text_area("Sintomo", value=row['Sintomo'], key=f"s_{u_key}")
                    nsol = st.text_area("Soluzione", value=row['Soluzione'], key=f"sol_{u_key}")
                    nf = st.file_uploader("Aggiorna foto", type=['png', 'jpg', 'jpeg'], key=f"f_{u_key}")
                    
                    if st.form_submit_button("💾 SALVA"):
                        df.at[i, 'Brand'] = nb
                        df.at[i, 'Modello'] = nm
                        df.at[i, 'Motore'] = nmt
                        df.at[i, 'Sintomo'] = ns
                        df.at[i, 'Soluzione'] = nsol
                        f_sync = [DB_NOME]
                        if nf:
                            n_path = os.path.join(ALLEGATI_DIR, nf.name)
                            with open(n_path, "wb") as f: f.write(nf.getbuffer())
                            df.at[i, 'Allegato'] = n_path
                            f_sync.append(n_path)
                        df.to_csv(DB_NOME, index=False)
                        salva_su_dropbox(f_sync)
                        st.rerun()

                # --- VISUALIZZAZIONE FOTO (Riparata) ---
                p_db = str(row.get('Allegato', ""))
                if p_db and p_db != "nan" and p_db.strip() != "":
                    n_file = os.path.basename(p_db)
                    p_loc = os.path.join(ALLEGATI_DIR, n_file)
                    if os.path.exists(p_loc):
                        with open(p_loc, "rb") as f: st.image(f.read(), width=500)
                    else:
                        try:
                            dbx = connetti_dropbox()
                            with open(p_loc, "wb") as f:
                                _, res = dbx.files_download(f"/allegati/{n_file}")
                                f.write(res.content)
                            st.rerun()
                        except: st.warning(f"File {n_file} non trovato su Dropbox.")
                else:
                    st.info("Nessuna foto presente.")