from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# --- CONFIGURAZIONE ---
DB_DIR = '../chroma_db'
# Caricamento embeddings e database
embeddings = OllamaEmbeddings(model="bge-m3", base_url="http://10.0.2.2:11434")
vector_db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
retriever = vector_db.as_retriever(search_kwargs={"k": 8})

# Modello di linguaggio
llm = ChatOllama(model="mistral", base_url="http://10.0.2.2:11434", temperature=0.0)

# --- PROMPT GENERALE CON FEW-SHOT ---
# Questo template insegna al modello il metodo, rendendolo flessibile per ogni input.
system_prompt = """Sei un esperto Analista Cyber. Analizza il log fornito e identifica la catena logica dell'attacco.

METODO DI ANALISI:
1. Identifica il VETTORE (come avviene l'attacco).
2. Identifica l'INTENTO (cosa vuole ottenere l'attaccante).
3. Correla i dati usando esclusivamente il CONTESTO fornito.

ESEMPI DI RAGIONAMENTO:
- Log: "GET /index.php?id=1' OR '1'='1" -> Vettore: SQL Injection nei parametri URL -> Mappatura: CAPEC-66, CWE-89, T1190.
- Log: "Failed password for root from 192.168.1.100 port 22" -> Vettore: SSH Brute Force -> Mappatura: CAPEC-112, CWE-307, T1110.

CONTESTO:
{context}

LOG DA ANALIZZARE: 
{question}

RISPOSTA (Segui rigorosamente questo schema):
- ANALISI DEL VETTORE: [Descrizione tecnica del log]
- CATENA LOGICA: [CAPEC ID] -> [CWE ID] -> [MITRE ID]
- DETTAGLI: [Cita i nomi esatti presenti nel contesto per ogni ID]
- OSSERVAZIONI: [Note su eventuali anomalie o passi successivi nella Kill Chain]"""

prompt = ChatPromptTemplate.from_template(system_prompt)

# --- CATENA DI ELABORAZIONE ---
rag_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

def run_test(log_line):
    print(f"\n" + "—"*60)
    print(f"📡 TEST LOG: {log_line}")
    print("—"*60)
    
    response = rag_chain.invoke(log_line)
    print(response)

if __name__ == "__main__":
    # Inserire la query qui
    import sys
    if len(sys.argv) > 1:
        run_test(sys.argv[1])
    else:
        print("Inserisci una riga di log come argomento.")