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

# CSS Grigio Chiaro Professionale
st.markdown("""
    <style>
    .stApp { background-color: #F5F5F5; }
    .streamlit-expanderHeader { 
        background-color: white !important; 
        border-radius: 8px; 
        border: 1px solid #E0E0E0; 
    }
    .streamlit-expanderContent { background-color: white !important; }
    div[data-testid="stForm"] { background-color: white !important; border-radius: 10px; padding: 20px; }
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
        
        # Filtri nella Sidebar (solo per la sezione Archivio)
        st.sidebar.markdown("---")
        st.sidebar.subheader("FILTRI")
        
        # Filtro per Brand
        lista_brand = ["TUTTI"] + sorted(df['Brand'].dropna().unique().tolist())
        filtro_brand = st.sidebar.selectbox("Filtra per Marca", lista_brand)
        
        search = st.sidebar.text_input("Cerca parola chiave...")

        # Applicazione Filtri
        df_display = df.copy()
        # Reset della pagina se i record filtrati sono meno di quelli necessari per la pagina attuale
        if totale_record <= inizio:
            st.session_state.pagina_attuale = 0
        if filtro_brand != "TUTTI":
            df_display = df_display[df_display['Brand'] == filtro_brand]
        
        if search:
            df_display = df_display[df_display.apply(lambda r: search.lower() in r.astype(str).str.lower().values, axis=1)]

        # --- LOGICA DI PAGINAZIONE ---
        record_per_pagina = 10
        if "pagina_attuale" not in st.session_state:
            st.session_state.pagina_attuale = 0

        totale_record = len(df_display)
        num_pagine = (totale_record // record_per_pagina) + (1 if totale_record % record_per_pagina > 0 else 0)

        # Navigazione pagine
        col_prev, col_page, col_next = st.columns([1, 2, 1])
        if col_prev.button("⬅️ Precedente") and st.session_state.pagina_attuale > 0:
            st.session_state.pagina_attuale -= 1
            st.rerun()
        
        col_page.markdown(f"<p style='text-align: center;'>Pagina {st.session_state.pagina_attuale + 1} di {max(1, num_pagine)}</p>", unsafe_allow_html=True)
        
        if col_next.button("Successivo ➡️") and st.session_state.pagina_attuale < num_pagine - 1:
            st.session_state.pagina_attuale += 1
            st.rerun()

        # Selezione dei record da mostrare
        inizio = st.session_state.pagina_attuale * record_per_pagina
        fine = inizio + record_per_pagina
        
        # Mostriamo i record (ordinati dal più recente)
        df_paginato = df_display.sort_index(ascending=False).iloc[inizio:fine]

        for i, row in df_paginato.iterrows():
            u_key = f"{i}_{row['Data']}".replace(" ", "").replace("/", "").replace(":", "")
            
            with st.expander(f"📝 {row['Brand']} {row['Modello']} - {row['Data']}"):
                # ... QUI INSERISCI TUTTO IL TUO CODICE DEI TAB (MODIFICA/ELIMINA/FOTO) ...
                # (Mantieni pure il codice che avevi già scritto per la visualizzazione interna)
                st.info(f"**Motore:** {row['Motore']} | **Sintomo:** {row['Sintomo']}")
                st.success(f"**Soluzione:** {row['Soluzione']}")
                
                # Gestione foto (quella che hai già)
                p_db = str(row.get('Allegato', ""))
                if p_db and p_db != "nan" and p_db.strip() != "":
                    if os.path.exists(p_db):
                        st.image(p_db, width=400)