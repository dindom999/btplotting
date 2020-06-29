import logging
from functools import partial
from tornado import gen

from bokeh.io import curdoc
from bokeh.models import Panel, DataTable, TableColumn, ColumnDataSource
from bokeh.layouts import column

handler = None
logger = logging.getLogger(__name__)


class CDSHandler(logging.Handler):

    def __init__(self, level=logging.NOTSET):
        super(CDSHandler, self).__init__(level)
        self._messages = []
        self._idx = {}
        self._cds = {}
        self._cb = {}

    def emit(self, record):
        message = record.message
        self._messages.append(message)
        for doc in self._cds:
            try:
                doc.remove_next_tick_callback(self._cb[doc])
            except ValueError:
                pass
            self._cb[doc] = doc.add_next_tick_callback(
                partial(self._stream_to_cds, doc))

    def get_cds(self, doc):
        if doc not in self._cds:
            self._cds[doc] = ColumnDataSource(
                data=dict(message=self._messages.copy()))
            self._cb[doc] = None
            self._idx[doc] = len(self._messages) - 1
            self._cds[doc].selected.indices = [self._idx[doc]]
        return self._cds[doc]

    @gen.coroutine
    def _stream_to_cds(self, doc):
        messages = self._messages[self._idx[doc] + 1:]
        if not len(messages):
            return
        self._idx[doc] = len(self._messages) - 1
        self._cds[doc].stream({'message': messages})
        self._cds[doc].selected.indices = [self._idx[doc]]


class CDSFilter(logging.Filter):

    def __init__(self, logger):
        super(CDSFilter, self).__init__()
        self.logger = logger

    def filter(self, record):
        name = record.name
        if name in self.logger or len(self.logger) == 0:
            return True
        return False


def init_log_panel(names, level=logging.NOTSET):
    logging.basicConfig(level=level)
    global handler
    if handler is None:
        handler = CDSHandler(level=level)
        handler.addFilter(CDSFilter(names))
        logging.getLogger().addHandler(handler)


def is_log_panel_activated():
    global handler
    return handler is not None


def get_log_panel(app, figurepage, client):
    global handler
    if handler is None:
        init_log_panel([])
    if client is not None:
        doc = client.doc
    else:
        doc = curdoc()
    message = TableColumn(field="message", title="Message", sortable=False)
    table = DataTable(source=handler.get_cds(doc),
                      columns=[message],
                      height=250,
                      scroll_to_selection=True,
                      sortable=False,
                      reorderable=False,
                      fit_columns=True)
    return Panel(
        child=column(children=[table], sizing_mode="scale_width"),
        title='Log')
