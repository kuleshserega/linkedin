from celery import task

from parser import LinkedinParser


@task
def create_linkedin_search(search_term, search_type):
    parser = LinkedinParser(search_term, search_type)
    parser.parse()
