import os
import json
from bs4 import BeautifulSoup
import shutil
from testing.LLM_testing import extract_metric_from_text, extract_specification_from_text


# Percorsi delle cartelle
INPUT_FOLDER = "sources/json"  # Cartella contenente i file JSON con le tabelle
OUTPUT_FOLDER = "JSON_CLAIMS"  # Cartella per salvare i file di output

# Funzione per caricare il mapping da file JSON
def load_mapping(file_path):
    """
    Carica il file JSON contenente il mapping delle tabelle.

    Args:
        file_path (str): Il percorso del file JSON.

    Returns:
        dict: Il contenuto del file JSON come dizionario.
    """
    with open(file_path, "r") as f:
        return json.load(f)

# Funzione per svuotare e ricreare una cartella
def reset_folder(folder_path):
    """
    Svuota e ricrea una cartella specificata.

    Args:
        folder_path (str): Il percorso della cartella da resettare.
    """
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)  # Rimuove la cartella esistente
    os.makedirs(folder_path, exist_ok=True)  # Crea una nuova cartella vuota

# Funzione per stampare un messaggio colorato nel terminale
def printC(message, number):
    """
    Stampa un messaggio colorato nel terminale in base a un numero.

    Args:
        number (int): Numero da 0 a 3 per selezionare il colore.
        message (str): Il messaggio da stampare.
    """
    # Definizione dei colori (ANSI escape codes)
    colors = {
        0: "\033[91m",  # Rosso
        1: "\033[92m",  # Verde
        2: "\033[93m",  # Giallo
        3: "\033[94m",  # Blu
    }

    reset = "\033[0m"  # Reset al colore normale

    # Ottieni il colore in base al numero
    color = colors.get(number, reset)  # Default: colore normale

    # Stampa il messaggio con il colore selezionato
    print(f"{color}{message}{reset}")

