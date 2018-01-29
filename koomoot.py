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

import requests

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


class KomootExport(object):
    def __init__(self, username):
        self.username = username
        self.session = requests.Session()

    def login(self):
        password = getpass.getpass('Komoot password for {}: '.format(self.username))
        r = self.session.get('https://www.komoot.com/')
        r = self.session.post('https://www.komoot.com/webapi/v006/auth/cookie',
                data={'username': self.username, 'password': password})

    def get_tours_html(self):
        r = session.get('https://www.komoot.com/user/542825766821/tours')
        return r.text

    def get_tours(self):
        tours_html = open('tours.html', encoding='utf-8').read()
        tours = self.parse_tours(tours_html)['tours']
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
        r = self.session.get(
            'https://www.komoot.com/api/v006/tours/{}/export'.format(tour_id))
        content_dispostinion = r.headers['Content-disposition']
        params = content_dispostinion.split(';')
        _value = params.pop(0)
        params = {
            k.strip():v.strip()[1:-1].encode('utf-8').decode('unicode_escape')
            for k,v in (p.split('=') for p in params)}
        filename = params['filename']
        return filename, r.text

    def download_all_tours(self):
        tours = self.get_tours()
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--user', required=True)
    args = parser.parse_args()

    komoot_export = KomootExport(args.user)
    komoot_export.login()
    komoot_export.download_all_tours()


if __name__ == '__main__':
    export()
