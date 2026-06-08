import streamlit as st
import os
import uuid
import json
import time
from dotenv import load_dotenv
from azure.storage.queue import QueueClient
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient

# Carica le variabili d'ambiente
load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
COSMOS_DB_ENDPOINT = os.environ.get("COSMOS_DB_ENDPOINT")
COSMOS_DB_KEY = os.environ.get("COSMOS_DB_KEY")

@st.cache_resource
def init_clients():
    blob_svc = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
    queue_svc = QueueClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING, "job-queue")
    cosmos_svc = CosmosClient(COSMOS_DB_ENDPOINT, COSMOS_DB_KEY)
    db = cosmos_svc.get_database_client("rce-db")
    cosmos_container = db.get_container_client("jobs")
    return blob_svc, queue_svc, cosmos_container

blob_service_client, queue_client, cosmos_container = init_clients()
container_out = blob_service_client.get_container_client("output-files")
container_in = blob_service_client.get_container_client("input-files")

st.set_page_config(page_title="Cloud Compiler RCE", page_icon="☁️", layout="wide")
st.title("☁️ Piattaforma Serverless per Remote Code Execution")

# Creazione delle due schede principali
tab_nuovo, tab_cronologia = st.tabs(["🚀 Nuovo Job", "🕒 Cronologia Esecuzioni"])

# --- FUNZIONE DI SUPPORTO PER MOSTRARE I RISULTATI ---
def mostra_risultati(risultato):
    if risultato.get('status') == 'Success':
        st.success(f"✅ Esecuzione completata con successo in {risultato.get('executionTimeSec', 0)} secondi.")
    else:
        st.error("❌ Si è verificato un errore durante l'elaborazione.")
        
    # Mostra i log bash del processo di compilazione
    st.subheader("Log della Compilazione (MyFun2C.sh)")
    st.code(risultato.get('log', 'Nessun log disponibile.'), language="text")
    
    if risultato.get('status') == 'Success':
        # Crea due colonne affiancate per l'Output e il Codice C
        col_out, col_c = st.columns(2)

        with col_out:
            st.subheader("Output del Programma Eseguito")
            try:
                out_blob = f"sorgente_{risultato['jobId']}_output.txt"
                if out_blob:
                    # Scarica il file output.txt e lo decodifica
                    testo_out = container_out.download_blob(out_blob).readall().decode('utf-8', errors='replace')
                    st.code(testo_out, language="text")
                else:
                    st.info("Nessun output registrato per questo job.")
            except Exception as e:
                st.warning(f"File di output non trovato nel Blob Storage: {e}")

        with col_c:
            with st.expander("Codice C Generato", expanded=False):
                try:
                    c_blob = f"sorgente_{risultato['jobId']}.c"
                    if c_blob:
                        # Scarica il file .c e lo decodifica
                        testo_c = container_out.download_blob(c_blob).readall().decode('utf-8', errors='replace')
                        st.code(testo_c, language="c")
                    else:
                        st.info("Nessun file C registrato per questo job.")
                except Exception as e:
                    st.warning(f"File C non trovato nel Blob Storage: {e}")


