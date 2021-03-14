import unittest

import bookmarks.test.test_common
import bookmarks.test.test_context
import bookmarks.test.test_bookmark_db
import bookmarks.test.test_images
import bookmarks.test.test_settings
import bookmarks.test.test_session_lock
import bookmarks.test.test_templates
import bookmarks.test.test_main
import bookmarks.test.test_bookmark_editor
import bookmarks.test.test_actions


if __name__ == '__main__':
    loader = unittest.TestLoader()
    cases = (
        loader.loadTestsFromTestCase(bookmarks.test.test_context.Test),
        loader.loadTestsFromTestCase(bookmarks.test.test_common.Test),
        loader.loadTestsFromTestCase(bookmarks.test.test_bookmark_db.Test),
        loader.loadTestsFromTestCase(bookmarks.test.test_images.Test),
        loader.loadTestsFromTestCase(bookmarks.test.test_templates.Test),
        loader.loadTestsFromTestCase(bookmarks.test.test_main.Test),
        loader.loadTestsFromTestCase(bookmarks.test.test_bookmark_editor.Test),
        loader.loadTestsFromTestCase(bookmarks.test.test_actions.Test),
        loader.loadTestsFromTestCase(bookmarks.test.test_session_lock.Test),
        loader.loadTestsFromTestCase(bookmarks.test.test_actions.TestWidgetActions),
    )
    suite = unittest.TestSuite(cases)
    unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
