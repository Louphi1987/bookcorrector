from __future__ import annotations

import pathlib

from flask import Blueprint, jsonify, render_template, request, send_file
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from .correction_engine import CorrectionEngine
from .exporter import build_docx_report
from .file_loader import SUPPORTED_EXTENSIONS, load_uploaded_document
from .transform import build_corrected_segments


main_bp = Blueprint("main", __name__)
engine = CorrectionEngine()


@main_bp.get("/")
def index():
    return render_template("index.html", supported_extensions=sorted(SUPPORTED_EXTENSIONS))


@main_bp.get("/health")
def health():
    return jsonify({"status": "ok"})


@main_bp.post("/api/analyze")
def analyze():
    uploaded = request.files.get("file")
    raw_text = request.form.get("text", "").strip()

    if uploaded and uploaded.filename:
        filename = secure_filename(uploaded.filename) or "manuscrit.txt"
        extension = pathlib.Path(filename).suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            return jsonify({"error": "Format non pris en charge."}), 400
        text = load_uploaded_document(filename, uploaded.read())
    elif raw_text:
        filename = "manuscrit-colle.txt"
        text = raw_text
    else:
        return jsonify({"error": "Ajoute un fichier ou colle du texte avant l'analyse."}), 400

    result = engine.analyze(text)
    return jsonify(result.to_payload(filename))


@main_bp.post("/api/export-docx")
def export_docx():
    payload = request.get_json(silent=True) or {}
    original_text = str(payload.get("original_text") or "")
    issues = payload.get("issues") or []
    selected_ids = set(payload.get("selected_ids") or [])
    filename = secure_filename(str(payload.get("filename") or "manuscrit")) or "manuscrit"

    if not original_text or not isinstance(issues, list):
        return jsonify({"error": "Export impossible: donnees manquantes."}), 400

    corrected_segments = build_corrected_segments(original_text, issues, selected_ids)

    document_bytes = build_docx_report(
        title=filename,
        original_text=original_text,
        corrected_segments=corrected_segments,
        issues=issues,
        selected_ids=selected_ids,
    )
    output_name = pathlib.Path(filename).stem + "_corrige.docx"
    return send_file(
        bytes_to_stream(document_bytes),
        as_attachment=True,
        download_name=output_name,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@main_bp.errorhandler(RequestEntityTooLarge)
def file_too_large(_error):
    return jsonify({"error": "Fichier trop volumineux. Limite actuelle: 6 Mo."}), 413


def bytes_to_stream(data: bytes):
    import io

    return io.BytesIO(data)