# Funzione per gestire le tabelle di tipo 1
def process_table_type1(html_content, paper_id, table_index):
    """
    Elabora una tabella di tipo 1, estraendo le informazioni e salvandole in un file JSON.

    Args:
        html_content (str): Il contenuto HTML della tabella.
        paper_id (str): L'ID del documento.
        table_index (int): L'indice della tabella.
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")  # Analizza l'HTML della tabella
        table = soup.find("table")  # Trova la tabella

        if not table:
            print("[AVVISO] Nessuna tabella trovata.")
            return

        # Estrai intestazioni
        headers = [header.text.strip() for header in table.find("tr").find_all("th")]
        rows = table.find_all("tr")[1:]  # Ignora la riga delle intestazioni

        claims = []
        count = 0

        for row in rows:
            # Estrai celle
            cells = row.find_all("th") + row.find_all("td")
            if not cells:
                continue

            # Specifiche della claim
            specifications = "{" + ",".join(
                f"|{headers[i]}, {cells[i].text.strip()}|"
                for i in range(len(headers)) if i < len(cells)
            ) + "}"

            # Estrai misura e risultato
            for col_index, cell in enumerate(cells):
                if col_index == len(headers) - 1:  # Assume che l'ultima colonna sia la misura
                    measure = headers[col_index]
                    outcome = cell.text.strip()

                    if outcome:
                        claims.append({f'Claim {count}': f'|{specifications}, {measure}, {outcome}|'})
                        count += 1

        if claims:
            # Salva le claims in un file JSON
            output_filename = f"{paper_id}_{table_index}_claims.json"
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)

            with open(output_path, "w") as out_f:
                json.dump(claims, out_f, indent=4)

            print(f"[INFO] Salvato: {output_filename}")

    except Exception as e:
        print(f"[ERROR] Errore nel processamento della tabella: {e}")

# Funzione per gestire le tabelle di tipo 2
def process_table_type2(input_file, key, value, table_index):
    """
    Elabora una tabella di tipo 2, estraendo le informazioni e salvandole in un file JSON.

    Args:
        input_file (str): Il nome del file di input.
        key (str): La chiave del dizionario.
        value (dict): Il valore del dizionario che contiene la tabella e altre informazioni.
        table_index (int): L'indice della tabella.
    """
    SPEC_NAME = "SPEC_NAME"
    METRIC_NAME = "METRIC_NAME"
    count = 0

    try:
        html_content = value.get("table", "")  # Ottieni il contenuto della tabella
        caption = value["caption"]
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table")

        if not table:
            print(f"[AVVISO] Nessuna tabella trovata in {input_file}, chiave {key}.")
            return

        # Estrai intestazioni
        header_row = table.find("tr")
        headers = [header.text.strip() for header in header_row.find_all(["th", "td"])]

        METRIC_NAME = extract_metric_from_text(caption) or "METRIC_NAME"

        rows = table.find_all("tr")[1:]
        data = []

        # Processa le righe della tabella
        for row in rows:
            cells = row.find_all("th") + row.find_all("td")
            model_name = cells[0].text.strip()

            # Estrai i valori delle celle
            for col_index, cell in enumerate(cells[1:], start=1):
                value = cell.text.strip()
                if value:
                    SPEC_NAME = extract_specification_from_text(caption, headers[col_index]) or "SPEC_NAME"

                    # Crea la claim
                    data.append({
                        f'Claim {count}': f"|{{|{headers[0]}, {model_name}|, |{SPEC_NAME}, {headers[col_index]}|}}, {METRIC_NAME} , {value}|"
                    })
                    count += 1

        if data:
            # Salva le claims in un file JSON
            output_filename = f"{os.path.splitext(input_file)[0]}_{table_index}_claims.json"
            output_path = os.path.join(OUTPUT_FOLDER, output_filename)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            print(f"[INFO] Salvato: {output_filename}")

    except Exception as e:
        print(f"[ERROR] Errore nel processamento della tabella in {input_file}, chiave {key}: {e}")

# Funzione per estrarre le informazioni sul colspan
def extract_colspan_info(html_row):
    """
    Estrae le informazioni sul colspan dalle celle di una riga HTML.

    Args:
        html_row (str): Una riga HTML da analizzare.

    Returns:
        dict: Un dizionario con i nomi delle celle e il loro colspan progressivo.
    """
    if not html_row:
        raise ValueError("Il contenuto HTML della riga è vuoto o non valido.")

    soup = BeautifulSoup(html_row, "html.parser")

    row = soup.find("tr")
    if not row:
        raise ValueError("La riga HTML fornita non contiene tag <tr> validi.")

    cells = row.find_all("th")
    result = {}

    for cell in cells:
        cell_text = cell.get_text(strip=True) or "N/A"
        colspan = int(cell.get("colspan", 1))  # Ottieni il colspan (default 1, convertito a int)
        result[cell_text] = colspan

    # Rimuovi "N/A" solo se esiste
    if "N/A" in result:
        del result["N/A"]

    # Ricalcola il colspan progressivo solo dopo aver rimosso "N/A"
    colspan_sum = 0  # Variabile per sommare i colspan
    for cell_text in result:
        colspan_sum += result[cell_text]
        result[cell_text] = colspan_sum  # Aggiorna il risultato con il colspan progressivo

    return result


# Funzione per estrarre i claim dalla tabella
def process_table_type3(input_file, key, value, table_index):
    """
    Elabora una tabella di tipo 3, estraendo le informazioni e salvandole in un file JSON.

    Args:
        input_file (str): Il nome del file di input.
        key (str): La chiave del dizionario.
        value (dict): Il valore del dizionario che contiene la tabella e altre informazioni.
        table_index (int): L'indice della tabella.
    """
    count = 0
    try:
        html_content = value.get("table")

        # Analizza l'HTML
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table")

        # Controlla se la tabella è valida
        if not table:
            print(f"[AVVISO] Nessuna tabella trovata in {input_file}, chiave {key}.")
            return table_index

        # Estrai righe della tabella
        rows = table.find_all("tr")  # Estrai tutte le righe della tabella

        if len(rows) < 3:  # Assicurati che ci siano almeno intestazione e righe di dati
            print(f"[AVVISO] La tabella in {input_file}, chiave {key}, non ha abbastanza righe.")
            return table_index

        # Estrai intestazioni dalla seconda riga
        header_row = rows[1]

        # Estrai informazioni sul colspan dalla prima riga (specifiche)
        spec_row = str(rows[0])
        colspan_info = extract_colspan_info(spec_row)

        # Estrai chiavi dalle intestazioni
        header_cells = header_row.find_all(["th", "td"])
        header_keys = [cell.text.strip() for cell in header_cells]

        # Processa righe dei dati
        data = []
        for row_index, row in enumerate(rows[2:], start=3):  # Dalla terza riga in poi
            cells = row.find_all(["th", "td"])
            if len(cells) != len(header_keys):
                print(f"[AVVISO] Numero di celle diverso dalle intestazioni in {input_file}, riga {row_index}.")
                continue

            metric_name = cells[0].text.strip()  # La prima cella è il nome della metrica
            for col_index, cell in enumerate(cells[1:], start=1):  # Salta la prima cella
                for key, value in colspan_info.items():
                    if col_index <= value:
                        spec_name = key
                        break
                    spec_name = "Spec_name"

                spec_value = header_keys[col_index]  # Nome della specifica
                metric_value = cell.text.strip()  # Valore della specifica

                if metric_value:  # Solo celle non vuote
                    claim = {
                        f"Claim {count}": f"|{{|{spec_name}, {spec_value}|}}, {metric_name}, {metric_value}|"
                    }
                    data.append(claim)
                    count += 1

        # Salva il risultato in un file JSON
        output_filename = f"{os.path.splitext(input_file)[0]}_{table_index}_claims.json"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"[INFO] Salvato: {output_filename}")
        table_index += 1

    except Exception as e:
        print(f"[ERRORE] Errore nel processamento della tabella in {input_file}, chiave {key}: {e}")
        return table_index

    return table_index


# Funzione principale per processare i file JSON
def process_json_files(output_mapping):
    """
    Elabora i file JSON nella cartella di input, utilizzando il mapping per decidere
    quale tipo di tabella processare e salvarne i risultati in file JSON separati.

    Args:
        input_folder (str): La cartella contenente i file JSON.
        output_folder (str): La cartella dove salvare i file JSON di output.
        output_mapping (dict): Un dizionario che mappa i tipi di tabelle da processare.
    """
    # Itera su tutti i file nella cartella
    for input_file in os.listdir(INPUT_FOLDER):
        if input_file.endswith(".json"):
            # Ottieni il nome del file senza estensione
            file_name = input_file[:-5]
            input_path = os.path.join(INPUT_FOLDER, input_file)
            paper_id = os.path.splitext(input_file)[0]

            with open(input_path, "r") as f:
                content = json.load(f)

            # Processa ogni "table" presente
            table_index = 1
            for key, value in content.items():
                # Ottieni il valore di mapping per la chiave corrente (file_name + key)
                mapping_value = output_mapping.get(f"{file_name}_{key}")
                printC(f"[PROCESSING] Chiave: {file_name}_{key}, Valore di mapping: {mapping_value}", mapping_value)

                # Processa la tabella in base al valore di mapping
                if mapping_value == 1 and "table" in value:
                    process_table_type1(value["table"], paper_id, table_index)
                    table_index += 1

                elif mapping_value == 2 and "table" in value:
                    process_table_type2(input_file, key, value, table_index)
                    table_index += 1
                elif mapping_value == 3 and "table" in value:
                    process_table_type3(input_file, key, value, table_index)
                    table_index += 1
                else:
                    print(f"[INFO] Saltata la chiave {key} poiché il valore di mapping è non gestito.")

if __name__ == "__main__":
    # Carica il mapping da un file JSON
    output_mapping = load_mapping("classification_mapping.json")
    
    # Resetta la cartella di output
    reset_folder(OUTPUT_FOLDER)
    
    # Avvia il processamento dei file JSON
    process_json_files(output_mapping)
