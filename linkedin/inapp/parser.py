# -*- coding: utf-8 -*-
import re
from lxml import html
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from django.conf import settings
from django.utils.http import urlquote

from models import LinkedinSearch, LinkedinSearchResult, LinkedinUser, \
    STATE_FINISHED, STATE_ERROR, STATE_NOT_LOGGED_IN, STATE_AUTHENTICATED, \
    STATE_NOT_VALID_CODE


class LinkedinParser(object):
    login_url = 'https://www.linkedin.com/uas/login?goback=&trk=hb_signin'

    LOGIN_BUTTON_XPATH = '//input[@type="submit"]'

    VERIFICATION_BUTTON_XPATH = '//input[@type="submit"]'

    LINKEDIN_URL = 'https://www.linkedin.com/'
    BASE_URL = 'https://www.linkedin.com/%s'
    SEARCH_COMPANY_URL = 'search/results/companies/' \
        '?keywords=%s&origin=GLOBAL_SEARCH_HEADER'
    COMPANY_EMPLOYEES_URL = 'search/results/people/' \
        '?facetCurrentCompany=%s&page=%d'

    def __init__(self, search_term='adidas', *args, **kwargs):
        super(LinkedinParser, self).__init__(*args, **kwargs)
        self.search_term = search_term
        self.serch_company_url = self.BASE_URL % self.SEARCH_COMPANY_URL
        self.employees_list_url = self.BASE_URL % self.COMPANY_EMPLOYEES_URL

        self.user = self._get_linkedin_user()

        self.browser = webdriver.PhantomJS()
        self.browser.set_window_size(1024, 768)

    def _get_linkedin_user(self):
        qs = LinkedinUser.objects.all()
        if qs:
            return qs[0]
        return None

    def parse(self):
        # use selenium to authenticate and load linkedin page
        self.browser.get(self.login_url)
        login_status = self._make_login()
        if login_status == STATE_AUTHENTICATED:
            self._make_search()
        else:
            LinkedinSearch(
                search_company=self.search_term, status=login_status).save()

        self.browser.quit()

    def _make_login(self):
        email = self.browser.find_element_by_id("session_key-login")
        password = self.browser.find_element_by_id("session_password-login")

        email.send_keys(self.user.email)
        password.send_keys(self.user.password)

        button_login = self.browser.find_element_by_xpath(
            self.LOGIN_BUTTON_XPATH)
        button_login.click()

        is_authenticated = self._is_user_auth()
        if not is_authenticated:
            asks_verification = self._asks_code_verification()
            if asks_verification:
                verified = self._substitute_verification_code()
                if not verified:
                    return STATE_NOT_VALID_CODE
            else:
                return STATE_NOT_LOGGED_IN

        return STATE_AUTHENTICATED

    def _make_search(self):
        # set company id depending what user entered in the search
        # if only numbers then set value as company id
        # if not then set search_term as company name
        if re.match(r'\d+$', self.search_term.encode('utf-8')):
            company_id = self.search_term
        else:
            self.browser.get(
                self.serch_company_url % urlquote(self.search_term))
            company_id = self._get_company_id()

        self.linkedin_search = LinkedinSearch(
            companyId=company_id, search_company=self.search_term)

        if not company_id:
            self.linkedin_search.status = STATE_ERROR
            self.linkedin_search.save()
        else:
            self.linkedin_search.save()

        self._get_next_list_of_employees(company_id, 1)

    def _is_user_auth(self):
        try:
            element_present = EC.presence_of_element_located(
                (By.ID, 'nav-settings__dropdown-trigger'))
            WebDriverWait(
                self.browser, settings.LINKEDIN_PAGE_TIMEOUT_LAODING).until(
                    element_present)
            print('User authentificated')
            with open(str(time.time()), 'w') as f:
                f.write(self.browser.page_source.encode('utf-8'))
        except TimeoutException:
            with open(str(time.time()), 'w') as f:
                f.write(self.browser.page_source.encode('utf-8'))
            print('Timed out waiting for user login')
            return False

        return True

    def _asks_code_verification(self):
        try:
            element_present = EC.presence_of_element_located(
                (By.ID, 'verification-code'))
            WebDriverWait(
                self.browser, settings.LINKEDIN_PAGE_TIMEOUT_LAODING).until(
                    element_present)
            print('Linkedin verification code asked')
        except TimeoutException:
            print('Timed out waiting for linkedin verification page')
            return False

        return True

    def _substitute_verification_code(self):
        if self.user.verification_code:
            verification_code = self.browser.find_element_by_id("verification-code")
            verification_code.send_keys(self.user.verification_code)

            code_verification_button = self.browser.find_element_by_xpath(
                self.VERIFICATION_BUTTON_XPATH)
            code_verification_button.click()

            return self._is_user_auth()
        else:
            return False

    def _get_company_id(self):
        try:
            element_present = EC.presence_of_element_located(
                (By.CLASS_NAME, 'search-result__title'))
            WebDriverWait(
                self.browser, settings.LINKEDIN_PAGE_TIMEOUT_LAODING).until(
                    element_present)
        except TimeoutException:
            print('Timed out waiting for companies page to load')

        search_page_html = html.fromstring(self.browser.page_source)

        xp = '(//a[contains(@class, "search-result__result-link")]/@href)[1]'
        try:
            company_link_html = search_page_html.xpath(xp)[0]
        except IndexError:
            print('Search page has no company link')
            return None

        cid = re.search('\d+', company_link_html)
        return cid.group(0)

    def _get_next_list_of_employees(self, company_id, page):
        self._wait_for_page_is_loaded(company_id, page)

        page_html = html.fromstring(self.browser.page_source)

        xp = '//li[contains(@class, "search-result__occluded-item")]'
        employees_list = page_html.xpath(xp)

        items = self._get_items(employees_list)
        if not isinstance(items, list):
            return None

        empls = []
        for item in items:
            empls.append(LinkedinSearchResult(
                search=self.linkedin_search,
                full_name=item['full_name'],
                title=item['title']))
        LinkedinSearchResult.objects.bulk_create(empls)

        if employees_list:
            self._get_next_list_of_employees(company_id, page+1)
        else:
            if hasattr(self, 'linkedin_search'):
                self.linkedin_search.status = STATE_FINISHED
                self.linkedin_search.save()

    def _get_items(self, employees_list):
        items = []
        for employee in employees_list:
            try:
                try_premium_exists = employee.xpath(
                    './/div[contains(@class, "search-paywall__warning")]')
                if try_premium_exists:
                    self.linkedin_search.status = STATE_ERROR
                    self.linkedin_search.save()
                    return None

                full_name = employee.xpath(
                    './/span[contains(@class, "actor-name")]/text()')[0]
                title = employee.xpath(
                    './/p[contains(@class, "subline-level-1")]/text()')[0]
                items.append({'full_name': full_name, 'title': title})
            except Exception:
                print('Full name or title is not found')

        print('Add %d items' % len(items))
        return items

    def _wait_for_page_is_loaded(self, company_id, page):
        self.browser.get(self.employees_list_url % (company_id, page))
        try:
            element_present = EC.presence_of_element_located(
                (By.CLASS_NAME, 'msg-overlay-bubble-header__title'))
            WebDriverWait(
                self.browser, settings.LINKEDIN_PAGE_TIMEOUT_LAODING).until(
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
            WebDriverWait(
                self.browser, settings.LINKEDIN_PAGE_TIMEOUT_LAODING).until(
                    element_present)
        except TimeoutException:
            print('Timed out waiting for all employees to load')
