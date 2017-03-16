# -*- coding: utf-8 -*-
import re
import logging
from lxml import html

import scrapy
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from inproj.items import LinkedinItem
from inproj.settings import LOGIN_LINKEDIN, PASSWORD_LINKEDIN, \
    LINKEDIN_PAGE_TIMEOUT_LAODING

logger = logging.getLogger(__name__)


class LinkedinSpider(scrapy.Spider):
    name = "linkedin"
    allowed_domains = ["linkedin.com"]
    start_urls = ['https://www.linkedin.com/uas/login?goback=&trk=hb_signin']

    BUTTON_XPATH = '//input[@type="submit"]'

    LINKEDIN_URL = 'https://www.linkedin.com/'
    BASE_URL = 'https://www.linkedin.com/%s'
    SEARCH_COMPANY_URL = 'search/results/companies/' \
        '?keywords=%s&origin=GLOBAL_SEARCH_HEADER'
    COMPANY_EMPLOYEES_URL = 'search/results/people/' \
        '?facetCurrentCompany=%s&page=%d'

    def __init__(self, search_term='adidas', *args, **kwargs):
        super(LinkedinSpider, self).__init__(*args, **kwargs)
        self.search_term = search_term
        self.serch_company_url = self.BASE_URL % self.SEARCH_COMPANY_URL
        self.employees_list_url = self.BASE_URL % self.COMPANY_EMPLOYEES_URL

        self.browser = webdriver.PhantomJS()
        self.browser.set_window_size(1024, 768)

    def parse(self, response):
        # use selenium to authenticate and load linkedin page
        self.browser.get(response.url)
        self._make_login()

        self.browser.get(self.serch_company_url % self.search_term)
        company_id = self._get_company_id()
        print('company_id', company_id)

        yield scrapy.Request(
            self.LINKEDIN_URL,
            self._get_next_list_of_employees,
            meta={'company_id': company_id, 'page': 1})

        # fl = '/home/user/public_html/INPROJ/inproj/log/file.html'
        # with open(fl, 'w') as f:
        #     f.write(self.browser.page_source.encode("utf-8"))

    def _make_login(self):
        email = self.browser.find_element_by_id("session_key-login")
        password = self.browser.find_element_by_id("session_password-login")

        email.send_keys(LOGIN_LINKEDIN)
        password.send_keys(PASSWORD_LINKEDIN)

        button_login = self.browser.find_element_by_xpath(self.BUTTON_XPATH)
        button_login.click()

        try:
            element_present = EC.presence_of_element_located(
                (By.ID, 'nav-settings__dropdown-trigger'))
            WebDriverWait(self.browser, LINKEDIN_PAGE_TIMEOUT_LAODING).until(
                element_present)
            print('User authentificated')
        except TimeoutException:
            print('Timed out waiting for page to load')

    def _get_company_id(self):
        try:
            element_present = EC.presence_of_element_located(
                (By.CLASS_NAME, 'search-result__title'))
            WebDriverWait(self.browser, LINKEDIN_PAGE_TIMEOUT_LAODING).until(
                element_present)
        except TimeoutException:
            print('Timed out waiting for companies page to load')

        search_page_html = html.fromstring(self.browser.page_source)
        xp = '(//a[contains(@class, "search-result__result-link")]/@href)[1]'
        try:
            company_link_html = search_page_html.xpath(xp)[0]
        except IndexError:
            print('Search page has no company link')

        cid = re.search('\d+', company_link_html)
        return cid.group(0)

    def _get_next_list_of_employees(self, response):
        self._wait_for_page_is_loaded(response.meta)

        page_html = html.fromstring(self.browser.page_source)
        xp = '//li[contains(@class, "search-result__occluded-item")]'
        employees_list = page_html.xpath(xp)

        for employee in employees_list:
            item = LinkedinItem()
            try:
                item['full_name'] = employee.xpath(
                    './/span[contains(@class, "actor-name")]/text()')[0]
                item['title'] = employee.xpath(
                    './/p[contains(@class, "subline-level-1")]/text()')[0]
            except Exception:
                pass

            print item
            yield item

        if employees_list:
            yield scrapy.Request(
                self.LINKEDIN_URL,
                self._get_next_list_of_employees,
                meta={
                    'company_id': response.meta["company_id"],
                    'page': response.meta["page"] + 1})

    def _wait_for_page_is_loaded(self, meta):
        self.browser.get(
            self.employees_list_url % (meta["company_id"], meta["page"]))
        try:
            element_present = EC.presence_of_element_located(
                (By.CLASS_NAME, 'msg-overlay-bubble-header__title'))
            WebDriverWait(self.browser, LINKEDIN_PAGE_TIMEOUT_LAODING).until(
                element_present)
        except TimeoutException:
            print('Timed out waiting for company employees page to load')

        self.browser.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")

        last_el_entry = '//li[contains' \
            '(@class, "search-result__occluded-item")]' \
            '[last()]/div[contains(@class, "search-result")]'

        try:
            element_present = EC.presence_of_element_located(
                (By.XPATH, last_el_entry))
            WebDriverWait(self.browser, LINKEDIN_PAGE_TIMEOUT_LAODING).until(
                element_present)
        except TimeoutException:
            print('Timed out waiting for all employees to load')
