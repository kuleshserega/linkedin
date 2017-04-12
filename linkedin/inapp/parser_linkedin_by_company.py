# -*- coding: utf-8 -*-
import re
from lxml import html
import logging

from selenium.webdriver.common.by import By
from django.conf import settings
from django.utils.http import urlquote

from parser_linkedin_base import BaseLinkedinParser

logger = logging.getLogger('linkedin_parser')


class LinkedinParserByCompany(BaseLinkedinParser):
    SEARCH_COMPANY_URL = 'search/results/companies/' \
        '?keywords=%s&origin=GLOBAL_SEARCH_HEADER'
    COMPANY_EMPLOYEES_URL = 'search/results/people/?facetCurrentCompany=%s'

    def __init__(self, *args, **kwargs):
        super(LinkedinParserByCompany, self).__init__(*args, **kwargs)
        self.search_company_url = self.BASE_URL % self.SEARCH_COMPANY_URL
        self.base_employees_url = self.BASE_URL % self.COMPANY_EMPLOYEES_URL

    def set_employees_list_url(self):
        self._set_linkedin_search_company_id()
        self.employees_list_url = self._compose_employees_list_url()

    def _set_linkedin_search_company_id(self):
        """Set search term value as linkedin search object company_id
        if term has only numbers,
        otherwise found company_id on company search page
        """
        company_id = None
        if re.match(r'\d+$', self.search_term.encode('utf-8')):
            company_id = self.search_term
        else:
            company_id = self._get_search_company_id()
            repeat_request_count = 0
            while (not company_id and repeat_request_count <
                   settings.MAX_REPEAT_LINKEDIN_REQUEST):
                company_id = self._get_search_company_id()
                repeat_request_count += 1
                logger.info('Current retry to find company ID: %s'
                            % repeat_request_count)

        self.linkedin_search.companyId = company_id
        self.linkedin_search.save()

    def _get_search_company_id(self):
        """Wait for search page loading

        Returns:
            Function _check_company_id result
        """
        try:
            self.browser.get(
                self.search_company_url % urlquote(self.search_term))
        except Exception as e:
            logger.error(e)

        timeout_exception_msg = 'Timed out waiting for companies page to load'
        elem_exists = self._selenium_element_load_waiting(
            By.CLASS_NAME, 'search-result__title',
            success_msg='Company page is loaded',
            timeout_exception_msg=timeout_exception_msg)

        if not elem_exists:
            return None

        result = self._check_company_id()
        return result

    def _check_company_id(self):
        """Try to find company id on search page in selenium browser

        Returns:
            Company Id if exists, None if company id not found
        """
        try:
            search_page_html = html.fromstring(self.browser.page_source)
        except Exception as e:
            logger.error(e)

        xp = '(//a[contains(@class, "search-result__result-link")]/@href)[1]'
        try:
            company_link_html = search_page_html.xpath(xp)[0]
        except IndexError:
            logger.info('Search page has no company link')
            return None
        except Exception as e:
            logger.error(e)
            return None

        cid = re.search('\d+', company_link_html)
        if cid:
            cid = cid.group(0)
            logger.info('Company ID: %s' % cid)
            return cid

        return None

    def _compose_employees_list_url(self):
        url = self.base_employees_url % self.linkedin_search.companyId
        return '&'.join((url, 'page=%d'))
