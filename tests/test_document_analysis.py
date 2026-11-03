import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf as fitz
from docx import Document

from app.document_analysis import (
    DocumentAnalysisError,
    analyze_document_text,
    extract_document_text,
    is_valid_docx_file,
)


class DocumentTextExtractionTests(unittest.TestCase):
    def test_extracts_text_and_page_reference_from_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "evidence.pdf"
            document = fitz.open()
            page = document.new_page()
            page.insert_text((72, 72), "Degree issued by Example University")
            document.save(path)
            document.close()

            text = extract_document_text(path)

        self.assertIn("[Trang 1]", text)
        self.assertIn("Degree issued by Example University", text)

    def test_extracts_paragraphs_and_tables_from_docx(self) -> None:
        document = Document()
        document.add_paragraph("Bằng thạc sĩ")
        table = document.add_table(rows=1, cols=2)
        table.cell(0, 0).text = "Đơn vị cấp"
        table.cell(0, 1).text = "Đại học mẫu"
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "evidence.docx"
            document.save(path)

            text = extract_document_text(path)
            self.assertTrue(is_valid_docx_file(path.read_bytes()))

        self.assertIn("[Đoạn 1] Bằng thạc sĩ", text)
        self.assertIn("[Bảng 1, hàng 1] Đơn vị cấp | Đại học mẫu", text)

    def test_rejects_malformed_docx_and_scanned_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "evidence.docx"
            path.write_bytes(b"not a docx archive")
            with self.assertRaises(DocumentAnalysisError) as malformed:
                extract_document_text(path)
            self.assertEqual(malformed.exception.code, "invalid_docx")
            self.assertFalse(is_valid_docx_file(b"not a docx archive"))

            scanned_pdf = Path(temporary_directory) / "scan.pdf"
            document = fitz.open()
            document.new_page()
            document.save(scanned_pdf)
            document.close()
            with self.assertRaises(DocumentAnalysisError) as no_text:
                extract_document_text(scanned_pdf)
            self.assertEqual(no_text.exception.code, "no_text")

    def test_rejects_text_over_the_configured_limit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "evidence.pdf"
            document = fitz.open()
            page = document.new_page()
            page.insert_text((72, 72), "A" * 100)
            document.save(path)
            document.close()

            with (
                patch("app.document_analysis.MAX_DOCUMENT_TEXT_CHARS", 30),
                self.assertRaises(DocumentAnalysisError) as too_large,
            ):
                extract_document_text(path)

        self.assertEqual(too_large.exception.code, "text_too_large")


class LocalModelTests(unittest.IsolatedAsyncioTestCase):
    async def test_requires_an_installed_model_name(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TEACHER_MANAGEMENT_OLLAMA_MODEL": "",
                "TEACHER_MANAGEMENT_OLLAMA_URL": "http://127.0.0.1:11434",
            },
        ):
            with self.assertRaises(DocumentAnalysisError) as error:
                await analyze_document_text("sample")

        self.assertEqual(error.exception.code, "missing_ollama_model")

    async def test_rejects_non_loopback_ollama_endpoint(self) -> None:
        with patch.dict(
            os.environ,
            {
                "TEACHER_MANAGEMENT_OLLAMA_MODEL": "test-model",
                "TEACHER_MANAGEMENT_OLLAMA_URL": "http://example.com:11434",
            },
        ):
            with self.assertRaises(DocumentAnalysisError) as error:
                await analyze_document_text("sample")

        self.assertEqual(error.exception.code, "invalid_ollama_url")

    async def test_parses_structured_response_from_local_ollama(self) -> None:
        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, str]:
                return {
                    "response": (
                        '{"summary":"Tóm tắt","extracted_information":['
                        '{"field":"Đơn vị cấp","value":"Đại học mẫu",'
                        '"source":"[Đoạn 2]"}]}'
                    )
                }

        class FakeClient:
            def __init__(self, **_: object) -> None:
                pass

            async def __aenter__(self) -> "FakeClient":
                return self

            async def __aexit__(self, *_: object) -> None:
                return None

            async def post(self, url: str, json: dict[str, object]) -> FakeResponse:
                self_url = "http://127.0.0.1:11434/api/generate"
                if url != self_url:
                    raise AssertionError(f"Unexpected Ollama URL: {url}")
                if "sample" not in str(json["prompt"]):
                    raise AssertionError("Document text was not sent to local Ollama.")
                return FakeResponse()

        with (
            patch.dict(
                os.environ,
                {
                    "TEACHER_MANAGEMENT_OLLAMA_MODEL": "test-model",
                    "TEACHER_MANAGEMENT_OLLAMA_URL": "http://127.0.0.1:11434",
                },
            ),
            patch("app.document_analysis.httpx.AsyncClient", FakeClient),
        ):
            result = await analyze_document_text("sample")

        self.assertEqual(result.summary, "Tóm tắt")
        self.assertEqual(result.extracted_information[0].value, "Đại học mẫu")


if __name__ == "__main__":
    unittest.main()
