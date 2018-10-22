from selenium import webdriver
import urllib2
from bs4 import BeautifulSoup
import urlparse
import requests
def get_browser_with_url(url, timeout=120, driver="phantomjs"):
    # set phantomjs user-agent
    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_3) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/7046A194A"
    )
    # get phantomjs execute path

    browser = webdriver.PhantomJS(executable_path=exe_path, desired_capabilities=dcap)
    
    # set maximum load time
    browser.set_page_load_timeout(timeout)

    # open a browser with given url
    browser.get(url)
    time.sleep(0.5)

    return browser

def search(query_url):

    # get html
    # use phantomjs to get html or use scrapy
    browser = get_browser_with_url(query_url)
    browser.get(query_url)
    if html:
    	#parser html
    	soup = BeautifulSoup(html, "html.parser")

        for div in divs:
        	# find key and value
