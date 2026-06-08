# ☁️ Azure Serverless RCE (Remote Code Execution)

An asynchronous and message-driven cloud platform for remote code compilation and execution. 
The system leverages the Worker pattern to decouple request reception from processing. It accepts source code written in a custom language as input, translates it into C via a dedicated lexical/syntactic/semantic analyzer, compiles it, and processes the user input within a secure and isolated sandbox.

## 🏗 Project Architecture

The project uses a microservices architecture entirely based on **Microsoft Azure**, separating the frontend from the heavy computing environment to ensure scalability and security.

![Azure Architecture](https://img.shields.io/badge/Architecture-Message_Driven-blue)
![Cloud](https://img.shields.io/badge/Cloud-Microsoft_Azure-0089D6?logo=microsoft-azure&logoColor=white)

The 5 Azure services used are:
1. **Azure App Service**: Hosts the frontend web interface developed in Python (Streamlit). It receives input, queries the database, and displays the results.
2. **Azure Queue Storage**: Asynchronous messaging queue that decouples user requests from the execution engine, preventing timeouts.
3. **Azure Blob Storage**: Physical storage divided into two containers (`input-files` and `output-files`) to save source codes, batch inputs, and generated outputs.
4. **Azure Cosmos DB (NoSQL Serverless)**: Database that maintains the history of all executions, computation times, progress status, and file references.
5. **Azure Container Instances (ACI)**: Isolated worker based on a Docker container. It picks up tasks from the queue, runs the Java translator (JFlex/CUP), compiles with GCC, executes the binary, saves the results, and finally cleans up the environment.

## ✨ Key Features

* **Source-to-Source Compilation**: Automatic translation from the custom language to the target C language.
* **Batch Execution**: Ability to inject a standard input directly when submitting the code.
* **Isolation and Security**: Execution takes place within an ephemeral Linux container, preventing damage to the host system.
* **Job History**: Dedicated interface to navigate the history of past executions, allowing users to view the input, generated intermediate C code, and final output.

---

## 🚀 Local Setup Guide

To test the project on your computer without deploying to Azure, you must have **Docker** and **Python 3.10+** installed.

### 1. Clone the repository
```bash
git clone https://github.com/losor2002/AzureServerlessRCE.git
cd AzureServerlessRCE
```
### 2. Configure the cloud environment
You need to create the Azure services (Storage Account and Cosmos DB) and obtain their keys.
Create a file named .env in the root of the project and insert the following credentials:
```text
AZURE_STORAGE_CONNECTION_STRING=La_Tua_Stringa_Di_Connessione
COSMOS_DB_ENDPOINT=Il_Tuo_URI_Cosmos
COSMOS_DB_KEY=La_Tua_Chiave_Primaria
```

### 3. Start the Backend (Isolated Worker)
Build the Docker image containing Java, GCC, and the Python script, and start it by injecting the environment variables:
```bash
docker build -t compilatore-cloud Docker
docker run --env-file .env compilatore-cloud
```
*The worker will remain listening on the Azure queue.*

### 4. Start the Frontend (Web Interface)
Open a second terminal, install the dependencies, and start Streamlit:
```bash
pip install -r requirements.txt
streamlit run app.py
```
*The interface will be available at `http://localhost:8501`.*

## 📂 Repository Structure
```text
├── Docker                     # Folder containing the necessary files to build the worker's Docker image
│   ├── MyFun2C.sh             # Bash automation script that starts the Java parser and GCC compiler
│   ├── Sorrentino_es5...jar   # JAR containing the transpiler from the MyFun language to C
│   └── worker.py              # Python daemon running in the container that orchestrates the download, compilation, and upload of results.
├── app.py                     # Streamlit frontend application
└── requirements.txt           # Python dependencies for the web server
```

*Transpiler project repository: [https://gitlab.com/compilatori3/Sorrentino_es5_MyFun](https://gitlab.com/compilatori3/Sorrentino_es5_MyFun)*
