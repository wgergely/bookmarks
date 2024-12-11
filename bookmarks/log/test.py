import json
import logging
import os
import tempfile
import threading
import time
import unittest

from PySide2 import QtCore

from .lib import *
from .lib import ERR_LOG_PATH, init_log_handlers


class TestLog(unittest.TestCase):
    """Tests for the logging module."""

    def setUp(self):
        set_logging_level(logging.INFO)
        init_log()

    def tearDown(self):
        teardown_log()

    def test_init_handlers(self):
        """Ensure handlers are initialized."""
        self.assertIsNotNone(get_handler(HandlerType.Memory))
        self.assertIsNotNone(get_handler(HandlerType.Console))
        self.assertIsNotNone(get_handler(HandlerType.File))

    def test_logging_messages_and_retrieval(self):
        """Test logging messages and retrieval from memory tank."""
        debug("test", "Debug message")  # Below INFO, should not be recorded
        info("test", "Info message")  # At INFO level, should be recorded
        warning("test", "Warning message")
        error("test", "Error message")

        # Retrieve and remove warnings/errors
        records = get_records(remove=True)
        self.assertEqual(len(records), 2)
        self.assertTrue(any("Warning message" in r for r in records))
        self.assertTrue(any("Error message" in r for r in records))

        # After removal, subsequent call should return no warnings/errors
        self.assertEqual(len(get_records()), 0)

    def test_get_records_without_init_raises_error(self):
        """Ensure calling get_records without init raises RuntimeError."""
        teardown_log()
        with self.assertRaises(RuntimeError):
            get_records()

    def test_clear_records(self):
        """Test clearing records from memory tank."""
        warning("test", "Some warning")
        self.assertEqual(len(get_records(level=logging.WARNING)), 1)
        # Remove the warning and check again
        self.assertEqual(len(get_records(level=logging.WARNING, remove=True)), 1)
        # Now no warnings should remain
        self.assertEqual(len(get_records(level=logging.WARNING)), 0)
        self.assertEqual(len(get_records(level=logging.WARNING)), 0)

    def test_get_handler_valid(self):
        """Test retrieving a valid handler."""
        mem_handler = get_handler(HandlerType.Memory)
        self.assertIsNotNone(mem_handler)

    def test_get_handler_invalid(self):
        """Test retrieving an invalid handler."""
        with self.assertRaises(ValueError):
            get_handler("NotAHandlerType")

    def test_set_logging_level(self):
        """Test updating the global logging level."""
        set_logging_level(logging.WARNING)
        debug("test", "Debug message")  # below WARNING
        info("test", "Info message")  # below WARNING
        warning("test", "Warning message")

        # Retrieve warnings/errors without removing first
        records = get_records(level=logging.WARNING, remove=True)
        self.assertEqual(len(records), 1)
        self.assertTrue("Warning message" in records[0])

        # Restore level
        set_logging_level(logging.DEBUG)

    def test_concurrent_logging(self):
        """Test concurrent logging from multiple threads."""

        def log_messages(name, msg_prefix, count):
            for i in range(count):
                info(name, f"{msg_prefix} {i}")

        threads = []
        thread_count = 5
        messages_per_thread = 50

        for i in range(thread_count):
            t = threading.Thread(target=log_messages, args=("test_thread", f"Thread-{i}", messages_per_thread))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Wait a moment for any logging I/O operations
        time.sleep(0.1)

        # Verify all info logs are captured
        recs = get_records(level=logging.INFO)
        self.assertEqual(len(recs), thread_count * messages_per_thread)

    def test_file_handler_rotation(self):
        """Test that the file handler rotates files after exceeding max size."""
        # Teardown and re-init with small max_bytes to trigger rotation.
        teardown_log()

        max_bytes = 1024
        backup_count = 2
        init_log_handlers(max_bytes=max_bytes, maxlen=1000, backup_count=backup_count)
        logger = get_logger("rotation_test")

        # Write enough logs to exceed max_bytes
        for i in range(200):
            logger.warning("This is a rotation test message of some length %d", i)

        # Wait a moment for filesystem writes
        time.sleep(0.5)
        files = [f for f in os.listdir(os.path.dirname(ERR_LOG_PATH)) if "error.log" in f]
        self.assertTrue(len(files) > 1, "No rotated files found.")

    def test_qt_message_handler(self):
        """Test that Qt messages are redirected to Python logging."""
        set_logging_level(logging.DEBUG)

        QtCore.qDebug("Qt Debug")
        QtCore.qWarning("Qt Warning")
        QtCore.qCritical("Qt Critical")

        recs = get_records(level=logging.DEBUG, remove=True)
        self.assertTrue(any("Qt Debug" in r for r in recs))
        self.assertTrue(any("Qt Warning" in r for r in recs))
        self.assertTrue(any("Qt Critical" in r for r in recs))

    def test_global_log_levels(self):
        """Test logging behavior across all global log levels."""
        for global_level in [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]:
            teardown_log()
            init_log()  # Re-init with default settings
            set_logging_level(global_level)

            # Log one message at each level
            debug("test_levels", "Debug level message")
            info("test_levels", "Info level message")
            warning("test_levels", "Warning level message")
            error("test_levels", "Error level message")
            critical("test_levels", "Critical level message")

            # Retrieve all logs at the lowest threshold (DEBUG) to see what was recorded
            recs = get_records(level=logging.DEBUG, remove=True)

            # Check which messages should have appeared given the global level
            # Messages at or above global_level should appear
            expected = []
            if global_level <= logging.DEBUG:
                expected.append("Debug level message")
            if global_level <= logging.INFO:
                expected.append("Info level message")
            if global_level <= logging.WARNING:
                expected.append("Warning level message")
            if global_level <= logging.ERROR:
                expected.append("Error level message")
            if global_level <= logging.CRITICAL:
                expected.append("Critical level message")

            # Verify all expected appear, and no extras do
            for msg in expected:
                self.assertTrue(any(msg in r for r in recs),
                                f"Expected '{msg}' to appear at global level {logging.getLevelName(global_level)}")

            # Also ensure no messages below the global threshold appear
            below_threshold = [m for m in
                               ["Debug level message", "Info level message",
                                "Warning level message", "Error level message",
                                "Critical level message"]
                               if m not in expected]

            for msg in below_threshold:
                self.assertFalse(any(msg in r for r in recs),
                                 f"Did not expect '{msg}' to appear at global level {logging.getLevelName(global_level)}")

    def test_save_tank_to_file_json(self):
        """Test saving the memory tank contents to a JSON file."""
        warning("test_save_json", "Multiline\nWarning Message")
        error("test_save_json", "Single line error message")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp_json:
            tmp_json_path = tmp_json.name

        save_tank_to_file(tmp_json_path)

        with open(tmp_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # We should have two entries
        self.assertEqual(len(data), 2)
        # The messages should be formatted, check presence of keywords
        self.assertTrue(any("Warning" in entry["message"] for entry in data))
        self.assertTrue(any("error" in entry["message"] for entry in data))

        os.remove(tmp_json_path)

    def test_save_tank_to_file_text(self):
        """Test saving the memory tank contents to a .log file with raw messages."""
        warning("test_save_text", "Multiline\nWarning Message")
        error("test_save_text", "Single line error message")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as tmp_log:
            tmp_log_path = tmp_log.name

        save_tank_to_file(tmp_log_path)

        # When reading as text, just read the whole file and check for the substrings
        with open(tmp_log_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check that both messages appear in the file content
        self.assertIn("Multiline\nWarning Message", content)
        self.assertIn("Single line error message", content)

        os.remove(tmp_log_path)


if __name__ == '__main__':
    unittest.main()
