import argparse
import csv
import datetime
import os
import re
import socket
import time
import urllib
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor, wait

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
DEBUG = False

class whichAlive(object):
    def __init__(self, file, THREAD_POOL_SIZE=10, allow_redirect=False, PROXY={}):
        self.file = file
        self.filename = ''.join(file.split('/')[-1].split('.')[:-1])
        self.outfilename = f'{self.filename}{str(time.time()).split(".")[0]}.csv'
        self.urllist = self.__urlfromfile()
        self.tableheader = ['no', 'url', 'ip', 'state',
                            'state_code', 'title', 'server', 'length']
        self.HEADER = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36',
        }
        self.THREAD_POOL_SIZE = THREAD_POOL_SIZE
        self.allurlnumber = len(self.urllist)
        self.completedurl = -1
        self.allow_redirect = allow_redirect
        self.PROXY = PROXY

    def run(self):
        self.completedurl += 1
        self.__writetofile(self.tableheader)
        tasklist = []
        start_time = datetime.datetime.now()
        t = ThreadPoolExecutor(max_workers=self.THREAD_POOL_SIZE)
        for k, url in enumerate(self.urllist):
            tasklist.append(t.submit(self.__scan, url, k+1))
        print(f'total {self.allurlnumber}')
        if wait(tasklist, return_when=ALL_COMPLETED):
            end_time = datetime.datetime.now()
            print(f'--------------------------------\nDONE, use {(end_time - start_time).seconds} seconds')
            print(f'outfile: {os.path.join(os.path.abspath(os.path.dirname(__file__)), "result", self.outfilename)}')

    def __scan(self, url, no):
        state_code = -1
        title = ''
        length = -1
        try:
            if DEBUG:
                print(f'[+] {no} {url}')
            u = urllib.parse.urlparse(url)
            ip = self.__getwebip(u.netloc)
            if self.allow_redirect:
                r = requests.get(url=url, headers=self.HEADER, timeout=15, verify=False, proxies=self.PROXY)
                state = 'alive'
                state_code = '->'.join([str(i.status_code) for i in r.history] + [str(r.status_code)])
                title = '->'.join([self.__getwebtitle(i) for i in r.history] + [self.__getwebtitle(r)])
                length = '->'.join([str(self.__getweblength(i)) for i in r.history] + [str(self.__getweblength(r))])
                server = '->'.join([self.__getwebserver(i) for i in r.history] + [str(self.__getwebserver(r))])
            else:
                r = requests.get(url=url, headers=self.HEADER, allow_redirects=False, timeout=15, verify=False, proxies=self.PROXY)
                state = 'alive'
                state_code = r.status_code
                title = self.__getwebtitle(r)
                length = self.__getweblength(r)
                server = self.__getwebserver(r)
        except requests.exceptions.ConnectTimeout:
            state = 'dead'
        except requests.exceptions.ReadTimeout:
            state = 'dead'
        except requests.exceptions.ConnectionError:
            state = 'dead'
        self.completedurl += 1
        thisline = [no, url, ip, state, state_code, title, server, length]
        nowpercent = '%.2f'%((self.completedurl/self.allurlnumber)*100)
        print(f'[{nowpercent}%] {url} {ip} {state} {title} {length}')
        self.__writetofile(thisline)

    def __getwebtitle(self, r):
        try:
            return re.findall(r'<title>(.*?)</title>', r.text)[0]
        except:
            return ''

    def __getwebip(self, domain):
        try:
            ip = socket.getaddrinfo(domain, 'http')
            return ip[0][4][0]
        except:
            return ''

    def __getweblength(self, r):
        try:
            return len(r.content)
        except:
            return -1

    def __getwebserver(self, r):
        try:
            return r.headers.get('server') if r.headers.get('server') else ''
        except:
            return ''

    def __urlfromfile(self):
        with open(self.file, 'r') as f:
            return [i.replace('\n', '').replace('\r', '') for i in f.readlines()]

    def __writetofile(self, data: list):
        f = open(f'result/{self.outfilename}', 'a')
        writer = csv.writer(f)
        writer.writerow(data)
        f.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(usage='whichAlive usage')
    parser.add_argument('-f', '--file', default='url.txt', help='URL lists file.')
    parser.add_argument('--proxy', default='', help='Set proxy, such as 127.0.0.1:8080')
    parser.add_argument('-t', '--thread', default=10, type=int, help='Set max threads, default 10')
    parser.add_argument('-d', '--debug', default=False, action='store_true', help='print some debug information')
    args = parser.parse_args()

    DEBUG = args.debug

    w = whichAlive(
        file=args.file,
        THREAD_POOL_SIZE=args.thread,
        allow_redirect=True,
        PROXY={'http': args.proxy, 'https': args.proxy}
    )
    w.run()

