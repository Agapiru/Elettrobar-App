import streamlit as st
import pandas as pd
import os
import dropbox
from datetime import datetime

# --- 1. CONFIGURAZIONE SICUREZZA E DROPBOX ---
# Recuperiamo le credenziali dai Secrets (Assicurati di averle inserite in Streamlit Cloud!)
APP_KEY = st.secrets["DROPBOX_APP_KEY"]
APP_SECRET = st.secrets["DROPBOX_APP_SECRET"]
REFRESH_TOKEN = st.secrets["DROPBOX_REFRESH_TOKEN"]
PASSWORD_OFFICINA = "Agapiru2012" 

def connetti_dropbox():
    """Crea una connessione eterna usando il Refresh Token"""
    return dropbox.Dropbox(
        app_key=APP_KEY,
        app_secret=APP_SECRET,
        oauth2_refresh_token=REFRESH_TOKEN
    )

def scarica_database_da_dropbox(nome_file):
    try:
        dbx = connetti_dropbox()
        
        # Scarica il CSV
        metadata, res = dbx.files_download("/" + nome_file)
        with open(nome_file, "wb") as f:
            f.write(res.content)
            
        # Scarica le foto dalla cartella /allegati di Dropbox
        if not os.path.exists(ALLEGATI_DIR):
            os.makedirs(ALLEGATI_DIR)
            
        try:
            # Elenca i file dentro la cartella /allegati su Dropbox
            risultato = dbx.files_list_folder('/allegati')
            for entry in risultato.entries:
                percorso_locale = os.path.join(ALLEGATI_DIR, entry.name)
                if not os.path.exists(percorso_locale):
                    dbx.files_download_to_file(percorso_locale, "/allegati/" + entry.name)
        except:
            # Se la cartella /allegati non esiste ancora su Dropbox, non facciamo nulla
            pass
            
        return True
    except Exception as e:
        return False

def salva_su_dropbox(file_locali):
    try:
        dbx = connetti_dropbox()
        for percorso_locale in file_locali:
            if os.path.exists(percorso_locale):
                # Se è la foto, la mettiamo nella cartella /allegati su Dropbox
                if "allegati" in percorso_locale:
                    nome_file_dbx = "/allegati/" + os.path.basename(percorso_locale)
                else:
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

    # NOVITÀ: Scarica i dati aggiornati da Dropbox appena apri l'app
    if "db_scaricato" not in st.session_state:
        scarica_database_da_dropbox(DB_NOME)
        st.session_state["db_scaricato"] = True

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
        
        # Carichiamo il database all'inizio del blocco Archivio
        if os.path.exists(DB_NOME):
            df = pd.read_csv(DB_NOME)
            
            search = st.text_input("Cerca per Brand, Modello o Sintomo...")
            if search:
                # Filtro di ricerca
                df_filtrato = df[df.apply(lambda r: search.lower() in r.astype(str).str.lower().values, axis=1)]
            else:
                df_filtrato = df

            # Visualizziamo i risultati
            if not df_filtrato.empty:
                for i, row in df_filtrato.sort_index(ascending=False).iterrows():
                    unique_key = f"{i}_{row['Data']}".replace(" ", "").replace("/", "").replace(":", "")
                    
                    with st.expander(f"📝 {row['Brand']} {row['Modello']} - {row['Data']}"):
                        # Form di modifica
                        with st.form(f"form_edit_{unique_key}"):
                            st.subheader("Modifica Intervento")
                            c1, c2, c3 = st.columns(3)
                            new_brand = c1.text_input("Brand", value=row['Brand'], key=f"brand_{unique_key}").upper()
                            new_modello = c2.text_input("Modello", value=row['Modello'], key=f"model_{unique_key}")
                            new_motore = c3.text_input("Motore", value=row['Motore'], key=f"motor_{unique_key}")
                            
                            new_sintomo = st.text_area("Sintomo / Difetto", value=row['Sintomo'], key=f"sint_{unique_key}")
                            new_soluzione = st.text_area("Soluzione Tecnica", value=row['Soluzione'], key=f"sol_{unique_key}")
                            
                            st.write("---")
                            st.write("📷 **Aggiorna o aggiungi foto**")
                            new_file = st.file_uploader("Scegli un nuovo file (opzionale)", type=['png', 'jpg', 'jpeg'], key=f"file_up_{unique_key}")
                            
                            if st.form_submit_button("💾 SALVA MODIFICHE"):
                                df.at[i, 'Brand'] = new_brand
                                df.at[i, 'Modello'] = new_modello
                                df.at[i, 'Motore'] = new_motore
                                df.at[i, 'Sintomo'] = new_sintomo
                                df.at[i, 'Soluzione'] = new_soluzione
                                
                                file_da_sincronizzare = [DB_NOME]
                                if new_file:
                                    new_path = os.path.join(ALLEGATI_DIR, new_file.name)
                                    with open(new_path, "wb") as f:
                                        f.write(new_file.getbuffer())
                                    df.at[i, 'Allegato'] = new_path
                                    file_da_sincronizzare.append(new_path)
                                
                                df.to_csv(DB_NOME, index=False)
                                salva_su_dropbox(file_da_sincronizzare)
                                st.success("Modifica salvata!")
                                st.rerun()

                        # Visualizzazione Foto e tasto Elimina
                st.write("---")
                col_foto, col_del = st.columns([3, 1])
                
                with col_foto:
                    percorso_raw = row.get('Allegato', "")
                    
                    if pd.notna(percorso_raw) and isinstance(percorso_raw, str) and percorso_raw.strip() != "":
                        nome_file = os.path.basename(percorso_raw)
                        percorso_corretto_locale = os.path.join(ALLEGATI_DIR, nome_file)

                        if os.path.exists(percorso_corretto_locale):
                            try:
                                with open(percorso_corretto_locale, "rb") as f:
                                    data = f.read()
                                    if len(data) > 0:
                                        st.image(data, caption=f"Foto: {nome_file}", width=300)
                                    else:
                                        st.warning(f"Il file {nome_file} è vuoto.")
                            except Exception as e:
                                st.error(f"Errore lettura file: {e}")
                        else:
                            # Se non è sul server, proviamo a scaricarlo al volo
                            try:
                                dbx = connetti_dropbox()
                                with open(percorso_corretto_locale, "wb") as f:
                                    metadata, res = dbx.files_download(f"/allegati/{nome_file}")
                                    f.write(res.content)
                                st.image(percorso_corretto_locale, caption=f"Recuperata: {nome_file}", width=300)
                            except:
                                st.warning(f"Foto {nome_file} non trovata.")
                    else:
                        st.info("Nessuna foto per questo intervento.")