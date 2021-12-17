import traceback


def get_stacktrace_from_exception(e: Exception):
    return "".join(traceback.TracebackException.from_exception(e).format())
