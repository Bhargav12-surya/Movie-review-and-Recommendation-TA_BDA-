"""Synthetic format/size/privacy fixtures; no real review evidence."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from dataset_tools.recordio import RecordFormatError, iter_records, parse_json


class RecordReaderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def write(self, name, content):
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_json_array_is_streamed_across_unicode_and_token_boundaries(self):
        values = [{"text": "é 🎬"} for _ in range(300)]
        path = self.write("reviews.json", json.dumps(values, ensure_ascii=False))
        self.assertEqual(list(iter_records(path, chunk_size=7)), values)

    def test_json_object_and_jsonl_are_supported(self):
        first = self.write("one.json", '{"id":1}')
        second = self.write("many.jsonl", '\n{"id":1}\n{"id":2}\n')
        self.assertEqual(list(iter_records(first)), [{"id": 1}])
        self.assertEqual(list(iter_records(second)), [{"id": 1}, {"id": 2}])

    def test_trailing_comma_trailing_data_and_scalar_records_rejected(self):
        for index, text in enumerate(('[{"id":1},]', '[{"id":1}]{}', '[1]', '{"id":1} {"id":2}')):
            with self.subTest(text=text):
                with self.assertRaises(RecordFormatError):
                    list(iter_records(self.write(f"bad{index}.json", text), chunk_size=3))

    def test_nonfinite_numbers_and_duplicate_keys_are_rejected(self):
        for text in ('{"value":NaN}', '{"value":Infinity}', '{"value":1e999}', '{"id":1,"id":2}'):
            with self.subTest(text=text):
                with self.assertRaises(RecordFormatError):
                    parse_json(text)

    def test_record_limits_apply_to_utf8_bytes(self):
        path = self.write("large.jsonl", json.dumps({"text": "é" * 30}, ensure_ascii=False))
        with self.assertRaises(RecordFormatError):
            list(iter_records(path, max_record_bytes=50))
        path = self.write("large.json", json.dumps([{"text": "é" * 30}], ensure_ascii=False))
        with self.assertRaises(RecordFormatError):
            list(iter_records(path, max_record_bytes=50, chunk_size=5))

    def test_csv_quoted_newlines_and_header_errors(self):
        path = self.root / "good.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["review_id", "review_text"])
            writer.writeheader()
            writer.writerow({"review_id": "a", "review_text": "line one\nline two"})
        self.assertEqual(list(iter_records(path))[0]["review_text"], "line one\nline two")
        for text in ("id,id\n1,2\n", "id,text\n1\n", "id,text\n1,x,y\n"):
            with self.assertRaises(RecordFormatError):
                list(iter_records(self.write("bad.csv", text)))

    def test_invalid_utf8_and_sanitized_errors(self):
        path = self.root / "private.jsonl"
        path.write_bytes(b'{"text":"private-secret"}\xff\n')
        with self.assertRaises(RecordFormatError) as caught:
            list(iter_records(path))
        self.assertNotIn("private-secret", str(caught.exception))

    def test_json_unpaired_surrogates_rejected(self):
        with self.assertRaises(RecordFormatError):
            parse_json('{"text":"\\ud800"}')


if __name__ == "__main__":
    unittest.main()
