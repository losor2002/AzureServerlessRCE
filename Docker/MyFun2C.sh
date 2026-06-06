#!/bin/bash

# Controlla se sono stati passati sia il file sorgente che il file di input
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Uso: ./MyFun2C.sh <file_sorgente> <file_input>"
    exit 1
fi

INPUT_FILE=$1
BATCH_INPUT=$2
BASE_NAME="${INPUT_FILE%.*}"
C_FILE="${BASE_NAME}.c"
EXECUTABLE="${BASE_NAME}.out"
OUTPUT_TXT="output_finale.txt"

echo "=== Pipeline di Compilazione ed Esecuzione ==="
echo "Input: $INPUT_FILE"
echo "File batch input: $BATCH_INPUT"
echo "File C: $C_FILE"
echo "Eseguibile: $EXECUTABLE"
echo "File Output: $OUTPUT_TXT"
echo "=============================================="

echo "[1/3] Compilazione da TuoLinguaggio a C..."
java -jar Sorrentino_es5_MyFun-1.0-SNAPSHOT-jar-with-dependencies.jar "$INPUT_FILE"

# Controlla se la compilazione Java ha avuto successo
if [ $? -ne 0 ]; then
    echo "Errore durante l'analisi e compilazione in C."
    exit 1
fi

echo "[2/3] Compilazione da C a Eseguibile tramite GCC..."
gcc "$C_FILE" -o "$EXECUTABLE" -lm

if [ $? -ne 0 ]; then
    echo "Errore durante la compilazione C (GCC)."
    exit 1
fi

echo "[3/3] Esecuzione in ambiente isolato..."
# Esegue il binario, inietta l'input utente (stdin) e salva i risultati (stdout)
./"$EXECUTABLE" < "$BATCH_INPUT" > "$OUTPUT_TXT"

# Se il programma va in crash (es. segmentation fault o divisione per zero)
if [ $? -ne 0 ]; then
    echo "Errore a runtime durante l'esecuzione del programma generato."
    exit 1
fi

echo "Successo! L'output dell'esecuzione è stato salvato in $OUTPUT_TXT"