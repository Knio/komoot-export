'''
GPX Exporter for Komoot.

This script will download all recorded tours in Komoot to .gpx files
'''

import argparse
import getpass
import json
import logging
import os
import time
import urllib

import requests

log = logging.getLogger()


class KomootExport(object):
    def __init__(self):
        self.user = None
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:58.0) Gecko/20100101 Firefox/58.0'})

    def login(self, username):
        password = getpass.getpass('Komoot password for {}: '.format(username))

        r = self.session.get('https://www.komoot.com/')
        r.raise_for_status()
        time.sleep(1)
        self.session.headers.update({'Accept': 'application/json'})

        r = self.session.post('https://www.komoot.com/webapi/v006/auth/cookie',
                data={'username': username, 'password': password})
        r.raise_for_status()
        time.sleep(1)

        r = self.session.get('https://www.komoot.com/heartbeat')
        print(r.text)
        r.raise_for_status()
        self.user = r.json()['user']
        time.sleep(1)


    def get_tours_html(self, user_id):
        r = self.session.get('https://www.komoot.com/user/{}/tours'.format(user_id))
        r.raise_for_status()
        return r.text

    def get_tours(self, user_id):
        tours_html = self.get_tours_html(user_id)
        tours = self.parse_tours(tours_html)['tours']
        log.debug('Loaded %d tours for user_id %s', len(tours), user_id)
        return tours

    @staticmethod
    def parse_tours(html):
        start_index = html.index('kmtBoot.setProps(')
        end_index = html.index(');\n    </script>', start_index);
        data = html[start_index + 18 : end_index - 1]
        data = data.encode('utf-8').decode('unicode_escape')
        data = json.loads(data)
        return data

    def get_tour_gpx(self, tour_id):
        time.sleep(2)
        log.debug('Getting tour_id %d', tour_id)
        r = self.session.get(
            'https://www.komoot.com/api/v007/tours/{}.gpx'.format(tour_id))
        r.raise_for_status()
        content_dispostinion = r.headers['Content-disposition']
        params = content_dispostinion.split(';')
        _value = params.pop(0)
        params = {
            k.strip():v.strip()[1:-1].encode('utf-8').decode('unicode_escape')
            for k,v in (p.split('=') for p in params)}
        filename = urllib.parse.unquote(params['filename'])
        filename = filename.translate({ord(i):'_' for i in r' ,<.>/?;:\'"[{]}\|=+'})
        log.debug('Got tour %s with filename %s', tour_id, filename)
        return filename, r.text

    def download_all_tours(self, user_id=None):
        if not user_id:
            user_id = self.user['username']
        tours = self.get_tours(user_id)
        existing_files = os.listdir('.')

        def already_downloaded(tour_id):
            for f in existing_files:
                if '_{}_'.format(tour_id) in f:
                    return f

        for tour in tours:
            tour_id = tour['id']
            exists = already_downloaded(tour_id)
            if exists:
                log.info('{} is already synced as {}'.format(tour_id, exists))
            else:
                filename, gpx = self.get_tour_gpx(tour_id)
                open(filename, 'w', encoding='utf-8').write(gpx)
                log.info('{} saved as {}'.format(tour_id, filename))


def export():
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user-name',
        help='User name (email) to log in as. Not required to export public tours.',
        required=False)
    parser.add_argument('--user-id',
        help='User ID of tours to export.',
        required=True)
    args = parser.parse_args()

    komoot_export = KomootExport()
    # turns out komoot doesn't actually auth check the gpx endpoint so this is optional ¯\_(ツ)_/¯
    if args.user_name:
        komoot_export.login(args.user_name)
    komoot_export.download_all_tours(args.user_id)


if __name__ == '__main__':
    export()
