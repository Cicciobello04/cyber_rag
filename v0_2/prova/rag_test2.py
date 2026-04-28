from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# --- CONFIGURAZIONE ---
DB_DIR = '../chroma_db'
embeddings = OllamaEmbeddings(model="bge-m3", base_url="http://10.0.2.2:11434")
vector_db = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
retriever = vector_db.as_retriever(search_kwargs={"k": 8})

# Modello (Temperature bassa per massima precisione)
llm = ChatOllama(model="mistral", base_url="http://10.0.2.2:11434", temperature=0.0)

# --- PROMPT 1: ANALISI E GROUNDING ---
# Qui forziamo il modello a copiare letteralmente dal contesto
analysis_template = """Sei un analista SOC di terzo livello. 
Usa il contesto fornito per identificare pattern di attacco in una riga di log.

REGOLE CRITICHE:
1. Se citi un ID (CWE, CAPEC, MITRE), devi copiare TESTUALMENTE il nome e la descrizione dal CONTESTO.
2. Non usare la tua memoria interna per definire gli ID. Se il contesto dice che CWE-78 è "OS Command Injection", scrivi quello.
3. Se non trovi l'ID nel contesto, non inventare.

CONTESTO:
{context}

LOG: 
{question}

RISPOSTA ATTESA:
- PATTERN (CAPEC): [ID - Nome]
- VULNERABILITÀ (CWE): [ID - Nome]
- TECNICA (MITRE): [ID - Nome]
- ANALISI: [Spiegazione tecnica breve]"""

analysis_prompt = ChatPromptTemplate.from_template(analysis_template)

# --- PROMPT 2: SELF-CORRECTION (VERIFICA) ---
verification_template = """Sei un revisore tecnico. Confronta l'ANALISI prodotta con il CONTESTO originale.
Il tuo compito è correggere eventuali errori di associazione tra ID e nomi (es. se CWE-78 è stato chiamato XSS invece di OS Command Injection).

CONTESTO ORIGINALE:
{context}

ANALISI DA REVISIONARE:
{analysis}

RISPOSTA:
Se l'analisi è corretta, restituiscila uguale. 
Se ci sono errori nei nomi degli ID, riscrivi l'analisi corretta mantenendo lo stesso schema."""

verification_prompt = ChatPromptTemplate.from_template(verification_template)

# --- COSTRUZIONE DELLE CATENE ---
# Catena di analisi
analysis_chain = (
    {"context": retriever, "question": RunnablePassthrough()}
    | analysis_prompt
    | llm
    | StrOutputParser()
)

# Catena di verifica (prende l'output della prima e il contesto)
def self_correction_step(input_data):
    # Recuperiamo di nuovo il contesto per la verifica
    context_docs = retriever.invoke(input_data["log"])
    context_text = "\n\n".join([doc.page_content for doc in context_docs])
    
    # Eseguiamo la revisione
    return verification_prompt.format(context=context_text, analysis=input_data["analysis"])

# --- FUNZIONE DI ANALISI AVANZATA ---
def analyze_log_with_verification(log_line):
    print(f"\n" + "="*60)
    print(f"🔍 FASE 1: Generazione Analisi")
    print("="*60)
    
    # Eseguiamo la prima catena
    initial_analysis = analysis_chain.invoke(log_line)
    
    # Se initial_analysis è un oggetto, estraiamo il contenuto
    if hasattr(initial_analysis, 'content'):
        initial_analysis = initial_analysis.content
    
    print(f"\n🧪 FASE 2: Verifica e Auto-Correzione...")
    
    context_docs = retriever.invoke(log_line)
    context_text = "\n\n".join([doc.page_content for doc in context_docs])
    
    # Chiamata al verificatore
    raw_final_output = llm.invoke(
        verification_prompt.format(context=context_text, analysis=initial_analysis)
    )
    
    # GESTIONE OUTPUT: Estraiamo solo il testo se è un oggetto LangChain
    final_text = raw_final_output.content if hasattr(raw_final_output, 'content') else str(raw_final_output)

    # Pulizia finale: rimuoviamo eventuali residui del prompt di verifica
    if "RESPONSE:" in final_text:
        final_text = final_text.split("RESPONSE:")[0]

    print("\n" + "="*60)
    print("✅ REPORT FINALE VALIDATO:")
    print("="*60)
    print(final_text.strip())

if __name__ == "__main__":
    test_log = "GET /admin.php?cmd=whoami&debug=true HTTP/1.1 200 1540"
    analyze_log_with_verification(test_log)