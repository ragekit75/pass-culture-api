import json
import logging


class Logger(logging.Logger):
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None, sinfo=None):
        """Make a record (as the parent class does), but store ``extra``
        arguments in an ``extra`` attribute, not as direct attributes of the
        object itself.

        Otherwise, JsonFormatter cannot distinguish ``extra`` arguments from
        other record attributes (most of which we don't use).

        Note that we cannot customize the record factory because it
        does not handle the ``extra`` arguments.
        """
        record = logging._logRecordFactory(name, level, fn, lno, msg, args, exc_info, func, sinfo)
        record.extra = extra or {}
        return record


class JsonFormatter(logging.Formatter):
    def format(self, record):
        json_record = {
            # FIXME
            # "logging.googleapis.com/trace": correlation_id,
            "module": record.name,
            "severity": record.levelname,
            "message": record.msg % record.args,
            "extra": record.extra,
        }
        try:
            return json.dumps(json_record)
        except TypeError:
            # It's possible that the `extra` arguments were not
            # serializable. Let's try by dumping something slightly
            try:
                json_record["extra"] = {"unserializable": str(record.extra)}
                serialized = json.dumps(json_record)
            except TypeError:
                # I don't think we could end up here. Let's be defensive, though.
                _logger.exception("Could not serialize log in JSON", extra={"log": str(json_record)})
                return ""
            else:
                _logger.exception(
                    "Could not serialize extra log arguments in JSON",
                    extra={"record": json_record, "extra": str(record.extra)},
                )
                return serialized


def install_formatter():
    logging.setLoggerClass(Logger)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.root.addHandler(handler)

    global _logger  # pylint: disable=global-statement
    _logger = logging.getLogger(__name__)


_logger = None


# FIXME (remove this)
# Usage:
# install_formatter()
# logger = logging.getLogger(__name__)
# logger.warning("Hey %s", "ho", extra={"foo": "bar"})
# logger.warning("Hey!", extra={"foo": "bar"})
# logger.warning("Hey!", extra={"oups": object()})
