#!/usr/bin/python3
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
import selenium.common.exceptions as selEx
#from selEx import selEx.TimeoutException, selEx.ElementNotInteractableException, selEx.StaleElementReferenceException, selEx.ElementClickInterceptedException, selEx.UnexpectedAlertPresentException
from urllib.parse import urljoin, urlsplit
import sys
import time
from datetime import datetime
import domain_utils
import random
import json

'''
Lots of inspiration from Englehardt's email tracking code:
https://github.com/citp/email_tracking/blob/79c78b2de09b79639776fb576ae1497d2f3184fc/crawler_emails/automation/Commands/custom_commands.py
'''


##### GLOBALS #####
user_info = {
    'email': 'DataExStudy@iseclab.org',
    'first_name': 'Jane',
    'last_name': 'Doe',
    'full_name': 'Jane Doe',
    'user': 'jdoe99',
    'password': 'p@55w0Rd99',
    'tel': '617 555 1234',
    'company': 'Doe & Data',
    'title': 'Dr.',
    'zip': '12345',
    'street1': '1 Main St.',
    'street2': 'Unit 7',
    'city': 'Boston',
    'state': 'Massachusetts',
    'message': 'https://iseclab.org/',
}

_KEYWORDS_EMAIL  = ['email', 'e-mail', 'subscribe', 'newsletter']
_KEYWORDS_SUBMIT = ['submit', 'sign up', 'sign-up', 'signup', 'sign me up', 'subscribe', 'register', 'join']
_KEYWORDS_SEARCH = ['search']
_KEYWORDS_SELECT = ['yes', 'ma', 'massachusetts', 'united states', 'usa', '1990']
_KEYWORDS_LINK = ['form', 'submit', 'sign-up', 'sign_up', 'signup', 'email', 'newsletter', 'feedback', 'contact', 'contact-us', 'contact_us', 'tellafriend', 'tell-a-friend', 'tell_a_friend', 'register', 'login', 'discount']

_MAX_LINKS = 5
_PAGE_LOAD_TIME = 10
_FORM_SUBMIT_SLEEP = 2

_DEBUG = True

##### END GLOBALS #####

'''
Testing color printing to highlight typing
'''
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'



def init_globals(globalsIn):
    globals().update(globalsIn)

def printDEBUG(ID, string, end="\n", level=1, error=False):
    x = ID.split("-")
    runSeed = x[0]
    procID = x[1]
    
    # Print main's output even outside of debug mode
    # TODO: I'm sure there's a better more elegant way to do this, but it's late
    # and I'm all out of brain power
    if procID == "MAIN":
        stamp = datetime.now().strftime("%m/%d/%Y-%H:%M:%S:%f")
        pstring = stamp + " [" + str(ID) + "]: " + "\t"*level + string
        print(pstring, end=end)
        with open("./%s/%s-debugFile.json" % (runSeed, ID), "a+") as debugOut:
            obj = {"Time": stamp, "ID": ID, "Action": string, "Level": level, "end": end}
            print(json.dumps(obj), file=debugOut)
        return

    if _DEBUG:
        stamp = datetime.now().strftime("%m/%d/%Y-%H:%M:%S:%f")
        pstring = stamp + " [" + str(ID) + "]: " + "\t"*level + string
        if error:
            pstring = bcolors.FAIL + pstring + bcolors.ENDC
        #print(pstring, end=end)
        with open("./%s/%s-debugFile.json" % (runSeed, ID), "a+") as debugOut:
            obj = {"Time": stamp, "ID": ID, "Action": string, "Level": level, "end": end}
            print(json.dumps(obj), file=debugOut)

def printLOG(ID, comms):
    x = ID.split("-")
    runSeed = x[0]
    procID = x[1]
    with open("./%s/runLogs/%s-RunLOG.json" % (runSeed, ID), "a+") as LogOut:
        print(comms, file=LogOut)



'''
https://stackoverflow.com/questions/18176602/how-to-get-name-of-exception-that-was-caught-in-python
'''
def get_full_class_name(obj):
    module = obj.__class__.__module__
    if module is None or module == str.__class__.__module__:
        return obj.__class__.__name__
    return module + '.' + obj.__class__.__name__

def get_blacklist(ID, inFile):
    # Implementing blacklist as a dictionary for O(1) lookup times
    blacklist = {}
    if inFile:
        printDEBUG(ID, "getting blacklist", level=0)
        with open(inFile, "r") as blIn:
            for line in blIn:
                line = line.partition('#')[0]
                line = line.rstrip()
                blacklist[line] = True
    return blacklist


