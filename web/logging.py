import logging, re


class RedactWebpay(logging.Filter):
    def filter(self, record):
        text = record.getMessage()
        if "/payments/return/" in text:
            record.msg = re.sub(r'(/payments/return/)\?[^\s"]*', r"\1?[REDACTED]", text)
            record.args = ()
        return True
