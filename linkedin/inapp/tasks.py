from celery import task

from parser_linkedin_by_company import LinkedinParserByCompany
from parser_linkedin_by_geo import LinkedinParserByGeo

BY_COMPANY_SEARCH_TYPE = 1
BY_GEO_FOR_SUPERVISORS_SEARCH_TYPE = 2


@task
def create_linkedin_search(search_term, search_type, search_geo):
    if int(search_type) == BY_COMPANY_SEARCH_TYPE:
        parser = LinkedinParserByCompany(search_term, search_type)
    elif int(search_type) == BY_GEO_FOR_SUPERVISORS_SEARCH_TYPE:
        parser = LinkedinParserByGeo(search_term, search_type, search_geo, 65)

    parser.parse()