def crawl_site(ID, site, driver, comms):
    printDEBUG(ID, "driver.get - crawling %s..." % site, level=0)
    try:
        driver.get(site)
        comms.add_subpage(site)
    except Exception as err:
        printDEBUG(ID, "%sERROR: %s - %s%s" % (bcolors.FAIL, get_full_class_name(err), err, bcolors.ENDC), level=0)
        comms.add_error(repr(err))
        return False
    return True

def _is_anchor_link(url, href):
    anchor_link = url + "#"
    if anchor_link == href[0:len(anchor_link)]:
        return True
    return False

def _is_internal_link(href, url, ps1=None):
    """Returns whether the given link is an internal link."""
    try:
        if ps1 is None:
            ps1 = domain_utils.get_ps_plus_1(url)
        return domain_utils.get_ps_plus_1(urljoin(url, href)) == ps1
    except TypeError:
        return False

# Make sure to keep and check a list of visited links already
def get_all_links(ID, driver):
    links = driver.find_elements_by_tag_name('a')
    highChanceLinks = {}
    lowChanceLinks = {}
    current_url = driver.current_url
    current_ps1 = domain_utils.get_ps_plus_1(current_url)
    for link in links:
        try:
            if not link.is_displayed():
                continue
            href = link.get_attribute('href')
            if href is None or not _is_internal_link(href, current_url, current_ps1) or _is_anchor_link(current_url, href) or href in lowChanceLinks or href in highChanceLinks:
                continue
            found = False
            for keyword in _KEYWORDS_LINK:
                if keyword in href.lower() or _element_contains_text(link, keyword):
                    found = True
                    break
            if found:
                highChanceLinks[href] = link
            else:
                lowChanceLinks[href] = link
        except selEx.StaleElementReferenceException as err:
            printDEBUG(ID, "%s" % err, level=2)
            continue

    retLinks = []
    highKeys = list(highChanceLinks.keys())
    random.shuffle(highKeys)
    for i in highKeys:
        link = highChanceLinks[i]
        href = i
        retLinks.append((link, href))

    lowKeys = list(lowChanceLinks.keys())
    random.shuffle(lowKeys)
    for i in lowKeys:
        link = lowChanceLinks[i]
        href = i
        retLinks.append((link, href))

    return retLinks

def find_forms(ID, driver):
    forms = driver.find_elements_by_tag_name('form')
    retForms = []
    for form in forms:
        try:
            if not form.is_displayed():
                continue
            else:
                retForms.append(form)
        except selEx.StaleElementReferenceException as err:
            printDEBUG(ID, "Error when finding forms: %s" % err, level=3)
            continue
    return retForms

def _type_in_field(comms, ID, input_field, text, clear):
    """Types text into an input field."""
    try:
        if clear:
            input_field.send_keys(Keys.CONTROL, 'a')
        input_field.send_keys(text)
        comms.add_typing(text)
        printDEBUG(ID, "%styping: %s%s" % (bcolors.WARNING, text, bcolors.ENDC), level=4)
    except selEx.ElementNotInteractableException as err:
        try:
            input_field.click()
            printDEBUG(ID, "ERROR not interactable - clicking and trying again: %s" % err, level=4)
            if clear:
                input_field.send_keys(Keys.CONTROL, 'a')
            input_field.send_keys(text)
            comms.add_typing(text)
            printDEBUG(ID, "%styping: %s%s" % (bcolors.WARNING, text, bcolors.ENDC), level=4)
        except (selEx.ElementNotInteractableException, selEx.ElementClickInterceptedException) as err:
            printDEBUG(ID, "ERROR not interactable/ intercepted: %s" % err, level=4)
            comms.add_error(repr(err))
    except selEx.InvalidArgumentException as err:
        printDEBUG(ID, "ERROR not found: %s" % err, level=4)
        comms.add_error(repr(err))
    except selEx.UnexpectedAlertPresentException as err:
        printDEBUG(ID, "Unexpected alert: %s" % err, level=4)
        comms.add_error(repr(err))
        return False
    return True


def _element_contains_text(element, text):
    """Scans various element attributes for the given text."""
    attributes = ['name', 'class', 'id', 'placeholder', 'value', 'for', 'title', 'innerHTML']
    text_list = text if type(text) is list else [text]
    for s in text_list:
        for attr in attributes:
            e = element.get_attribute(attr)
            if e is not None and s in e.lower():
                return True
    return False

