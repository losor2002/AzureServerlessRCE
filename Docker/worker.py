import os
import subprocess
import time
import json
from azure.storage.queue import QueueClient
from azure.storage.blob import BlobServiceClient
from azure.cosmos import CosmosClient

# 1. LETTURA VARIABILI D'AMBIENTE
AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
COSMOS_DB_ENDPOINT = os.environ.get("COSMOS_DB_ENDPOINT")
COSMOS_DB_KEY = os.environ.get("COSMOS_DB_KEY")

if not all([AZURE_STORAGE_CONNECTION_STRING, COSMOS_DB_ENDPOINT, COSMOS_DB_KEY]):
    raise ValueError("ERRORE: Variabili d'ambiente mancanti!")

# 2. INIZIALIZZAZIONE DEI CLIENT AZURE
blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)
queue_client = QueueClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING, "job-queue")
cosmos_client = CosmosClient(COSMOS_DB_ENDPOINT, COSMOS_DB_KEY)

# Collegamento al DB e ai Container
db_client = cosmos_client.get_database_client("rce-db")
cosmos_container = db_client.get_container_client("jobs")

container_input = blob_service_client.get_container_client("input-files")
container_output = blob_service_client.get_container_client("output-files")

def avvia_worker():
    print("Worker avviato. In attesa di messaggi nella coda 'job-queue'...")
    
    while True:
        messaggi = queue_client.receive_messages(max_messages=1)
        
        for msg in messaggi:
            print(f"\n--- NUOVO JOB RICEVUTO: {msg.id} ---")
            
            try:
                # Il messaggio sarà un JSON: {"jobId": "123"}
                dati_job = json.loads(msg.content)
                job_id = dati_job['jobId']
            except Exception as e:
                print(f"ERRORE CRITICO durante la lettura del messaggio: {e}")
                
                # Eliminiamo il messaggio dalla coda
                queue_client.delete_message(msg)
                print("Messaggio rimosso dalla coda. Torno in ascolto...")
                continue
            
            try:
                # Nomi dei file in input
                source_blob_name = f"sorgente_{job_id}.txt"
                input_blob_name = f"input_{job_id}.txt"
                # Nomi dei file di output
                output_txt_name = f"sorgente_{job_id}_output.txt"
                c_file_name = f"sorgente_{job_id}.c"
                
                print(f"[1/4] Download dei file dal Blob Storage...")
                with open(source_blob_name, "wb") as f:
                    f.write(container_input.download_blob(source_blob_name).readall())
                with open(input_blob_name, "wb") as f:
                    f.write(container_input.download_blob(input_blob_name).readall())

                print(f"[2/4] Esecuzione della compilazione (MyFun2C.sh)...")
                inizio = time.time()
                # Lanciamo lo script che hai creato prima
                processo = subprocess.run(
                    ["./MyFun2C.sh", source_blob_name, input_blob_name], 
                    capture_output=True, text=True
                )
                tempo_esecuzione = round(time.time() - inizio, 2)

                print(f"[3/4] Caricamento dei risultati sul Blob Storage...")
                
                stato_esecuzione = "Success" if processo.returncode == 0 else "Error"
                
                # Carichiamo l'output testuale (stdout)
                if os.path.exists(output_txt_name):
                    with open(output_txt_name, "rb") as f:
                        container_output.upload_blob(name=output_txt_name, data=f, overwrite=True)
                
                # Carichiamo il codice C intermedio generato
                if os.path.exists(c_file_name):
                    with open(c_file_name, "rb") as f:
                        container_output.upload_blob(name=c_file_name, data=f, overwrite=True)

                print(f"[4/4] Aggiornamento del database Cosmos DB...")
                # Struttura del documento da salvare nel database NoSQL
                documento_db = {
                    "id": job_id,           # Obbligatorio in CosmosDB
                    "jobId": job_id,        # La nostra Partition Key
                    "status": stato_esecuzione,
                    "executionTimeSec": tempo_esecuzione,
                    "log": processo.stderr if processo.returncode != 0 else processo.stdout,
                }
                # Upsert aggiorna il record se esiste, lo crea se non esiste
                cosmos_container.upsert_item(documento_db)

                print(f"JOB {job_id} COMPLETATO CON SUCCESSO IN {tempo_esecuzione}s!")
                
            except Exception as e:
                print(f"ERRORE CRITICO durante l'elaborazione del job: {e}")
            
            finally:
                # Qualsiasi cosa succeda (successo o errore), eliminiamo il messaggio dalla coda
                queue_client.delete_message(msg)
                print("Messaggio rimosso dalla coda.")
                
                # 2. Pulizia del File System
                print("Pulizia dei file temporanei in corso...")
                file_da_cancellare = [
                    source_blob_name,                           # Es: sorgente_123.txt
                    input_blob_name,                            # Es: input_123.txt
                    c_file_name,                                # Es: sorgente_123.c
                    output_txt_name,                            # Il file generato dallo script bash
                    f"sorgente_{job_id}.out",                   # L'eseguibile compilato da GCC
                    f"sorgente_{job_id}_parsed.xml"             # L'AST ottenuto dall'analisi sintattica
                ]
                
                for file_temp in file_da_cancellare:
                    if os.path.exists(file_temp):
                        os.remove(file_temp)
                        print(f"  - Eliminato: {file_temp}")
                
                print("Pulizia completata. Torno in ascolto...")
            
        time.sleep(5)

if __name__ == "__main__":
    avvia_worker()