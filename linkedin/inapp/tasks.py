from celery import task

from parser_linkedin_by_company import LinkedinParseByCompany
from parser_linkedin_by_geo import LinkedinParseByGeo

BY_COMPANY_SEARCH_TYPE = 1
BY_GEO_FOR_SUPERVISORS_SEARCH_TYPE = 2


@task
def create_linkedin_search(search_term, search_type):
    if int(search_type) == BY_COMPANY_SEARCH_TYPE:
        parser = LinkedinParseByCompany(search_term, search_type)
    elif int(search_type) == BY_GEO_FOR_SUPERVISORS_SEARCH_TYPE:
        parser = LinkedinParseByGeo(search_term, search_type)

    parser.parse()
