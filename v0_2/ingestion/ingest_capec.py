import json
import os
from tqdm import tqdm
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

# --- CONFIGURAZIONE ---
JSON_FILE = '../data/capec.json'
DB_DIR = '../chroma_db'
BATCH_SIZE = 50 

print("🔍 Analisi del file CAPEC...")
with open(JSON_FILE, 'r') as f:
    capec_data = json.load(f)

documents = []
for obj in capec_data['objects']:
    if obj.get('type') == 'attack-pattern' and not obj.get('x_mitre_deprecated'):
        name = obj.get('name')
        desc = obj.get('description', 'Nessuna descrizione disponibile')
        
        capec_id = "N/A"
        related_cwes = []
        
        if obj.get('external_references'):
            for ref in obj['external_references']:
                source = ref.get('source_name', '').lower()
                ext_id = ref.get('external_id')
                if source == 'capec': capec_id = ext_id
                elif source == 'cwe': related_cwes.append(ext_id)
        
        # LOGICA ROBUSTA PER EXECUTION FLOW
        execution_flow = ""
        steps = obj.get('x_capec_execution_flow', [])
        if steps:
            flow_list = []
            for s in steps:
                if isinstance(s, dict):
                    flow_list.append(f"- Step {s.get('step', '?')}: {s.get('description', '')}")
                else:
                    flow_list.append(f"- {str(s)}")
            execution_flow = "\nExecution Flow:\n" + "\n".join(flow_list)

        content = (
            f"ID: {capec_id}\nAttack Pattern: {name}\n"
            f"Related CWEs: {', '.join(related_cwes)}\n"
            f"Description: {desc}{execution_flow}"
        )
        
        doc = Document(
            page_content=content, 
            metadata={"id": capec_id, "name": name, "type": "capec_pattern", "cwes": str(related_cwes)}
        )
        documents.append(doc)

embeddings = OllamaEmbeddings(model="bge-m3", base_url="http://10.0.2.2:11434")
vector_db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)

print(f"🚀 Indicizzazione di {len(documents)} pattern...")
for i in tqdm(range(0, len(documents), BATCH_SIZE)):
    vector_db.add_documents(documents[i : i + BATCH_SIZE])

print(f"\n✨ CAPEC integrato correttamente!")