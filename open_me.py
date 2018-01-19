import urllib2
import json
import base64
import webbrowser
from urlparse import urlparse
import getpass
import sys
import argparse
import unittest

def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', help='Enter username')
    parser.add_argument('-r', nargs='*', help='Enter repositories')
    return parser.parse_args(args)



class Request(urllib2.Request):

    def __add__(self, other):
        request = Request(self.get_full_url() + other)
        for name, value in self.headers.items():
            request.add_header(name, value)
        return request

errors = {
    401: 'Unauthorized',
    404: 'Not found Page',
    304: 'Not Modified',
    400: 'Bad request',
    403: 'Forbidden',
    500: 'Internal Server Error'
}

class BitBucket(object):

    def __init__(self, username, password, repositories=[]):
        self.__api_version = '2.0'
        self.pull_request_limit = 10
        self.base_url = 'https://api.bitbucket.org'
        self.username = username
        self.__password = password
        self.basic_auth =  base64.b64encode('%s:%s' % (username, self.__password))
        self.repositories = repositories
        self.pull_requests = []

    def _get_repositories(self):
        '''
            get all user repositories with pagination
            return generator
        '''
        repositories_list = ['/repositories?role=contributor&role=admin']
        while repositories_list:
            url = repositories_list.pop()
            repositories = self.__send_request(url)
            for repository in repositories.get('values'):
                yield repository.get('full_name')
            if repositories.get('next', False):
                repositories_list.append('/repositories?{}'.format(urlparse(repositories['next']).query))

    def _get_pull_requests(self):
        repositories = self._get_repositories()
        if self.repositories:
            repositories = (repository for repository in repositories if self.format_name(repository) in self.repositories)
        for repository in repositories:
            pr_url = '/repositories/{}/pullrequests'.format(repository)
            pull_requests = self.__send_request(pr_url)
            for pr in pull_requests.get('values'):
                yield pr.get('links')['html']['href']

    def open_pull_requests(self):
        prs = self._get_pull_requests()
        for url in prs:
            self.pull_requests.append(url)
            if len(self.pull_requests) > self.pull_request_limit:
                raise ValueError('Too many PRs, try to filter by repository')
            webbrowser.open(url)

    def connection(self):
        try:
            print('connection...')
            request = Request(self.base_url)
            request.add_header('authorization', 'Basic %s' % self.basic_auth)
            urllib2.urlopen(request)
            self.request = request
        except urllib2.HTTPError as e:
            print(errors.get(e.code), e.msg)
            raise e

    def __send_request(self, url):
        if not hasattr(self, 'request'):
            raise ValueError('not has connection \n call connection method')
        try:
            url_to_send = self.request + '{}{}{}'.format('/', self.__api_version, url)
            res = urllib2.urlopen(url_to_send)
            return json.loads(res.read())
        except urllib2.HTTPError as e:
            print(errors.get(e.code), e.msg)
            raise e

    def format_name(self, name):
        return name.split('/')[-1]


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])

    if not args.u:
        print('Not found username \n run python script_name.py --help for more information')
    else:
        password = getpass.getpass(prompt='Enter password:')
        bitbucket = BitBucket(args.u, password, args.r)
        bitbucket.connection()
        bitbucket.open_pull_requests()
        if not bitbucket.pull_requests:
            print('not found pull requests')


class TestCase(unittest.TestCase):
    def setUp(self):
        self.bitbucket = BitBucket('test_user_name', 'test_password')

    def test_check_user(self):
        try:
            self.bitbucket.connection()
        except urllib2.HTTPError as e:
            self.assertEqual(e.code, 401)

    def test_check_connection(self):
        try:
            self.bitbucket.open_pull_requests()
        except ValueError as e:
            self.assertEqual(e.message, 'not has connection \n call connection method')

    def tearDown(self):
        self.bitbucket = None