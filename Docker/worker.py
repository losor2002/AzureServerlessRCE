import os
import subprocess
import time
import json
from azure.storage.queue import QueueClient
from azure.storage.blob import BlobServiceClient

AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
if not AZURE_STORAGE_CONNECTION_STRING:
    raise ValueError("ERRORE CRITICO: Variabile d'ambiente AZURE_STORAGE_CONNECTION_STRING non trovata!")

QUEUE_NAME = "job-queue"

def avvia_worker():
    print("Avvio del worker... In attesa di job nella coda.")
    queue_client = QueueClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING, QUEUE_NAME)
    
    while True:
        # Controlla la coda
        messaggi = queue_client.receive_messages(max_messages=1)
        
        for msg in messaggi:
            print(f"Trovato un nuovo job! ID Messaggio: {msg.id}")
            
            # Qui in futuro inseriremo il codice per scaricare i file dal Blob Storage
            # simuliamo di avere già i file sorgente.txt e input.txt pronti
            
            print("Avvio della pipeline di compilazione...")
            # Lancia il tuo script bash da Python e aspetta che finisca
            processo = subprocess.run(
                ["./MyFun2C.sh", "test_sorgente.txt", "test_input.txt"], 
                capture_output=True, 
                text=True
            )
            
            if processo.returncode == 0:
                print("Esecuzione completata con successo!")
                # Qui in futuro caricheremo output_finale.txt sul Blob e aggiorneremo Cosmos DB
            else:
                print("Errore durante l'esecuzione.")
                print(processo.stderr)

            # Rimuove il messaggio dalla coda a lavoro finito
            queue_client.delete_message(msg)
            print("Job completato e rimosso dalla coda. Torno in ascolto...\n")
            
        # Aspetta 5 secondi prima di controllare di nuovo la coda
        time.sleep(5)

if __name__ == "__main__":
    avvia_worker()