def handle_input_and_submit(ID, form, webdriver, comms):
    x = ID.split("-")
    runSeed = x[0]
    procID = x[1]
    try:
        clear = True
        input_fields = form.find_elements_by_tag_name('input')
        textarea_fields = form.find_elements_by_tag_name('textarea')
        input_fields.extend(textarea_fields)
        submit_button = None
        text_field = None
        typed = False
    except selEx.StaleElementReferenceException as err:
        comms.add_error(repr(err))
        printDEBUG(ID, "Error when finding elements on page: %s" % err, level=3)
        return False
    for input_field in input_fields:
        try:
            if not input_field.is_displayed():
                continue

            type = input_field.get_attribute('type').lower()
            if type == 'email':
                # using html5 "email" type, this is probably an email field
                typed = _type_in_field(comms, ID, input_field, user_info['email'], clear)
                text_field = input_field
            elif type == 'text':
                # try to decipher this based on field attributes
                if _element_contains_text(input_field, 'company'):
                    typed = _type_in_field(comms, ID, input_field, user_info['company'], clear)
                elif _element_contains_text(input_field, 'title'):
                    typed = _type_in_field(comms, ID, input_field, user_info['title'], clear)
                elif _element_contains_text(input_field, 'name'):
                    if _element_contains_text(input_field, ['first', 'forename', 'fname']):
                        typed = _type_in_field(comms, ID, input_field, user_info['first_name'], clear)
                    elif _element_contains_text(input_field, ['last', 'surname', 'lname']):
                        typed = _type_in_field(comms, ID, input_field, user_info['last_name'], clear)
                    elif _element_contains_text(input_field, ['user', 'account']):
                        typed = _type_in_field(comms, ID, input_field, user_info['user'], clear)
                    else:
                        typed = _type_in_field(comms, ID, input_field, user_info['full_name'], clear)
                elif _element_contains_text(input_field, ['zip', 'postal']):
                    typed = _type_in_field(comms, ID, input_field, user_info['zip'], clear)
                elif _element_contains_text(input_field, 'city'):
                    typed = _type_in_field(comms, ID, input_field, user_info['city'], clear)
                elif _element_contains_text(input_field, 'state'):
                    typed = _type_in_field(comms, ID, input_field, user_info['state'], clear)
                elif _element_contains_text(input_field, _KEYWORDS_EMAIL):
                    typed = _type_in_field(comms, ID, input_field, user_info['email'], clear)
                elif _element_contains_text(input_field, "age"):
                    typed = _type_in_field(comms, ID, input_field, user_info['age'], clear)
                elif _element_contains_text(input_field, ['street', 'address']):
                    if _element_contains_text(input_field, ['2', 'number']):
                        typed = _type_in_field(comms, ID, input_field, user_info['street2'], clear)
                    elif _element_contains_text(input_field, '3'):
                        pass
                    else:
                        typed = _type_in_field(comms, ID, input_field, user_info['street1'], clear)
                elif _element_contains_text(input_field, ['phone', 'tel', 'mobile']):
                    typed = _type_in_field(comms, ID, input_field, user_info['tel'], clear)
                elif _element_contains_text(input_field, 'search'):
                    pass
                else:
                    # skip if visibly marked "optional"
                    placeholder = input_field.get_attribute('placeholder')
                    if placeholder is not None and 'optional' in placeholder.lower():
                        pass

                    # default: assume email
                    else:
                        typed = _type_in_field(comms, ID, input_field, user_info['email'], clear)
                text_field = input_field
            elif type == 'number':
                if _element_contains_text(input_field, ['phone', 'tel', 'mobile']):
                    typed = _type_in_field(comms, ID, input_field, user_info['tel'], clear)
                elif _element_contains_text(input_field, ['zip', 'postal']):
                    typed = _type_in_field(comms, ID, input_field, user_info['zip'], clear)
                else:
                    typed = _type_in_field(comms, ID, input_field, user_info['zip'], clear)
            elif type == 'checkbox' or type == 'radio':
                # check anything/everything
                if not input_field.is_selected():
                    try:
                        input_field.click()
                    except (selEx.ElementNotInteractableException, selEx.ElementClickInterceptedException) as err:
                        comms.add_error(repr(err))
                        printDEBUG(ID, "Error clicking checkbox: %s" % err, level=3)
            elif type == 'password':
                typed = _type_in_field(comms, ID, input_field, user_info['password'], clear)
            elif type == 'tel':
                typed = _type_in_field(comms, ID, input_field, user_info['tel'], clear)
            elif type == 'submit' or type == 'button' or type == 'image':
                if _element_contains_text(input_field, _KEYWORDS_SUBMIT):
                    submit_button = input_field
            elif type == 'textarea':
                typed = _type_in_field(comms, ID, input_field, user_info['message'], clear)
            elif type == 'reset' or type == 'hidden' or type == 'search':
                # common irrelevant input types
                pass
            else:
                # default: assume email
                typed = _type_in_field(comms, ID, input_field, user_info['email'], clear)

        except (selEx.StaleElementReferenceException, selEx.UnexpectedAlertPresentException) as err:
            comms.add_error(repr(err))
            printDEBUG(ID, "Error when inputting fields: %s" % err, level=3)
            continue

    # find 'button' tags (if necessary)
    try:
        if submit_button is None:
            buttons = form.find_elements_by_tag_name('button')
            for button in buttons:
                if not button.is_displayed():
                    continue

                # filter out non-submit button types
                type = button.get_attribute('type').lower()
                if type is not None and (type == 'reset' or type == 'menu'):
                    continue

                # pick first matching button
                if _element_contains_text(button, _KEYWORDS_SUBMIT):
                    submit_button = button
                    break
    except (selEx.StaleElementReferenceException, selEx.UnexpectedAlertPresentException) as err:
        comms.add_error(repr(err))
        printDEBUG(ID, "Error when finding button tags: %s" % err, level=3)

    # fill in 'select' fields
    try:
        select_fields = form.find_elements_by_tag_name('select')
        for select_field in select_fields:
            if not select_field.is_displayed():
                continue

            # select an appropriate element if possible,
            # otherwise second element (to skip blank fields),
            # falling back on the first
            select = Select(select_field)
            select_options = select.options
            selected_index = None
            for i, opt in enumerate(select_options):
                opt_text = opt.text.strip().lower()
                if opt_text in _KEYWORDS_SELECT:
                    selected_index = i
                    break
            if selected_index is None:
                selected_index = min(1, len(select_options) - 1)
            try:
                select.select_by_index(selected_index)
            except (selEx.ElementNotInteractableException, selEx.ElementClickInterceptedException, selEx.NoSuchElementException) as err:
                comms.add_error(repr(err))
                printDEBUG(ID, "Error select object not interactable: %s" % err, level=3)
    except selEx.StaleElementReferenceException as err:
        comms.add_error(repr(err))
        printDEBUG(ID, "Error when selecting fields: %s" % err, level=3)
    # debug: save screenshot
    if _DEBUG:
        webdriver.save_screenshot('./%s/screenshots/%s-%s.png' % (runSeed, ID, urlsplit(webdriver.current_url)[1]))

    # submit the form
    if submit_button is not None and typed:
        try:
            printDEBUG(ID, "Submitting form with click()", level=3)
            submit_button.click()  # trigger javascript events if possible
            comms.submitted_form()
        except:
            pass
    if text_field is not None and typed:
        try:
            text_field.send_keys(Keys.RETURN)  # press enter
            comms.submitted_form()
            printDEBUG(ID, "Submitting form with RETURN", level=3)
        except:
            pass
    if typed:
        try:
            if form.tag_name.lower() == 'form':
                form.submit()  # submit() form
                comms.submitted_form()
                printDEBUG(ID, "Submitting form with submit()", level=3)
        except:
            pass
    return typed

