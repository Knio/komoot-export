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
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:75.0) Gecko/20100101 Firefox/75.0'})

    def login(self, username):
        password = getpass.getpass('Komoot password for {}: '.format(username))

        r = self.session.get('https://www.komoot.com/')
        r.raise_for_status()
        time.sleep(1)

        r = self.session.post('https://account.komoot.com/v1/signin',
                data=json.dumps({'email': username, 'password': '','reason': None}),
                headers={'Accept': 'application/json'})

        r.raise_for_status()
        e = r.json()['error']
        if e: raise Exception(e)
        time.sleep(1)

        r = self.session.post('https://account.komoot.com/v1/signin',
                data=json.dumps({'email': username, 'password': password,'reason': None}),
                headers={'Accept': 'application/json'})

        r.raise_for_status()
        e = r.json()['error']
        if e: raise Exception(e)
        time.sleep(1)

        r = self.session.get('https://account.komoot.com/api/account/v1/session?hl=en')
        r.raise_for_status()
        time.sleep(1)

        ### old login below
        # r = self.session.post('https://www.komoot.com/webapi/v006/auth/cookie',
        #         data={'username': username, 'password': password},
        #         headers={'Accept': 'application/json'})


        # r.raise_for_status()
        # print(r.text)
        # time.sleep(1)

        # r = self.session.get('https://www.komoot.com/heartbeat',
        #         headers={'Accept': 'application/json'})
        # r.raise_for_status()
        # print(r.text)
        # time.sleep(1)

    def get_tours(self, user_id):
        tours = []
        page = 0
        while True:
            r = self.session.get(
                'https://www.komoot.com/api/v007/users/{}/activities/?page={}&limit=50'.format(user_id, page))
            r.raise_for_status()
            data = r.json()
            page_tours = data['_embedded']['items']
            tours += page_tours
            page += 1
            if page >= data['page']['totalPages']:
                break
        log.info('Loaded %d tours for user_id %s', len(tours), user_id)
        return tours

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
        if filename.endswith('_gpx'):
            filename = filename[:-4] + '.gpx'
        log.debug('Downloaded tour %s to %s', tour_id, filename)
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
            tour_id = tour['_embedded']['tour']['id']
            exists = already_downloaded(tour_id)
            if exists:
                log.info('Tour {} is already synced as {}'.format(tour_id, exists))
                continue
            try:
                filename, gpx = self.get_tour_gpx(tour_id)
                open(filename, 'w', encoding='utf-8').write(gpx)
                log.info('Tour {} saved as {}'.format(tour_id, filename))
            except requests.exceptions.HTTPError as e:
                log.error('Failed to download tour %s: %r', tour_id, e)


def export():
    logging.basicConfig(level=logging.INFO)
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
