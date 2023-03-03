BOT_NAME = "scrapy_apteka"

SPIDER_MODULES = ["scrapy_apteka.spiders"]
NEWSPIDER_MODULE = "scrapy_apteka.spiders"

ROBOTSTXT_OBEY = True

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

FEEDS = {
    'output_%(time)s.json': {
        'format': 'json',
        'overwrite': True
    }
}