def _dismiss_alert(ID, webdriver):
    """Dismisses an alert, if present."""
    try:
        WebDriverWait(webdriver, 0.5).until(expected_conditions.alert_is_present())
        alert = webdriver.switch_to_alert()
        alert.dismiss()
        printDEBUG(ID, "Dismissing alert", level=3)
    except selEx.TimeoutException:
        pass

def fill(ID, driver, forms, comms):
    if forms is None:
        return False
    else:
        good = False
        comms.found_form()
        for form in forms:
            main_handle = driver.current_window_handle
            printDEBUG(ID, "Handling form on %s" % driver.current_url, level=2)
            if handle_input_and_submit(ID, form, driver, comms):
                good = True
            time.sleep(_FORM_SUBMIT_SLEEP)
            _dismiss_alert(ID, driver)
            time.sleep(1)
            wait_until_loaded(ID, driver, _PAGE_LOAD_TIME)
            # close pop-ups
            windows = driver.window_handles
            if len(windows) > 1:
                for window in windows:
                    if window != main_handle:
                        driver.switch_to_window(window)
                        driver.close()
                driver.switch_to_window(main_handle)
                time.sleep(1)
            return good

def is_loaded(ID, webdriver):
    try:
        return (webdriver.execute_script("return document.readyState") == "complete")
    except (selEx.WebDriverException, selEx.UnexpectedAlertPresentException) as err:
        printDEBUG(ID, "Error: %s" % err, level=3)
        return False

