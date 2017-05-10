# -*- coding: utf-8 -*-
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

from models import LinkedinSearch, LinkedinSearchResult, LinkedinUser, \
    STATE_IN_PROCESS, STATE_FINISHED, STATE_AUTHENTICATED, \
    STATE_ASKS_CODE, STATE_CODE_NOT_VALID, STATE_LINKEDIN_USER_EMPTY, \
    STATE_ERROR, STATE_ASKS_PREMIUM, STATE_NOT_LOGGED_IN, SEARCH_BY_COMPANY, \
    STATE_CONNECTION_REFUSED

logger = logging.getLogger('linkedin_parser')

PAGE_HAS_NO_RESULTS = 1
PAGE_IS_LOADED = 2
PAGE_IS_NOT_LOADED = 3
PAGE_URL_NOT_COMPOSED = 4


class BaseLinkedinParser(object):
    login_url = 'https://www.linkedin.com/uas/login?goback=&trk=hb_signin'
    linkedin_search = None
    employees_list_url = None
    user = None

    LOGIN_BUTTON_XPATH = '//input[@type="submit"]'
    VERIFICATION_BUTTON_XPATH = '//input[@type="submit"]'

    LINKEDIN_URL = 'https://www.linkedin.com/'
    BASE_URL = 'https://www.linkedin.com/%s'

    def __init__(self, search_term='adidas',
                 search_type=SEARCH_BY_COMPANY, *args, **kwargs):
        super(BaseLinkedinParser, self).__init__(*args, **kwargs)
        self.search_term = search_term
        self.search_type = search_type

        self.user = self._get_linkedin_user()

        self.browser = webdriver.PhantomJS()
        self.browser.set_window_size(1024, 768)

    def set_employees_list_url(self):
        """Need to set employees_list_url that will be used
        with further collection of employees
        """
        raise NotImplementedError('set_employees_list_url should be override')

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

        self._create_search_entry()
        login_status = self._make_login()
        self._update_status(login_status)

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
        self.save_page_to_log_if_debug(file_name)

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

    def _create_search_entry(self):
        """Create new entry search with transferred search_term and search_type
        """
        self.linkedin_search = LinkedinSearch(
            search_term=self.search_term, search_type=self.search_type)
        self.linkedin_search.save()

    def _update_status(self, login_status):
        self.linkedin_search.status = login_status
        self.linkedin_search.save()

    def _make_search(self):
        """Search by company name or company ID
        """
        self.set_employees_list_url()
        self.linkedin_search.status = STATE_IN_PROCESS
        if not self.employees_list_url:
            self.linkedin_search.status = STATE_ERROR
            self.linkedin_search.save()
            return False

        self.linkedin_search.save()

        self._get_next_list_of_employees(1)

    def _get_next_list_of_employees(self, page_numb):
        """Recursive function that call oneself if new items exists on page
        Stop if linkedin asks premium account or no items returns
        """
        state_after_load = self._load_employees_page(page_numb)

        file_name = '%s_%s.html' % (self.search_term, str(time.time()))
        self.save_page_to_log_if_debug(file_name)

        if state_after_load == PAGE_IS_NOT_LOADED:
            self.linkedin_search.status = STATE_CONNECTION_REFUSED
            self.linkedin_search.save()
            return None

        try:
            page_html = html.fromstring(self.browser.page_source)
            xp = '//li[contains(@class, "search-result__occluded-item")]'
            employees_list = page_html.xpath(xp)
        except Exception as e:
            logger.error(e)
            self.linkedin_search.status = STATE_FINISHED
            self.linkedin_search.save()
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
        # Try to load employees page
        if not self.employees_list_url:
            return PAGE_URL_NOT_COMPOSED
        else:
            self._load_results_page_with_number(page_numb)

        first_part_loaded = self._wait_first_part_is_loaded(page_numb)
        second_part_loaded = self._wait_second_part_is_loaded(page_numb)
        if first_part_loaded and second_part_loaded:
            return PAGE_IS_LOADED
        else:
            has_at_least_one_employee = self._page_has_at_least_one_employee(
                page_numb)
            if has_at_least_one_employee:
                return PAGE_IS_LOADED

        has_no_results_msg = self._page_has_no_results_msg()
        if has_no_results_msg:
            return PAGE_HAS_NO_RESULTS

        return PAGE_IS_NOT_LOADED

        # if has_no_results_msg:
        #     return None

        # if not employees_loaded:
        #     return STATE_CONNECTION_REFUSED

    def _load_results_page_with_number(self, page_numb):
        try:
            employees_url_with_page = '&'.join([
                self.employees_list_url, 'page=%d' % page_numb])
            self.browser.get(employees_url_with_page)
        except Exception as e:
            logger.error(e)

    def _wait_first_part_is_loaded(self, page):
        """Waiting for first part employees page loaded in selenium browser

        Returns:
            True if first part of page has been loaded, False if not
        """
        timeout_exception_msg = 'Timed out waiting for ' \
            'employees page number %d to load' % page
        last_el_entry = '//li[contains(@class, ' \
            '"search-result__occluded-item")][5]'

        elem_exists = False
        repeat_request_count = 0
        while (not elem_exists and repeat_request_count <
               settings.MAX_REPEAT_LINKEDIN_REQUEST):
            repeat_request_count += 1
            success_msg = 'First part of employees %d page ' \
                'is loaded from %d retry' % (page, repeat_request_count)
            elem_exists = self._selenium_element_load_waiting(
                By.XPATH, last_el_entry,
                success_msg=success_msg,
                timeout_exception_msg=timeout_exception_msg)

        if not elem_exists:
            return False
        return True

    def _wait_second_part_is_loaded(self, page):
        """Waiting for second part of employees page loaded

        Returns:
            True part has been loaded, False otherwise
        """
        self._scroll_employees_page()

        last_el_entry = '//li[contains(@class, ' \
            '"search-result__occluded-item")][10]/' \
            'div/div[contains(@class, "search-result__wrapper")]'
        timeout_excp_msg = 'Timed out waiting for all employees to load'

        elem_exists = False
        repeat_request_count = 0
        while (not elem_exists and repeat_request_count <
               settings.MAX_REPEAT_LINKEDIN_REQUEST):
            repeat_request_count += 1
            success_msg = 'Employees page number %d after scroll ' \
                'is loaded from %d retry' % (page, repeat_request_count)
            elem_exists = self._selenium_element_load_waiting(
                By.XPATH, last_el_entry, success_msg=success_msg,
                timeout_exception_msg=timeout_excp_msg)

        if not elem_exists:
            return False
        return True

    def _scroll_employees_page(self):
        """After scrolling page in browser
        new employees are becoming available
        """
        try:
            self.browser.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);")
        except Exception as e:
            logger.error(e)

    def _page_has_at_least_one_employee(self, page):
        first_el_entry = '//li[contains(@class, ' \
            '"search-result__occluded-item")][1]'

        s_msg = 'Page number %d has at least one employee' % page
        timeout_excp_msg = 'Timed out waiting for first page employee to load'
        elem_exists = self._selenium_element_load_waiting(
            By.XPATH, first_el_entry,
            success_msg=s_msg, timeout_exception_msg=timeout_excp_msg)

        if not elem_exists:
            return False
        return True

    def _page_has_no_results_msg(self):
        """
        Returns:
            True if no results linkedin message found, False otherwise
        """
        try:
            self.browser.find_element_by_xpath(
                '//h1[contains(@class, "search-no-results__message")]')
            logger.info('On current page "has no results" block exists')
        except NoSuchElementException:
            return False
        except Exception as e:
            logger.error(e)
            return False

        return True

    def _get_items(self, employees_list, npage, premium_exists=False):
        """Get all items(linkedin users) from loaded employees page

        Returns:
            Items list, empty list if has errors in parse data with xpath
        """
        items = []
        for i, employee in enumerate(employees_list):
            if premium_exists and i == 0:
                continue

            full_name = self._get_full_name(employee)
            if not full_name:
                continue

            items.append({
                'full_name': full_name,
                'title': self._get_title(employee),
                'location': self._get_location(employee),
                'current_company': self._get_current_company(employee)})

        logger.info('Add %d items from page number %d' % (len(items), npage))
        return items

    def _get_full_name(self, employee):
        try:
            full_name = employee.xpath(
                './/span[contains(@class, "actor-name")]/text()')[0]
        except Exception:
            full_name = None
            logger.error('Full name is not found in entry')

        return full_name

    def _get_title(self, employee):
        try:
            title = employee.xpath(
                './/p[contains(@class, "subline-level-1")]/text()')[0]
        except Exception:
            title = None

        return title

    def _get_location(self, employee):
        try:
            location = employee.xpath(
                './/p[contains(@class, "subline-level-2")]/text()')[0]
        except Exception:
            location = None

        return location

    def _get_current_company(self, employee):
        company_xpath = './/p[contains(@class, ' \
            '"search-result__snippets")]//text()'
        try:
            current_company = employee.xpath(company_xpath)
            current_company = ' '.join(
                current_company).replace('Current:', '')
        except Exception:
            current_company = ''

        return current_company.strip()

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
                location=item['location'].strip(),
                current_company=item['current_company'].strip()))
        LinkedinSearchResult.objects.bulk_create(empls)

    def save_page_to_log_if_debug(self, file_name, debug=False):
        # Write html pages to project logs dir if DEBUG setting is True
        if settings.DEBUG or debug:
            file_path = '%s/%s' % (
                settings.LOGS_DIR, file_name.replace(' ', '_'))
            logger.info('Path to employees list html file: %s' % file_path)
            try:
                page = self.browser.page_source.encode('utf-8')
            except Exception as e:
                logger.error(e)
                return None

            with open(file_path, 'w') as f:
                f.write(page)
