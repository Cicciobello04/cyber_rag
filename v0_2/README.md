# v0_2 - Cyber RAG UI

Interfaccia web per caricare codice/report/log, analizzare i contenuti con retrieval su Chroma (MITRE/CWE) e generare conclusioni tramite agente LLM.

## Struttura

- `v0_2/ui/app.py`: UI web (upload, risultati, storico)
- `v0_2/services/file_ingestion.py`: validazione/sanitizzazione/normalizzazione input
- `v0_2/services/analysis_engine.py`: motore unificato di analisi
- `v0_2/storage/report_store.py`: salvataggio storico analisi in JSON
- `v0_2/models/schemas.py`: schema unico di input/output

## Avvio

Dal root repository:

```bash
pip install -r /home/runner/work/cyber_rag/cyber_rag/v0_2/requirements.txt
python -m uvicorn v0_2.ui.app:app --host 0.0.0.0 --port 8000
```

Apri: `http://localhost:8000`

## Requisiti operativi

- Chroma DB già popolato in `v0_2/chroma_db`
- Ollama raggiungibile su `http://10.0.2.2:11434`
- Modelli:
  - Embedding: `bge-m3`
  - LLM: `mistral`

## Flussi supportati

- Upload singolo o multiplo (batch)
- Analisi per file codice/report/log con output uniforme
- Storico consultabile dei report generati

## Formati supportati

Codice: `.py .c .cpp .cc .h .hpp .java .js .ts .go .rs .php .cs`

Testo/report/log: `.txt .md .log .json .yaml .yml .csv .xml`

Dimensione massima file: 2MB
