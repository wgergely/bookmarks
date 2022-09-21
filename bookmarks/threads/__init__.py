"""Multi-threading utility classes and methods.

Certain expensive data load happens on secondary worker threads. Each thread is
assigned a single worker class instance and a thread data queue.

The workers usually consume *weakref.ref* objects that derive from base data loaded
by the list models. See :attr:`bookmarks.threads.threads.THREADS` for queue, worker and
thread definitions.



"""