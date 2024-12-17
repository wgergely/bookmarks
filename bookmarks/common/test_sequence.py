"""Comprehensive unit tests for the sequence utility module.

These tests cover a broad and comprehensive range of scenarios, aiming for
robustness required in a production environment:

- Normal sequences (typical numeric padding).
- Collapsed sequences (with and without padded numbering).
- Invalid inputs (None, wrong types, missing roles, ambiguous patterns).
- Unicode and special characters in paths, including sequences and collapsed sequences.
- Platform-specific path separators (forward slash, backslash, mixed).
- Version numbers and complex prefixes/suffixes, sequence not at the end of filename.
- Large sequence numbers and ambiguous patterns.
- Various path schemes:
  - Windows drive letters (C:/, C:\\)
  - UNC paths (\\\\server\\share\\...)
  - Unix-like paths (/mnt/prod/...)
  - URIs and network paths (file://, s3://, ftp://)
  - Non-path filenames
- Ensuring proxy paths handle all these cases gracefully.

"""
import threading
import unittest
import weakref
from queue import Queue
from unittest.mock import MagicMock

from PySide2 import QtCore

from . import common
from . import sequence


class TestSequenceUtilsComprehensive(unittest.TestCase):
    def setUp(self):
        common.PathRole = 256
        common.SequenceRole = 257
        common.FramesRole = 258

    def test_normal_sequences(self):
        p = "C:/project/shots/shot_001.exr"
        self.assertFalse(sequence.is_collapsed(p))
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "001")

        p = "C:\\project\\shots\\shot_001.exr"
        self.assertFalse(sequence.is_collapsed(p))
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "001")

        # Proxy normalizes backslashes
        pp = sequence.proxy_path(p)
        self.assertIn(sequence.SEQPROXY, pp)
        self.assertFalse('\\' in pp)

    def test_collapsed_sequences(self):
        p = "C:/path/image_<<001-010>>.exr"
        self.assertTrue(sequence.is_collapsed(p))
        start = sequence.get_sequence_start_path(p)
        self.assertEqual(start, "C:/path/image_001.exr")
        end = sequence.get_sequence_end_path(p)
        self.assertEqual(end, "C:/path/image_010.exr")

        # Without zero-padding
        p = "C:/path/image_<<1-3>>.jpg"
        start = sequence.get_sequence_start_path(p)
        self.assertEqual(start, "C:/path/image_1.jpg")
        end = sequence.get_sequence_end_path(p)
        self.assertEqual(end, "C:/path/image_3.jpg")

    def test_invalid_inputs(self):
        with self.assertRaises(TypeError):
            sequence.is_collapsed(123)
        with self.assertRaises(TypeError):
            sequence.get_sequence(None)
        with self.assertRaises(RuntimeError):
            sequence.get_sequence("C:/path/image_<<001-003>>.exr")
        with self.assertRaises(TypeError):
            sequence.get_sequence_start_path(None)
        with self.assertRaises(TypeError):
            sequence.get_sequence_end_path(None)

        # Invalid dict to proxy_path
        with self.assertRaises(TypeError):
            sequence.proxy_path({common.PathRole: 123})
        # Missing PathRole
        with self.assertRaises(TypeError):
            sequence.proxy_path({})
        # Invalid object type
        with self.assertRaises(TypeError):
            sequence.proxy_path(99)

    def test_unicode_and_special_characters(self):
        p = "C:/प्रोजेक्ट/शॉट_<<001-010>>.png"
        self.assertTrue(sequence.is_collapsed(p))
        self.assertIn(sequence.SEQPROXY, sequence.proxy_path(p))

        p = "C:/path/ima$ge_0001@.png"
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "0001")

    def test_complex_prefixes_suffixes(self):
        p = "C:/project/shots/image_001_backup.png"
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "001")

        p = "C:/project/shot010_camera05_v100.png"
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "100")

        p = "C:/show/ep01/shot010_v002_001.png"
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "001")

        p = "C:/show/ep01/shot015_v010.0005_exr_sequence.png"
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "0005")

    def test_large_numbers_ambiguous_patterns(self):
        p = "C:/path/shot_10_20_001.png"
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "001")

        p = "C:/path/no_sequence_here.txt"
        self.assertIsNone(sequence.get_sequence(p))

        p = "C:/path/image_<<001-100>.exr"  # Missing '>'
        self.assertIsNone(sequence.is_collapsed(p))

        p = "C:/path/image_999999999.png"
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "999999999")

        # Sequence in extension
        p = "C:/path/image_010.exr2"
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "010")

    def test_mixed_separators(self):
        p = "C:/project\\shots/shot_v010.0005.dpx"
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "0005")

    def test_get_sequence_paths(self):
        # Proper collapsed index
        mock_index = MagicMock(spec=QtCore.QModelIndex)
        mock_index.data.side_effect = lambda role: {
            common.PathRole: "C:/path/image_<<010-012>>.png",
            common.SequenceRole: sequence.GetSequenceRegex.search("C:/path/image_010.png"),
            common.FramesRole: ["010", "011", "012"]
        }.get(role, None)
        paths = sequence.get_sequence_paths(mock_index)
        self.assertEqual(paths, [
            "C:/path/image_010.png",
            "C:/path/image_011.png",
            "C:/path/image_012.png"
        ])

        # Non-collapsed index with no sequence
        mock_index = MagicMock(spec=QtCore.QModelIndex)
        mock_index.data.side_effect = lambda role: {
            common.PathRole: "C:/path/final_render.png"
        }.get(role, None)
        paths = sequence.get_sequence_paths(mock_index)
        self.assertEqual(paths, ["C:/path/final_render.png"])

    def test_weakref_proxy_path(self):
        d = common.DataDict({common.PathRole: "C:/path/image_010.dpx"})
        w = weakref.ref(d)
        pp = sequence.proxy_path(w)
        self.assertIn(sequence.SEQPROXY, pp)

    def test_unc_paths(self):
        p = "\\\\server\\share\\project\\shot_050.dpx"
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "050")
        pp = sequence.proxy_path(p)
        self.assertIn(sequence.SEQPROXY, pp)
        self.assertFalse('\\' in pp)

        # Collapsed UNC path
        p = "\\\\server\\share\\frames_<<010-020>>.exr"
        self.assertTrue(sequence.is_collapsed(p))
        start = sequence.get_sequence_start_path(p)
        self.assertEqual(start, "\\\\server\\share\\frames_010.exr")

    def test_unix_like_paths(self):
        p = "/mnt/prod/project/sequence_010.exr"
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "010")

        p = "/mnt/prod/project/image_<<001-100>>.exr"
        self.assertTrue(sequence.is_collapsed(p))
        end = sequence.get_sequence_end_path(p)
        self.assertEqual(end, "/mnt/prod/project/image_100.exr")

    def test_file_uri_scheme(self):
        p = "file:///path/to/shot_001.tif"
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "001")

        p = "file:///path/to/frames_<<001-003>>.png"
        self.assertTrue(sequence.is_collapsed(p))
        end = sequence.get_sequence_end_path(p)
        self.assertEqual(end, "file:///path/to/frames_003.png")

    def test_network_uris_s3(self):
        p = "s3://bucket-name/project/shot_0005.exr"
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "0005")

        p = "s3://bucket/frames_<<001-002>>.jpg"
        self.assertTrue(sequence.is_collapsed(p))
        start = sequence.get_sequence_start_path(p)
        self.assertEqual(start, "s3://bucket/frames_001.jpg")

    def test_ftp_uris(self):
        p = "ftp://example.com/project/frame_1000.png"
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "1000")

        mock_index = MagicMock(spec=QtCore.QModelIndex)
        seq_match = sequence.GetSequenceRegex.search("ftp://example.com/images_010.exr")
        mock_index.data.side_effect = lambda role: {
            common.PathRole: "ftp://example.com/images_<<010-012>>.exr",
            common.SequenceRole: seq_match,
            common.FramesRole: ["010", "011", "012"]
        }.get(role, None)
        paths = sequence.get_sequence_paths(mock_index)
        self.assertEqual(paths, [
            "ftp://example.com/images_010.exr",
            "ftp://example.com/images_011.exr",
            "ftp://example.com/images_012.exr"
        ])

    def test_non_path_strings(self):
        p = "image_001.png"
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "001")

        p = "clip_<<001-010>>.mov"
        self.assertTrue(sequence.is_collapsed(p))
        start = sequence.get_sequence_start_path(p)
        self.assertEqual(start, "clip_001.mov")

        p = "someproto://path/image_002.exr"
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "002")

        # Without an extension, should fail match
        p = "C:/path/to/frame_010"
        self.assertIsNone(sequence.get_sequence(p))

    def test_unicode_in_uris_and_network_paths(self):
        p = "s3://बकेट/प्रोजेक्ट/इमेज_001.png"
        m = sequence.get_sequence(p)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(2), "001")

        p = "\\\\सर्वर\\शेयर\\फ़्रेम_<<001-002>>.exr"
        self.assertTrue(sequence.is_collapsed(p))
        end = sequence.get_sequence_end_path(p)
        self.assertEqual(end, "\\\\सर्वर\\शेयर\\फ़्रेम_002.exr")

        p = "file:///पथ/फ्रेम_<<01-02>>.jpg"
        self.assertTrue(sequence.is_collapsed(p))
        start = sequence.get_sequence_start_path(p)
        self.assertEqual(start, "file:///पथ/फ्रेम_01.jpg")

    def test_weakref_proxy_with_uri(self):
        d = common.DataDict({common.PathRole: "ftp://server/path/frame_050.dpx"})
        w = weakref.ref(d)
        pp = sequence.proxy_path(w)
        self.assertIn(sequence.SEQPROXY, pp)

    def test_invalid_and_ambiguous_uris(self):
        with self.assertRaises(TypeError):
            sequence.is_collapsed(123.45)

        p = "file:///path/to/name_noNumbersHere.ext"
        self.assertIsNone(sequence.get_sequence(p))

        p = "s3://bucket/folder/frames_<<001-??>>.exr"  # Invalid range
        self.assertIsNone(sequence.is_collapsed(p))

        p = "s3://bucket/folder/frames_<<001-010>>_more_<<011-020>>.exr"
        m = sequence.is_collapsed(p)
        self.assertIsNotNone(m)

        self.assertEqual(m.group(1), "s3://bucket/folder/frames_")
        self.assertEqual(m.group(2), "001-010")
        self.assertEqual(m.group(3), "_more_<<011-020>>.exr")


