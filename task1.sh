#!/bin/bash

# Esegui il primo script Python
# EFFETTUA TUTTE LE ESTRAZIONI DI CLAIM
python3 claim_extractor.py
# Verifica se il primo script è stato eseguito correttamente
if [ $? -eq 0 ]; then
    echo "claim_extractor.py completato con successo"
else
    echo "Errore nell'esecuzione di claim_extractor.py"
    exit 1
fi

# Esegui il secondo script Python
# effettua la conversione del file JSON in formato leggibile
python3 format_json.py
# Verifica se il primo script è stato eseguito correttamente
if [ $? -eq 0 ]; then
    echo "format_json.py completato con successo"
else
    echo "Errore nell'esecuzione di format_json.py"
    exit 1
fi
