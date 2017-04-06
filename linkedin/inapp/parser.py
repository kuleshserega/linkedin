# -*- coding: utf-8 -*-
import re
from lxml import html
import time
import signal
import logging

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from django.conf import settings
from django.utils.http import urlquote

from models import LinkedinSearch, LinkedinSearchResult, LinkedinUser, \
    STATE_FINISHED, STATE_ERROR, STATE_NOT_LOGGED_IN, STATE_AUTHENTICATED, \
    STATE_ASKS_CODE, STATE_CODE_NOT_VALID, STATE_IN_PROCESS, \
    STATE_LINKEDIN_USER_EMPTY, STATE_ASKS_PREMIUM

logger = logging.getLogger('linkedin_parser')


class LinkedinParser(object):
    login_url = 'https://www.linkedin.com/uas/login?goback=&trk=hb_signin'

    user = None
    company_id = None

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
        """
        Returns:
            User object from db, None if user not found
        """
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
        """Wrapper around explicity waiting for
        elememt will appear in selenium browser
        """
        try:
            element_present = EC.presence_of_element_located(
                (by_selector_type, selector))
            WebDriverWait(
                self.browser, settings.LINKEDIN_PAGE_TIMEOUT_LAODING).until(
                    element_present)
            logger.info(success_msg)
        except TimeoutException:
            logger.error(timeout_exception_msg)
            return False
        except Exception as e:
            logger.error(e)
            return False

        return True

    def parse(self):
        """Use selenium to authenticate and load linkedin page
        """
        try:
            self.browser.get(self.login_url)
        except Exception as e:
            logger.error(e)
        self.linkedin_search = LinkedinSearch(search_company=self.search_term)

        login_status = self._make_login()
        self.linkedin_search.status = login_status
        self.linkedin_search.save()

        if login_status == STATE_AUTHENTICATED:
            self._make_search()

        try:
            self.browser.service.process.send_signal(signal.SIGTERM)
            self.browser.quit()
        except OSError as e:
            logger.error(e)

    def _make_login(self):
        """Try to authenticate with selenium browser

        Returns:
            Status of authentication
        """
        try:
            email = self.browser.find_element_by_id("session_key-login")
            password = self.browser.find_element_by_id(
                "session_password-login")

            if not self.user:
                return STATE_LINKEDIN_USER_EMPTY

            email.send_keys(self.user.email)
            password.send_keys(self.user.password)

            button_login = self.browser.find_element_by_xpath(
                self.LOGIN_BUTTON_XPATH)
            button_login.click()
        except Exception as e:
            logger.error(e)

        is_authenticated = self._is_user_auth()
        if not is_authenticated:
            search_status = self._get_search_status()
            if search_status:
                return search_status

        return STATE_AUTHENTICATED

    def _is_user_auth(self):
        """Check substituted in selenium user is authenticated on linkedin

        Returns:
            True if is authenticated, False if not
        """
        elem_exists = self._selenium_element_load_waiting(
            By.ID, 'nav-settings__dropdown-trigger',
            success_msg='User authenticated',
            timeout_exception_msg='Timed out waiting for user login')

        file_name = 'auth_%s_%s.html' % (self.search_term, str(time.time()))
        self._save_page_to_log_if_debug(file_name)

        if not elem_exists:
            return False
        return True

    def _get_search_status(self):
        """Check status of the running search

        Returns:
            None if any condition is not satisfied, Status code otherwise
        """
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
        """For case when linkedin has been asked for code verification

        Returns:
            True if code verification exist on the page, False if not
        """
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
        """Try to substitute and send verification code in selenium browser

        Returns:
            Check function: _is_user_auth
        """
        logger.info('Start waiting for user set verification code')
        time.sleep(180)
        logger.info('End waiting')

        self.user = self._get_linkedin_user()
        try:
            verification_code = self.browser.find_element_by_id(
                "verification-code")
            verification_code.send_keys(self.user.verification_code)

            code_verification_button = self.browser.find_element_by_xpath(
                self.VERIFICATION_BUTTON_XPATH)
            code_verification_button.click()
        except Exception as e:
            logger.error(e)

        return self._is_user_auth()

    def _make_search(self):
        """Make search with search term
        """
        self._set_obj_company_id()
        self.linkedin_search.companyId = self.company_id
        self.linkedin_search.search_company = self.search_term
        self.linkedin_search.status = STATE_IN_PROCESS

        if not self.company_id:
            self.linkedin_search.status = STATE_ERROR
            self.linkedin_search.save()
            return None

        self.linkedin_search.save()

        self._get_next_list_of_employees(1)

    def _set_obj_company_id(self):
        """Set search term value as object company_id if term has only numbers,
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

        self.company_id = company_id

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

    def _get_next_list_of_employees(self, page_numb):
        """Recursive function that call oneself if new items exists on page
        Stop if linkedin asks premium account or no items returns
        """
        self._load_employees_page(page_numb)
        try:
            page_html = html.fromstring(self.browser.page_source)
            xp = '//li[contains(@class, "search-result__occluded-item")]'
            employees_list = page_html.xpath(xp)
        except Exception as e:
            logger.error(e)
            return None

        premium_exists = self._check_premium_exists(employees_list)
        if premium_exists and len(employees_list) == 1:
            self.linkedin_search.status = STATE_ASKS_PREMIUM
            self.linkedin_search.save()
            return None

        items = self._get_items(employees_list, page_numb, premium_exists)
        self._save_items_to_db(items)

        if employees_list:
            self._get_next_list_of_employees(page_numb+1)
        else:
            self.linkedin_search.status = STATE_FINISHED
            self.linkedin_search.save()

    def _check_premium_exists(self, employees_list):
        """Check if linkedin asks for premium

        Returns:
            True if premium block exists, False otherwise
        """
        if employees_list:
            premium_exists = employees_list[0].xpath(
                './/div[contains(@class, "search-paywall__warning")]')
            if premium_exists:
                return True

        return False

    def _load_employees_page(self, page_numb):
        # Try to load employees page MAX_REPEAT_LINKEDIN_REQUEST times
        employees_loaded = self._wait_for_page_is_loaded(page_numb)
        repeat_request_count = 0
        while (not employees_loaded and repeat_request_count <
               settings.MAX_REPEAT_LINKEDIN_REQUEST):
            no_results = self._no_page_results()
            if no_results:
                break

            employees_loaded = self._wait_for_page_is_loaded(page_numb)
            repeat_request_count += 1
            logger.info('Current retry to load page number %d: %s'
                        % (page_numb, repeat_request_count))

        file_name = '%s_%s.html' % (self.search_term, str(time.time()))
        self._save_page_to_log_if_debug(file_name)

    def _no_page_results(self):
        """
        Returns:
            True if no results linkedin message found, False otherwise
        """
        try:
            self.browser.find_element_by_xpath(
                '//h1[contains(@class, "search-no-results__message")]')
        except NoSuchElementException:
            return False
        except Exception as e:
            logger.error(e)

        return True

    def _get_items(self, employees_list, npage, premium_exists=False):
        """Get all items(linkedin users) from loaded employees page

        Returns:
            Items list, None if has errors in parse data with xpath
        """
        items = []
        for i, employee in enumerate(employees_list):
            try:
                if premium_exists and i == 0:
                    continue

                full_name = employee.xpath(
                    './/span[contains(@class, "actor-name")]/text()')[0]
                title = employee.xpath(
                    './/p[contains(@class, "subline-level-1")]/text()')[0]
                location = employee.xpath(
                    './/p[contains(@class, "subline-level-2")]/text()')[0]
                items.append({
                    'full_name': full_name,
                    'title': title,
                    'location': location})
            except Exception:
                logger.error('Full name or title is not found in entry')

        logger.info('Add %d items from page number %d' % (len(items), npage))
        return items

    def _save_items_to_db(self, items):
        # Save items (linkedin users) to db
        empls = []
        for item in items:
            last_name = None
            if 'LinkedIn' in item['full_name']:
                first_name = item['full_name']
            else:
                name = item['full_name'].rsplit(' ', 1)
                first_name = name[0] if len(name) > 0 else None
                last_name = name[1] if len(name) > 1 else None

            empls.append(LinkedinSearchResult(
                search=self.linkedin_search,
                first_name=first_name,
                last_name=last_name,
                title=item['title'],
                location=item['location']))
        LinkedinSearchResult.objects.bulk_create(empls)

    def _wait_for_page_is_loaded(self, page):
        """Waiting for employees page loaded in selenium browser

        Returns:
            True if all page has been loaded,
            False if one of the page parts was not loaded or no results found
        """
        try:
            self.browser.get(self.employees_list_url % (self.company_id, page))
        except Exception as e:
            logger.error(e)

        success_msg = 'First part of employees %d page is loaded' % page
        timeout_exception_msg = 'Timed out waiting for ' \
            'employees page number %d to load' % page
        last_el_entry = '//li[contains' \
            '(@class, "search-result__occluded-item")]' \
            '[7]/div[contains(@class, "search-result")]'
        elem_exists = self._selenium_element_load_waiting(
            By.XPATH, last_el_entry,
            success_msg=success_msg,
            timeout_exception_msg=timeout_exception_msg)

        if not elem_exists:
            return False

        is_loaded = self._wait_second_part_is_loaded(page)
        if not is_loaded:
            return False
        return True

    def _wait_second_part_is_loaded(self, page):
        """Waiting for second part of employees page loaded

        Returns:
            True part has been loaded, False otherwise
        """
        try:
            self.browser.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")
        except Exception as e:
            logger.error(e)

        last_el_entry = '//li[contains' \
            '(@class, "search-result__occluded-item")]' \
            '[last()]/div[contains(@class, "search-result")]'

        s_msg = 'Employees page number %d after scroll is loaded' % page
        timeout_excp_msg = 'Timed out waiting for all employees to load'
        elem_exists = self._selenium_element_load_waiting(
            By.XPATH, last_el_entry,
            success_msg=s_msg, timeout_exception_msg=timeout_excp_msg)

        if not elem_exists:
            return False

        return True

    def _save_page_to_log_if_debug(self, file_name):
        # Write html pages to project logs dir if DEBUG setting is True
        if settings.DEBUG:
            file_path = '%s/%s' % (settings.LOGS_DIR, file_name)
            logger.info('Path to employees list html file: %s' % file_path)
            try:
                page = self.browser.page_source.encode('utf-8')
            except Exception as e:
                logger.error(e)
                return None

            with open(file_path, 'w') as f:
                f.write(page)
