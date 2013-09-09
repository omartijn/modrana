#
# threads.py:  anaconda thread management
#
# modified for use by modRana
#
# Copyright (C) 2012
# Red Hat, Inc.  All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author(s):  Chris Lumens <clumens@redhat.com>
#
# modified for use with modRana by: Martin Kolman
#import logging
#log = logging.getLogger("modRana")
# until modRana has a proper logging structure,
# use a fake stdout log
from __future__ import with_statement # for python 2.5
import sys

class FakeLog(object):
    def info(self, message):
        print("INFO:" + message)

    def debug(self, message):
        print("DEBUG:" + message)

    def error(self, message):
        print("ERROR:" + message)


log = FakeLog()

import threading
from core.signal import Signal


class ThreadManager(object):
    """A singleton class for managing threads and processes.

       Notes:
       THE INSTANCE HAS TO BE CREATED IN THE MAIN THREAD!

       This manager makes one assumption that contradicts python's
       threading module documentation.  In this class, we assume that thread
       names are unique and meaningful.  This is an okay assumption for us
       to make given that anaconda is only ever going to have a handful of
       special purpose threads.
    """

    def __init__(self):
        self._objs = {}
        self._globalIndex = 0
        self._errors = {}
        self._main_thread = threading.currentThread()
        # signals
        self.threadStatusChanged = Signal()
        self.threadProgressChanged = Signal()
        self.threadRemoved = Signal()


    def __call__(self):
        return self

    def _getDuplicateName(self, name):
        """Get a not yet used index for the given duplicate thread
        name, going from 1 up, if there are OVER 9000 THREADS
        with the same base name, give up and use a global index
        """
        index = 1
        while index < 9000:
            threadName = "%s_%d" % (name, index)
            if threadName in self._objs:
                index+=1
            else:
                return threadName
        # this situation should be very unlikely
        log.debug("thread manager: over 9000 threads with the same base name, seriously ?")
        log.debug("thread manager: using global index...")
        index = self._globalIndex
        self._globalIndex+=1
        return "%s_global_index_%d" % (name, index)

    def add(self, obj):
        """Given a Thread or Process object, add it to the list of known objects
           and start it.  It is assumed that obj.name is unique and descriptive.
        """
        if obj.name in self._objs:
            obj.name = self._getDuplicateName(obj.name)

        self._objs[obj.name] = obj
        self._errors[obj.name] = None
        obj.start()

    def remove(self, name):
        """Removes a thread from the list of known objects.  This should only
           be called when a thread exits, or there will be no way to get a
           handle on it.
        """
        thread = self._objs.pop(name)
        threadHasCallback = False
        try:
            threadHasCallback = thread.callback
        except Exception:
            # not a thread ?
            log.debug("threads: no callback or not a thread ?")

        if threadHasCallback:
            # trigger the threadRemoved signal
            self.threadRemoved(name)

    def exists(self, name):
        """Determine if a thread or process exists with the given name."""
        return name in self._objs

    def get(self, name):
        """Given an object name, see if it exists and return the object.
           Return None if no such object exists.  Additionally, this method
           will re-raise any uncaught exception in the thread.
        """
        obj = self._objs.get(name)
        if obj:
            self.raise_error(name)

        return obj

    def wait(self, name):
        """Wait for the thread to exit and if the thread exited with an error
           re-raise it here.
        """
        if self.exists(name):
            self.get(name).join()

        self.raise_error(name)


    def cancel_thread(self, thread_name):
        """Cancel a a thread - cancel callback for given thread

        :param thread_name: thread to cancel
        :type thread_name: str
        """
        try:
            # get thread for the given task
            thread_instance = self.get(thread_name)
            if thread_instance:
                # cancel its callback
                thread_instance.callback = None
                print("threads: thread %s cancelled" % thread_name)
        except Exception:
            import sys
            print("notification: exception canceling thread"
                  " callback for %s" % thread_name)
            e = sys.exc_info()[1]
            print(e)



    def set_error(self, name, *exc_info):
        """Set the error data for a thread

           The exception data is expected to be the tuple from sys.exc_info()
        """
        self._errors[name] = exc_info

    def get_error(self, name):
        """Get the error data for a thread using its name
        """
        return self._errors.get(name)

    def any_errors(self):
        """Return True of there have been any errors in any threads
        """
        return any(self._errors.values())

    def raise_error(self, name):
        """If a thread has failed due to an exception, raise it into the main
           thread.
        """
        if self._errors.get(name):
            raise self._errors[name][0](self._errors[name][1]).with_traceback(self._errors[name][2])

    def in_main_thread(self):
        """Return True if it is run in the main thread."""
        cur_thread = threading.currentThread()
        return cur_thread is self._main_thread


