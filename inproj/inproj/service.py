import sys
import os
import datetime
import logging

from wsgiservice import Resource, mount, get_app
from twisted.internet import reactor, defer
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource
from twisted.python import log
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings

from settings import LOG_DIR

logging.basicConfig()
dtstr = datetime.datetime.now().strftime('%Y%m%d')
log_file = 'linkedin_service_%s.log' % dtstr
log_file_path = os.path.join(LOG_DIR, log_file)
log.startLogging(open(log_file_path, 'a'))

runner = CrawlerRunner(get_project_settings())


@mount('/linkedin_search')
class LinkedinSearch(Resource):
    """
    - GET(Launch new linkedin search)
    """
    NOT_FOUND = (KeyError,)

    def GET(self):
        crawl()
        return {'status': 'ok'}


@defer.inlineCallbacks
def crawl():
    yield runner.crawl('linkedin')


app = get_app({
    'LinkedinSearch': LinkedinSearch,
})


if __name__ == "__main__":
    if len(sys.argv) > 1:
        port = int(sys.argv[1])

        resource = WSGIResource(reactor, reactor.getThreadPool(), app)
        factory = Site(resource)
        reactor.listenTCP(port, factory)

        reactor.run()