def wait_until_loaded(ID, webdriver, timeout, period=0.25):
    mustend = time.time() + timeout
    while time.time() < mustend:
        try:
            if is_loaded(ID, webdriver): return True
        except selEx.UnexpectedAlertPresentException as err:
            printDEBUG(ID, "Alert while waiting: %s" % err, level=3)
            _dismiss_alert(ID, webdriver)
        time.sleep(period)
    return False

def blacklisted(ID, url, blacklist):
    ps1 = domain_utils.get_ps_plus_1(url)
    printDEBUG(ID, "blacklist searching for: %s" % ps1, error=True, level=0)
    if ps1 in blacklist:
        printDEBUG(ID, "blacklist hit for: %s" % ps1, error=True, level=0)
        return True
    else:
        return False

# Driver needs to have a visited site in it already
#   e.g. calles driver.get and then find_and_fill(driver)


#############################################################
#############################################################
def find_and_fill(ID, driver, sites_crawled, blacklist, comms):
    wait_until_loaded(ID, driver, _PAGE_LOAD_TIME)
    if driver.current_url in sites_crawled or blacklisted(ID, driver.current_url, blacklist):
        return False
    site = driver.current_url
    sites_crawled.add(site)
    printDEBUG(ID, "WORKING ON %s" % site, level=1)
    main_handle = driver.current_window_handle
    # Step 1 find and fill form on the landing page
    forms = find_forms(ID, driver)
    if fill(ID, driver, forms, comms):
        printDEBUG(ID, "Successfully filled form", level=1)
        return True
    # If there are no forms on the landing page, find links on the landing page
    links = get_all_links(ID, driver)
    printDEBUG(ID, "Links found on %s:" % site, level=2)
    if links:
        all_links = []
        for link, href in links:
            all_links.append(href)
        pstring = " - ".join(all_links)
        printDEBUG(ID, pstring, level=2)
    else:
        printDEBUG(ID, "\tNONE", level=2)
    if links:
        printDEBUG(ID, "GOING DEEPER...", level=2)
        #dig deeper
        #TODO debug here
        counter = 0
        for link, href in links:
            printDEBUG(ID, "href: %s\tcounter: %d" % (href, counter), level=3)
            if counter >= _MAX_LINKS:
                return False
            try:
                #printDEBUG(ID, "Tying to click link to: %s" % href, level=3)
                printDEBUG(ID, "Visiting: %s" % href, level=3)
                #link.click()
                crawl_site(ID, href, driver, comms)
                if driver.current_url in sites_crawled or blacklisted(ID, driver.current_url, blacklist):
                    return False
                sites_crawled.add(driver.current_url)
            except Exception as err:
                #printDEBUG(ID, "Error clicking link: %s" % err, level=3)
                printDEBUG(ID, "Error getting link: %s" % err, level=3)
                continue 
            wait_until_loaded(ID, driver, _PAGE_LOAD_TIME)
            #printDEBUG(ID, "clicked link: %s" % driver.current_url, level=2)
            printDEBUG(ID, "visited link: %s" % driver.current_url, level=2)
            forms = find_forms(ID, driver)
            if fill(ID, driver, forms, comms):
                printDEBUG(ID, "Successfully filled form", level=2)
                return True 
            #else:
                #try:
                #    printDEBUG(ID, "Calling driver.back()", level=2)
                #    driver.back()
                #    printDEBUG(ID, "Back on page: %s" % driver.current_url, level=2)
                #except Exception as err:
                #    printDEBUG(ID, "ERROR in driver.back(): %s" % err, level=3)
                #    break
                #wait_until_loaded(ID, driver, _PAGE_LOAD_TIME)
            counter += 1
        return False
    else:
        return False

# TODO: logging out what has been done where... Need to verify working