class ModRanaThread(threading.Thread):
    """A threading.Thread subclass that exists only for a couple purposes:

       (1) Make exceptions that happen in a thread invoke our exception handling
           code as well.  Otherwise, threads will silently die and we are doing
           a lot of complicated code in them now.

       (2) Remove themselves from the thread manager when completed.

       (3) All created threads are made daemonic, which means anaconda will quit
           when the main process is killed.
    """

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.daemon = True
        self._status = None  # string describing current state of the thread
        self._progress = None  # floating point value from 0.1 to 1.0
        self._stateLock = threading.Lock()
        self._callback = self._nop()
        self.target = self._nop()  # payload goes here
        # Python 2.5 on Maemo 5 is missing the name and ident properties
        if sys.version_info[:2] <= (2, 5):
            self.name = self.getName()
            import thread  # not needed outside of Python 2.5
            # (also not valid outside of Python 2.5,
            # thread has been renamed to _thread in Python 3)
            self.ident = thread.get_ident()

    def _nop(self, *args, **kwargs):
        """A placeholder method that consumes any arguments
        and notifies about being used"""
        pass

    @property
    def status(self):
        with self._stateLock:
            return self._status

    @status.setter
    def status(self, value):
        with self._stateLock:
            self._status = value
            # needs to be outside of the lock
        # to prevent deadlocks when signal handler
        # wants to access the property
        if self.callback:
            threadMgr.threadStatusChanged(self.name, value)

    @property
    def progress(self):
        with self._stateLock:
            return self._progress

    @progress.setter
    def progress(self, value):
        with self._stateLock:
            self._progress = value
            # needs to be outside of the lock
        # to prevent deadlocks when signal handler
        # wants to access the property
        if self.callback:
            threadMgr.threadProgressChanged(self.name, value)

    @property
    def callback(self):
        """The callback property contains the optional
        callback handler for this threads target/payload.
        Even if a callback is already set, if it is set
        to None or False during processing, the callback will
        not be called.
        Using this, a request running in a thread can
        be cancelled or redirected to another callback."""
        return self._callback

    @callback.setter
    def callback(self, value):
        self._callback = value

    def run(self, *args, **kwargs):
        # http://bugs.python.org/issue1230540#msg25696
        import sys

        log.info("Running Thread: %s (%s)" % (self.name, self.ident))
        try:
            threading.Thread.run(self, *args, **kwargs)
            self._conditionalCallback(self.target())
        except KeyboardInterrupt:
            raise
        except:
            threadMgr.set_error(self.name, *sys.exc_info())
            sys.excepthook(*sys.exc_info())
        finally:
            threadMgr.remove(self.name)
            log.info("Thread Done: %s (%s)" % (self.name, self.ident))

    def _conditionalCallback(self, *args, **kwargs):
        """Used as a "wrapper" for the real callback.
        Enables cancelling the calling of the callback while the task is not yet done"""
        if self.callback:
            self.callback(*args, **kwargs)

def initThreading():
    """Set up threading for anaconda's use. This method must be called before
       any GTK or threading code is called, or else threads will only run when
       an event is triggered in the GTK main loop. And IT HAS TO BE CALLED IN
       THE MAIN THREAD.
    """
    # from gi.repository import GObject
    # GObject.threads_init()

    # modRana:
    # corresponding code was moved to the GTK module
    # as modRana needs to work with non-GTK GUIs

    global threadMgr
    threadMgr = ThreadManager()


threadMgr = None