class TestSequenceUtilsConcurrent(unittest.TestCase):
    def setUp(self):
        common.PathRole = 256
        common.SequenceRole = 257
        common.FramesRole = 258

    def _worker_is_collapsed(self, paths, results_queue):
        for p in paths:
            try:
                res = sequence.is_collapsed(p)
                results_queue.put((p, 'is_collapsed', res))
            except Exception as e:
                results_queue.put((p, 'is_collapsed', e))

    def _worker_get_sequence(self, paths, results_queue):
        for p in paths:
            try:
                res = sequence.get_sequence(p)
                results_queue.put((p, 'get_sequence', res))
            except Exception as e:
                results_queue.put((p, 'get_sequence', e))

    def _worker_proxy_path(self, items, results_queue):
        for v in items:
            try:
                res = sequence.proxy_path(v)
                results_queue.put((v, 'proxy_path', res))
            except Exception as e:
                results_queue.put((v, 'proxy_path', e))

    def test_concurrent_access_is_collapsed(self):
        # Mix of collapsed and non-collapsed paths, unicode, URIs, etc.
        paths = [
            "C:/path/image_001.exr",
            "C:/path/image_<<001-010>>.exr",
            "s3://bucket/frames_<<001-002>>.jpg",
            "\\\\server\\share\\frames_<<010-020>>.exr",
            "/mnt/prod/project/image_<<001-100>>.exr",
            "ftp://example.com/images_010.exr",
            "C:\\path\\frame_100.png",
            "C:/प्रोजेक्ट/शॉट_<<001-010>>.png"
        ]

        results = Queue()
        threads = []
        # Launch multiple threads calling is_collapsed
        for _ in range(5):
            t = threading.Thread(target=self._worker_is_collapsed, args=(paths, results))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        # Check results
        while not results.empty():
            path, method, value = results.get()
            if isinstance(value, Exception):
                self.fail(f"Unexpected exception {value} for {path} in {method}")

    def test_concurrent_access_get_sequence(self):
        paths = [
            "C:/path/image_001.exr",
            "C:/show/ep01/shot010_v002_001.png",
            "C:/path/image_999999999.png",
            "file:///path/to/shot_001.tif",
            "someproto://path/image_002.exr"
        ]

        results = Queue()
        threads = []
        # Launch multiple threads calling get_sequence
        for _ in range(5):
            t = threading.Thread(target=self._worker_get_sequence, args=(paths, results))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        # Check results for correctness
        expected_sequences = {
            "C:/path/image_001.exr": "001",
            "C:/show/ep01/shot010_v002_001.png": "001",
            "C:/path/image_999999999.png": "999999999",
            "file:///path/to/shot_001.tif": "001",
            "someproto://path/image_002.exr": "002"
        }

        while not results.empty():
            path, method, value = results.get()
            if isinstance(value, Exception):
                self.fail(f"Unexpected exception {value} for {path} in {method}")
            else:
                if value:
                    # Check sequence number matches expected
                    seq_num = value.group(2)
                    self.assertEqual(seq_num, expected_sequences[path],
                                     f"Incorrect sequence number for {path}")

    def test_concurrent_proxy_path(self):
        # Prepare a mix of items: strings, dicts, weakrefs
        d = common.DataDict({common.PathRole: "C:/path/image_010.dpx"})
        w = weakref.ref(d)  # Now valid
        items = [
            "C:/path/image_001.png",
            "C:/path/image_<<001-003>>.exr",
            d,
            w,
            "ftp://example.com/images_010.exr"
        ]

        results = Queue()
        threads = []
        # Launch multiple threads calling proxy_path
        for _ in range(5):
            t = threading.Thread(target=self._worker_proxy_path, args=(items, results))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        # Validate proxy paths contain SEQPROXY for sequences and collapsed,
        # and remain unchanged otherwise (except normalized slashes)
        while not results.empty():
            item, method, value = results.get()
            if isinstance(value, Exception):
                self.fail(f"Unexpected exception {value} for {item} in {method}")
            else:
                # Check correctness
                if isinstance(item, dict) or isinstance(item, weakref.ref):
                    # These contain sequences
                    self.assertIn(sequence.SEQPROXY, value)
                elif "<<" in str(item) and ">>" in str(item):
                    # Collapsed sequence
                    self.assertIn(sequence.SEQPROXY, value)
                elif sequence.get_sequence(str(item)):
                    # Normal sequence
                    self.assertIn(sequence.SEQPROXY, value)
                else:
                    # Non-sequence
                    # Just ensure we didn't break it
                    # Non sequence: "ftp://example.com/images_010.exr" is actually a sequence
                    if sequence.get_sequence(str(item)):
                        self.assertIn(sequence.SEQPROXY, value)
                    else:
                        # If truly non-sequence (not likely in this set), it should remain unchanged
                        self.assertNotIn(sequence.SEQPROXY, value)


if __name__ == '__main__':
    unittest.main()