# --- SCHEDA 1: NUOVO JOB ---
with tab_nuovo:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📄 Codice Sorgente")
        codice_sorgente = st.text_area("Inserisci il codice custom:", height=300, label_visibility="collapsed")

    with col2:
        st.markdown("### ⌨️ Standard Input (Batch)")
        input_batch = st.text_area("Inserisci l'input (opzionale):", height=300, label_visibility="collapsed")

    if st.button("🚀 Compila ed Esegui", type="primary", use_container_width=True):
        if not codice_sorgente.strip():
            st.warning("⚠️ Inserisci del codice sorgente prima di eseguire.")
        else:
            job_id = str(uuid.uuid4())
            source_name = f"sorgente_{job_id}.txt"
            input_name = f"input_{job_id}.txt"
            
            with st.status("Avvio pipeline cloud...", expanded=True) as status:
                st.write("📦 Caricamento file su Azure Blob Storage...")
                container_in.upload_blob(name=source_name, data=codice_sorgente, overwrite=True)
                container_in.upload_blob(name=input_name, data=input_batch, overwrite=True)
                
                st.write("📨 Inserimento job nella coda...")
                messaggio = {"jobId": job_id}
                queue_client.send_message(json.dumps(messaggio))
                
                st.write("⏳ In attesa che il worker elabori il codice...")
                
                risultato = None
                tentativi = 0
                while tentativi < 30: # Circa 60 secondi di timeout
                    time.sleep(2)
                    tentativi += 1
                    query = f"SELECT * FROM c WHERE c.jobId = '{job_id}'"
                    items = list(cosmos_container.query_items(query=query, enable_cross_partition_query=True))
                    if items:
                        risultato = items[0]
                        break
                
                if risultato:
                    status.update(label="Elaborazione completata!", state="complete")
                else:
                    status.update(label="Timeout! Il worker sta impiegando troppo tempo o è spento.", state="error")
                    st.stop()

            st.divider()
            mostra_risultati(risultato)


# --- SCHEDA 2: CRONOLOGIA ---
with tab_cronologia:
    col_titolo, col_btn = st.columns([4, 1])
    with col_titolo:
        st.markdown("### Storico dei Job eseguiti")
    with col_btn:
        if st.button("🔄 Aggiorna dati", use_container_width=True):
            st.rerun()
        
    try:
        # Recupera tutti gli item da Cosmos DB
        tutti_jobs = list(cosmos_container.query_items(query="SELECT * FROM c", enable_cross_partition_query=True))
        
        if not tutti_jobs:
            st.info("Nessun job trovato nel database.")
        else:
            # Ordiniamo in Python i job dal più recente al più vecchio (usando il timestamp interno _ts)
            tutti_jobs.sort(key=lambda x: x.get('_ts', 0), reverse=True)
            
            # Creiamo un dizionario per popolare la selectbox { "ID - Stato - Tempo": record_intero }
            opzioni_job = {f"{j['jobId']} | Esito: {j.get('status', 'N/A')} | Tempo: {j.get('executionTimeSec', 0)}s": j for j in tutti_jobs}
            
            job_selezionato_label = st.selectbox("Seleziona un'esecuzione precedente per vederne i dettagli:", list(opzioni_job.keys()))
            
            if job_selezionato_label:
                item_selezionato = opzioni_job[job_selezionato_label]
                st.divider()
                
                # --- NUOVA SEZIONE: CODICE SORGENTE E INPUT ---
                st.subheader("File di Input Originali")
                col_sorgente, col_input = st.columns(2)

                job_id = item_selezionato.get('jobId')

                with col_sorgente:
                    st.subheader("📄 Codice Sorgente")
                    try:
                        nome_sorgente = f"sorgente_{job_id}.txt"
                        testo_sorgente = container_in.download_blob(nome_sorgente).readall().decode('utf-8', errors='replace')
                        st.code(testo_sorgente, language="text") # Metti "text" o il nome del tuo linguaggio
                    except Exception as e:
                        st.warning(f"File sorgente non trovato nel Blob Storage: {e}")

                with col_input:
                    st.subheader("⌨️ Standard Input")
                    try:
                        nome_input = f"input_{job_id}.txt"
                        testo_input = container_in.download_blob(nome_input).readall().decode('utf-8', errors='replace')
                        if testo_input.strip():
                            st.code(testo_input, language="text")
                        else:
                            st.info("Nessun input batch fornito per questa esecuzione.")
                    except Exception as e:
                        st.warning(f"File di input non trovato nel Blob Storage: {e}")
                st.divider()
                # ----------------------------------------------
                
                mostra_risultati(item_selezionato)
                
    except Exception as e:
        st.error(f"Errore nel caricamento della cronologia: {e}")