from celery import task

from parser import LinkedinParser


@task
def create_linkedin_search(search_term):
    parser = LinkedinParser(search_term)
    parser.parse()
