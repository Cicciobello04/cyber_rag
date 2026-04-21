from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse

from v0_2.services.analysis_engine import UnifiedAnalysisEngine
from v0_2.services.file_ingestion import FileIngestionError, FileIngestionService
from v0_2.storage.report_store import ReportStore

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = BASE_DIR / "uploads"
DB_DIR = BASE_DIR / "chroma_db"
HISTORY_FILE = BASE_DIR / "storage" / "history.json"

app = FastAPI(title="Cyber RAG v0_2 UI")
ingestion = FileIngestionService(str(UPLOAD_DIR))
engine = UnifiedAnalysisEngine(db_dir=str(DB_DIR))
store = ReportStore(str(HISTORY_FILE))


def _page(title: str, body: str) -> HTMLResponse:
    html = f"""
    <html><head><meta charset='utf-8'><title>{title}</title></head>
    <body style='font-family: Arial, sans-serif; margin: 24px;'>
      <h1>{title}</h1>
      <p><a href='/'>Upload</a> | <a href='/history'>Storico analisi</a></p>
      {body}
    </body></html>
    """
    return HTMLResponse(content=html)


@app.get("/", response_class=HTMLResponse)
async def upload_page() -> HTMLResponse:
    return _page(
        "Cyber RAG v0_2 - Upload",
        """
        <form action='/analyze' method='post' enctype='multipart/form-data'>
          <p><label>File (singolo o multiplo): <input type='file' name='files' multiple required></label></p>
          <p><label>Contesto: <input type='text' name='context' style='width: 420px;'></label></p>
          <p>
            <label>Priorità:
              <select name='priority'>
                <option value='low'>low</option>
                <option value='medium' selected>medium</option>
                <option value='high'>high</option>
              </select>
            </label>
          </p>
          <p>
            <label>Modalità:
              <select name='mode'>
                <option value='immediate' selected>immediate</option>
                <option value='batch'>batch</option>
              </select>
            </label>
          </p>
          <button type='submit'>Avvia analisi</button>
        </form>
        """,
    )


@app.post("/analyze", response_class=HTMLResponse)
async def analyze_files(
    files: List[UploadFile] = File(...),
    context: str = Form(default=""),
    priority: str = Form(default="medium"),
    mode: str = Form(default="immediate"),
) -> HTMLResponse:
    results = []

    for uf in files:
        try:
            uploaded = await ingestion.ingest_upload(uf)
            result = engine.analyze(uploaded, mode=mode, context=context, priority=priority)
        except FileIngestionError as exc:
            result = {
                "analysis_id": "N/A",
                "original_filename": uf.filename,
                "status": "failed",
                "error": str(exc),
            }
        except Exception as exc:
            result = {
                "analysis_id": "N/A",
                "original_filename": uf.filename,
                "status": "failed",
                "error": f"Errore interno: {exc}",
            }

        if isinstance(result, dict):
            results.append(result)
        else:
            data = result.model_dump()
            store.add(data)
            results.append(data)

    items = []
    for r in results:
        link = ""
        if r.get("analysis_id") and r.get("analysis_id") != "N/A":
            link = f" | <a href='/results/{r['analysis_id']}'>apri risultato</a>"
        items.append(
            f"<li><strong>{r.get('original_filename')}</strong> - {r.get('status', 'unknown')}"
            f"{link}<br><small>{r.get('error', r.get('executive_summary', ''))}</small></li>"
        )

    return _page("Analisi completata", f"<ul>{''.join(items)}</ul><p><a href='/history'>Vai allo storico</a></p>")


@app.get("/results/{analysis_id}", response_class=HTMLResponse)
async def show_result(analysis_id: str) -> HTMLResponse:
    result = store.get(analysis_id)
    if not result:
        return _page("Risultato non trovato", f"<p>ID {analysis_id} non presente nello storico.</p>")

    evidence_rows = "".join(
        [
            f"<li>{e.get('item_id')} - {e.get('name')} [{e.get('source_type')}]"
            f" (score: {e.get('score')})</li>"
            for e in result.get("evidence", [])
        ]
    )
    actions = "".join([f"<li>{a}</li>" for a in result.get("immediate_actions", [])])

    body = f"""
    <p><strong>File:</strong> {result.get('original_filename')}</p>
    <p><strong>Tipo:</strong> {result.get('file_type')}</p>
    <p><strong>Stato:</strong> {result.get('status')}</p>
    <p><strong>Summary:</strong> {result.get('executive_summary')}</p>
    <p><strong>Pattern principale:</strong> {result.get('most_likely_pattern_id')}</p>
    <p><strong>Predizione:</strong> {result.get('predicted_next_step')}</p>
    <p><strong>Azioni immediate:</strong></p><ul>{actions}</ul>
    <p><strong>Conclusione:</strong> {result.get('raw_conclusion')}</p>
    <p><strong>Evidenze retrieval:</strong></p><ul>{evidence_rows}</ul>
    """
    return _page(f"Risultato {analysis_id}", body)


@app.get("/history", response_class=HTMLResponse)
async def history() -> HTMLResponse:
    items = store.list_all()
    rows = []
    for item in items:
        aid = item.get("analysis_id", "N/A")
        rows.append(
            f"<li><a href='/results/{aid}'>{aid}</a> - {item.get('original_filename')} - "
            f"{item.get('status')} - {item.get('created_at')}</li>"
        )

    return _page("Storico analisi", f"<ul>{''.join(rows) if rows else '<li>Nessuna analisi salvata.</li>'}</ul>")
