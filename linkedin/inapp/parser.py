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
    STATE_ASKS_CODE, STATE_CODE_NOT_VALID, STATE_IN_PROCESS, \
    STATE_LINKEDIN_USER_EMPTY


class LinkedinParser(object):
    login_url = 'https://www.linkedin.com/uas/login?goback=&trk=hb_signin'

    user = None

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
        self.search_company_url = self.BASE_URL % self.SEARCH_COMPANY_URL
        self.employees_list_url = self.BASE_URL % self.COMPANY_EMPLOYEES_URL

        self.user = self._get_linkedin_user()

        self.browser = webdriver.PhantomJS()
        self.browser.set_window_size(1024, 768)

    def _get_linkedin_user(self):
        filters = {}
        if hasattr(self, 'user') and self.user:
            filters['id'] = self.user.id
            filters['password'] = self.user.password
            filters['email'] = self.user.email

        qs = LinkedinUser.objects.filter(**filters)
        if qs:
            return qs[0]
        return None

    def _selenium_element_load_waiting(
            self, by_selector_type, selector,
            success_msg='', timeout_exception_msg=''):
        try:
            element_present = EC.presence_of_element_located(
                (by_selector_type, selector))
            WebDriverWait(
                self.browser, settings.LINKEDIN_PAGE_TIMEOUT_LAODING).until(
                    element_present)
            print(success_msg)
        except TimeoutException:
            print(timeout_exception_msg)
            return False
        except Exception as e:
            print('Error:', e)
            return False

        return True

    def parse(self):
        # use selenium to authenticate and load linkedin page
        self.browser.get(self.login_url)
        self.linkedin_search = LinkedinSearch(search_company=self.search_term)

        login_status = self._make_login()
        self.linkedin_search.status = login_status
        self.linkedin_search.save()

        if login_status == STATE_AUTHENTICATED:
            self._make_search()

        self.browser.quit()

    def _make_login(self):
        email = self.browser.find_element_by_id("session_key-login")
        password = self.browser.find_element_by_id("session_password-login")

        if not self.user:
            return STATE_LINKEDIN_USER_EMPTY

        email.send_keys(self.user.email)
        password.send_keys(self.user.password)

        button_login = self.browser.find_element_by_xpath(
            self.LOGIN_BUTTON_XPATH)
        button_login.click()

        is_authenticated = self._is_user_auth()
        if not is_authenticated:
            search_status = self._get_search_status()
            if search_status:
                return search_status

        return STATE_AUTHENTICATED

    def _is_user_auth(self):
        elem_exists = self._selenium_element_load_waiting(
            By.ID, 'nav-settings__dropdown-trigger',
            success_msg='User authenticated',
            timeout_exception_msg='Timed out waiting for user login')

        if settings.DEBUG:
            file_name = 'auth_%s_%s.html' % (
                self.search_term, str(time.time()))
            self._save_page_to_log(file_name)

        if not elem_exists:
            return False
        return True

    def _get_search_status(self):
        asks_verification = self._asks_code_verification()
        if asks_verification:
            self.linkedin_search.status = STATE_ASKS_CODE
            self.linkedin_search.save()

            verified = self._substitute_verification_code()
            if not verified:
                return STATE_CODE_NOT_VALID
        else:
            return STATE_NOT_LOGGED_IN

        return None

    def _asks_code_verification(self):
        timeout_exception_msg = 'Timed out waiting for' \
            'linkedin verification page'
        elem_exists = self._selenium_element_load_waiting(
            By.ID, 'verification-code',
            success_msg='Linkedin verification code asked',
            timeout_exception_msg=timeout_exception_msg)

        if not elem_exists:
            return False
        return True

    def _substitute_verification_code(self):
        print('Begin waiting for user set verification code')
        time.sleep(180)
        print('End waiting')

        self.user = self._get_linkedin_user()

        verification_code = self.browser.find_element_by_id(
            "verification-code")
        verification_code.send_keys(self.user.verification_code)

        code_verification_button = self.browser.find_element_by_xpath(
            self.VERIFICATION_BUTTON_XPATH)
        code_verification_button.click()

        return self._is_user_auth()

    def _make_search(self):
        # set company id depending what user entered in the search
        # if only numbers then set value as company id
        # if not then set search_term as company name
        if re.match(r'\d+$', self.search_term.encode('utf-8')):
            company_id = self.search_term
        else:
            self.browser.get(
                self.search_company_url % urlquote(self.search_term))
            company_id = self._get_company_id()
            repeat_request_count = 0
            while (not company_id and repeat_request_count <
                   settings.MAX_REPEAT_LINKEDIN_REQUEST):
                company_id = self._get_company_id()
                repeat_request_count += 1
                print('Current retry to find company ID: %s'
                      % repeat_request_count)

        self.linkedin_search.companyId = company_id
        self.linkedin_search.search_company = self.search_term
        self.linkedin_search.status = STATE_IN_PROCESS

        if not company_id:
            self.linkedin_search.status = STATE_ERROR
        self.linkedin_search.save()

        repeat_request_page_count = 0
        is_loaded = self._get_next_list_of_employees(company_id, 1)
        while (not is_loaded and repeat_request_page_count <
               settings.MAX_REPEAT_LINKEDIN_REQUEST):
            is_loaded = self._get_next_list_of_employees(company_id, 1)
            repeat_request_page_count += 1
            print('Current retry to load 1 page: %s'
                  % repeat_request_page_count)

        if not is_loaded:
            self.linkedin_search.status = STATE_ERROR
            self.linkedin_search.save()
            return False

    def _get_company_id(self):
        timeout_exception_msg = 'Timed out waiting for companies page to load'
        elem_exists = self._selenium_element_load_waiting(
            By.CLASS_NAME, 'search-result__title',
            success_msg='Company page is loaded',
            timeout_exception_msg=timeout_exception_msg)

        if not elem_exists:
            return None

        search_page_html = html.fromstring(self.browser.page_source)

        xp = '(//a[contains(@class, "search-result__result-link")]/@href)[1]'
        try:
            company_link_html = search_page_html.xpath(xp)[0]
        except IndexError:
            print('Search page has no company link')
            return None

        cid = re.search('\d+', company_link_html)
        if cid:
            cid = cid.group(0)
            print('Company ID: %s' % cid)
            return cid

        return None

    def _get_next_list_of_employees(self, company_id, page_numb):
        employees_loaded = self._wait_for_page_is_loaded(company_id, page_numb)
        if not employees_loaded:
            return False

        if settings.DEBUG:
            file_name = '%s_%s.html' % (self.search_term, str(time.time()))
            self._save_page_to_log(file_name)

        page_html = html.fromstring(self.browser.page_source)

        xp = '//li[contains(@class, "search-result__occluded-item")]'
        employees_list = page_html.xpath(xp)

        items = self._get_items(employees_list, page_numb)
        if not isinstance(items, list):
            return False

        self._save_items_to_db(items)

        if employees_list:
            repeat_request_count = 0
            is_loaded = self._get_next_list_of_employees(
                company_id, page_numb+1)
            if is_loaded:
                return True

            while (not is_loaded and repeat_request_count <
                   settings.MAX_REPEAT_LINKEDIN_REQUEST):
                is_loaded = self._get_next_list_of_employees(
                    company_id, page_numb+1)
                repeat_request_count += 1
                print('Current retry to load %d page: %s'
                      % (page_numb+1, repeat_request_count))

            if not is_loaded:
                self.linkedin_search.status = STATE_ERROR
                self.linkedin_search.save()
                return False
            return True
        else:
            self.linkedin_search.status = STATE_FINISHED
            self.linkedin_search.save()

    def _get_items(self, employees_list, npage):
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
                return None

        print('Add %d items from page number %d' % (len(items), npage))
        return items

    def _save_items_to_db(self, items):
        empls = []
        for item in items:
            empls.append(LinkedinSearchResult(
                search=self.linkedin_search,
                full_name=item['full_name'],
                title=item['title']))
        LinkedinSearchResult.objects.bulk_create(empls)

    def _wait_for_page_is_loaded(self, company_id, page):
        self.browser.get(self.employees_list_url % (company_id, page))
        success_msg = 'First part of employees %d page is loaded' % page
        timeout_exception_msg = 'Timed out waiting for company' \
            'employees page to load'
        elem_exists = self._selenium_element_load_waiting(
            By.CLASS_NAME, 'msg-overlay-bubble-header__title',
            success_msg=success_msg,
            timeout_exception_msg=timeout_exception_msg)

        if not elem_exists:
            return False

        self.browser.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);")

        last_el_entry = '//li[contains' \
            '(@class, "search-result__occluded-item")]' \
            '[last()]/div[contains(@class, "search-result")]'

        success_msg_1 = 'The whole employees %d page is loaded' % page
        timeout_exception_msg_1 = 'Timed out waiting for all employees to load'
        elem_exists = self._selenium_element_load_waiting(
            By.XPATH, last_el_entry,
            success_msg=success_msg_1,
            timeout_exception_msg=timeout_exception_msg_1)

        if not elem_exists:
            return False

        return True

    def _save_page_to_log(self, file_name):
        file_path = '%s/%s' % (settings.LOGS_DIR, file_name)
        page = self.browser.page_source.encode('utf-8')
        with open(file_path, 'w') as f:
            f.write(page)
