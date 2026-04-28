import os, json
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import JsonOutputParser

# --- 1. CONFIGURAZIONE SISTEMA ---
DB_DIR = '../chroma_db'
embeddings = OllamaEmbeddings(model="bge-m3", base_url="http://10.0.2.2:11434")
vector_db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)

# Mistral configurato per massimizzare il grounding deterministico
llm = ChatOllama(model="mistral", base_url="http://10.0.2.2:11434", temperature=0.0, format="json")

# --- 2. PROMPT DI ESTRAZIONE RIGIDA ---
extraction_template = """Sei un estrattore di dati JSON per la cybersecurity. 
Analizza l'INPUT e usa SOLO i documenti nelle sezioni SOURCE per la mappatura.

REGOLE TASSATIVE:
1. CAPEC ID: Cerca solo in 'SOURCE CAPEC_PATTERN'.
2. CWE ID: Cerca solo in 'SOURCE CWE_WEAKNESS'.
3. MITRE ID: Cerca solo in 'SOURCE MITRE_TECHNIQUE'.
4. Se un ID non è presente nel contesto, scrivi "NOT_FOUND".
5. Non usare la tua memoria per inventare ID. Copia letteralmente dal contesto.

CONTESTO:
{context}

INPUT: 
{question}

RISPOSTA JSON:
{{
  "analisi_tecnica": "...",
  "capec": {{"id": "...", "nome": "..."}},
  "cwe": {{"id": "...", "nome": "..."}},
  "mitre": {{"id": "...", "nome": "..."}}
}}"""
extraction_prompt = ChatPromptTemplate.from_template(extraction_template)

# --- 3. LOGICA DI ANALISI E LETTURA ---

def run_cyber_analysis(target_input):
    """
    Riconosce se l'input è un file o testo diretto e avvia la pipeline RAG.
    """
    content = target_input
    
    # Logica di lettura file
    if os.path.isfile(target_input):
        print(f"📂 Rilevato percorso file: {target_input}. Lettura contenuto...")
        with open(target_input, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        print(f"✍️ Analisi testo diretto rilevata.")

    print(f"🚀 Elaborazione di {len(content)} caratteri...")
    
    # FASE 1: HyDE (Espansione Semantica)
    print("🧠 FASE 1: HyDE - Generazione descrizione tecnica intermedia...")
    hyde_desc = llm.invoke(f"Descrivi tecnicamente questa minaccia: {content}").content

    # FASE 2: FILTERED RETRIEVAL (Bilanciamento Metadati)
    print("🔍 FASE 2: RETRIEVAL - Recupero documenti mirati dal database...")
    docs_mitre = vector_db.similarity_search(hyde_desc, k=3, filter={"type": "mitre_technique"})
    docs_cwe = vector_db.similarity_search(hyde_desc, k=3, filter={"type": "cwe_weakness"})
    docs_capec = vector_db.similarity_search(hyde_desc, k=3, filter={"type": "capec_pattern"})
    
    context_parts = []
    for d in docs_mitre: context_parts.append(f"[SOURCE MITRE] ID: {d.metadata.get('id')}\n{d.page_content}")
    for d in docs_cwe: context_parts.append(f"[SOURCE CWE] ID: {d.metadata.get('id')}\n{d.page_content}")
    for d in docs_capec: context_parts.append(f"[SOURCE CAPEC] ID: {d.metadata.get('id')}\n{d.page_content}")
    
    # FASE 3: EXTRACTION & MAPPING JSON
    print("🔬 FASE 3: EXTRACTION - Mappatura deterministica in corso...")
    chain = (
        {"context": lambda x: "\n\n".join(context_parts), "question": RunnablePassthrough()}
        | extraction_prompt
        | llm
        | JsonOutputParser()
    )
    
    result = chain.invoke(content)
    print("\n" + "="*55 + "\n✅ REPORT ANALISI VALIDATO\n" + "="*55)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    # Puoi passare una stringa o un percorso file (es. "vulnerable.c" o "attack.log")
    input_test = "Un utente ha tentato di scalare i privilegi eseguendo un exploit locale basato su un errore di configurazione dei permessi SUID su un binario di sistema."
    # input_test = "../testing/vulnerable/vulnerable.c"
    
    run_cyber_analysis(input_test)