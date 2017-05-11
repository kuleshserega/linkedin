import logging

from celery import task

from parser_linkedin_by_company import LinkedinParserByCompany
from parser_linkedin_by_geo import LinkedinParserByGeo
from models import LinkedinSearch

BY_COMPANY_SEARCH_TYPE = 1
BY_GEO_FOR_SUPERVISORS_SEARCH_TYPE = 2

logger = logging.getLogger('linkedin_parser')


@task
def create_linkedin_search(search_term, search_type, search_geo):
    if int(search_type) == BY_COMPANY_SEARCH_TYPE:
        parser = LinkedinParserByCompany()
        parser.create_new_linkedin_search(search_term, search_type)
    elif int(search_type) == BY_GEO_FOR_SUPERVISORS_SEARCH_TYPE:
        parser = LinkedinParserByGeo()
        parser.create_new_linkedin_search(search_term, search_type, search_geo)

    parser.parse()


@task
def update_linkedin_search(search_id):
    try:
        linkedin_search = LinkedinSearch.objects.get(pk=search_id)
        if linkedin_search.search_type == BY_COMPANY_SEARCH_TYPE:
            parser = LinkedinParserByCompany()
        elif linkedin_search.search_type == BY_GEO_FOR_SUPERVISORS_SEARCH_TYPE:
            parser = LinkedinParserByGeo()

        parser.update_existing_linkedin_search(linkedin_search.id)
        parser.parse()
    except LinkedinSearch.DoesNotExist as e:
        logging.error(e)
