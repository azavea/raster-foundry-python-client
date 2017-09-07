import logging

from . import NOTEBOOK_SUPPORT


def check_notebook(f):
    def no_op(*args, **kwargs):
        logging.warn('This function requires jupyter notebook and ipyleaflet')
        return

    if not NOTEBOOK_SUPPORT:
        return no_op
    else:
        return f
