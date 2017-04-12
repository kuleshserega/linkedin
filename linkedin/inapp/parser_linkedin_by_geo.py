# -*- coding: utf-8 -*-
import time
import logging

from selenium.webdriver.common.by import By

from parser_linkedin_base import BaseLinkedinParser

logger = logging.getLogger('linkedin_parser')


class LinkedinParserByGeo(BaseLinkedinParser):
    REGION_BLOCK_EXPANDED_XPATH = '//li[contains(@class,' \
        '"search-facet--geo-region") and ' \
        'contains(@class, "search-facet--is-expanded")]'
    SOCIAL_SUPERVISORS_URL = 'search/results/people/?keywords=' \
        'Social%20Marketing%20Supervisor&origin=FACETED_SEARCH'

    def __init__(self, *args, **kwargs):
        super(LinkedinParserByGeo, self).__init__(*args, **kwargs)
        self.base_supervisors_url = self.BASE_URL % self.SOCIAL_SUPERVISORS_URL

    def set_employees_list_url(self):
        result = self._set_region_on_search_page()
        if result:
            self.employees_list_url = self._compose_employees_list_url()

    def _set_region_on_search_page(self):
        """Load "social marketing supervisor" page with region
        Set url with region for LinkedIn employees search
        """
        base_supervisors_page = self._load_base_supervisors_page()
        if not base_supervisors_page:
            return None

        region_block_expanded = self._is_region_block_expanded()
        if not region_block_expanded:
            result = self._make_expanded_region_block()
            if not result:
                return None

        location_field_added = self._add_location_into_search_field()
        if not location_field_added:
            return None

        dropdown_opened = self._click_first_from_dropdown()
        if not dropdown_opened:
            return None

        return True

    def _load_base_supervisors_page(self):
        try:
            self.browser.get(self.base_supervisors_url)
        except Exception as e:
            logger.error(e)

        timeout_exception_msg = 'Timed out waiting for social ' \
            'marketing supervisors page to load'
        elem_exists = self._selenium_element_load_waiting(
            By.CLASS_NAME, 'search-facet--geo-region',
            success_msg='Social marketing supervisors page is loaded',
            timeout_exception_msg=timeout_exception_msg)

        if not elem_exists:
            return False
        return True

    def _is_region_block_expanded(self):
        region_block_expanded = None
        try:
            region_block_expanded = \
                self.browser.find_element_by_xpath(
                    self.REGION_BLOCK_EXPANDED_XPATH)
        except Exception as e:
            logger.error(e)

        return region_block_expanded

    def _make_expanded_region_block(self):
        """If not expanded region block press to expand

        Returns:
            True if element from region block exist on page, False otherwise
        """
        region_block_link = self.browser.find_element_by_xpath(
            '//li[contains(@class, "search-facet--geo-region")]/button')
        region_block_link.click()

        timeout_exception_msg = 'Timed out waiting for to expand region block'
        elem_exists = self._selenium_element_load_waiting(
            By.XPATH, self.REGION_BLOCK_EXPANDED_XPATH,
            success_msg='Region block is expanded',
            timeout_exception_msg=timeout_exception_msg)

        if not elem_exists:
            return False
        return True

    def _add_location_into_search_field(self):
        """Insert location field from search into
        corresponding region field on linkedin page
        """
        adding_region_link_xpath = '//li[contains(@class, ' \
            '"search-facet--geo-region")]/fieldset/ol/' \
            'li[contains(@class, "search-s-add-facet")]/button'
        el = self.browser.find_element_by_xpath(adding_region_link_xpath)
        el.click()

        region_field_xpath = '//li[contains(@class, ' \
            '"search-facet--geo-region")]/fieldset/ol/' \
            'li[contains(@class, "search-s-add-facet")]/' \
            'section/div/div/div/div/div/input'
        timeout_exception_msg = 'Timed out waiting for adding region field'
        elem_exists = self._selenium_element_load_waiting(
            By.XPATH, region_field_xpath,
            success_msg='Region field is added',
            timeout_exception_msg=timeout_exception_msg)

        region_field = self.browser.find_element_by_xpath(region_field_xpath)
        region_field.send_keys(self.linkedin_search.search_term)

        # explicity wait for region drop down menu is loaded
        time.sleep(10)

        if not elem_exists:
            return False
        return True

    def _click_first_from_dropdown(self):
        """Click on first element from drop down region menu
        Wait for search page with
        region param in url (facetGeoRegion) will be loaded
        """
        first_region_xpath = '//ul[contains(@class, ' \
            '"type-ahead-results")]/li[1]'
        try:
            el = self.browser.find_element_by_xpath(first_region_xpath)
            el.click()
        except Exception as e:
            logger.error(e)
            return False

        return True

    def _compose_employees_list_url(self):
        """Set employees_list_url property
        """
        # TODO: change current behavior to waiting some element on the page
        time.sleep(10)
        return self.browser.current_url
