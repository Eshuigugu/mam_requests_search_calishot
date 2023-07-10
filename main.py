import time
import requests
import json
import os
import pickle
from appdirs import user_data_dir
import html


CALISHOT_JSON_COLUMNS = ('cover', 'title', 'authors', 'links', 'tags', 'identifiers', 'formats')
# this script does create some files under this directory
appname = "search_calishot"
appauthor = "Eshuigugu"
data_dir = user_data_dir(appname, appauthor)
cookies_filepath = os.path.join(data_dir, 'cookies.pkl')
mam_blacklist_filepath = os.path.join(data_dir, 'blacklisted_ids.txt')

if not os.path.isdir(data_dir):
    os.makedirs(data_dir)

if os.path.exists(mam_blacklist_filepath):
    with open(mam_blacklist_filepath, 'r') as f:
        blacklist = set([int(x.strip()) for x in f.readlines()])
else:
    blacklist = set()

sess = requests.Session()
if os.path.exists(cookies_filepath):
    cookies = pickle.load(open(cookies_filepath, 'rb'))
    sess.cookies = cookies


def test_url(url, sess=requests.Session()):
    try:
        return sess.get(url, timeout=10).status_code == 200
    except:
        return False


def get_mam_requests(limit=5000):
    url = 'https://www.myanonamouse.net/tor/json/loadRequests.php'
    keepGoing = True
    start_idx = 0
    req_books = []

    # fetch list of requests to search for
    while keepGoing:
        time.sleep(1)
        headers = {}
        # fill in mam_id for first run
        # headers['cookie'] = 'mam_id='

        query_params = {
            'tor[text]': '',
            'tor[srchIn][title]': 'true',
            'tor[viewType]': 'unful',
            'tor[startDate]': '',
            'tor[endDate]': '',
            'tor[startNumber]': f'{start_idx}',
            'tor[sortType]': 'dateD'
        }
        headers['Content-type'] = 'application/json; charset=utf-8'

        r = sess.get(url, params=query_params, headers=headers, timeout=60)
        if r.status_code >= 300:
            raise Exception(f'error fetching requests. status code {r.status_code} {r.text}')

        req_books += r.json()['data']
        total_items = r.json()['found']
        start_idx += 100
        keepGoing = min(total_items, limit) > start_idx and not \
            {x['id'] for x in req_books}.intersection(blacklist)

    # save cookies for later. yum
    with open(cookies_filepath, 'wb') as f:
        pickle.dump(sess.cookies, f)

    with open(mam_blacklist_filepath, 'a') as f:
        for book in req_books:
            f.write(str(book['id']) + '\n')
            book['url'] = 'https://www.myanonamouse.net/tor/viewRequest.php/' + \
                          str(book['id'])[:-5] + '.' + str(book['id'])[-5:]
            book['title'] = html.unescape(str(book['title']))
            if book['authors']:
                book['authors'] = [author for k, author in json.loads(book['authors']).items()]
    return req_books


def search_calishot(title, author):
    request_params = {
        '_search': f'{title} {author}',
        '_sort': 'uuid'
    }
    time.sleep(1)
    r = sess.get(CALISHOT_URL, params=request_params, timeout=60)
    columns = r.json()['columns']

    # restructure the json results
    results = [{k: json.loads(v) if v and k in CALISHOT_JSON_COLUMNS else v for k, v in
                zip(columns, x)} for x in r.json()['rows']]
    for result in results:
        result['url'] = result['title']['href']
        result['title'] = result['title']['label']

    # try fetching the cover images to ensure the calibre libraries are online
    return [x for x in results if test_url(x['cover']['img_src'], sess=sess)]


def pretty_print_hits(mam_book, hits):
    print(mam_book['title'])
    print(' ' * 2 + mam_book['url'])
    if len(hits) > 5:
        print(' ' * 2 + f'got {len(hits)} hits')
        print(' ' * 2 + f'showing first 5 results')
        hits = hits[:5]
    for hit in hits:
        print(' ' * 2 + hit["title"])
        print(' ' * 4 + hit['url'])
    print()


def should_search_for_book(mam_book):
    return mam_book['cat_name'].startswith('Ebooks') \
           and mam_book['filled'] == 0 \
           and mam_book['torsatch'] == 0 \
           and mam_book['id'] not in blacklist


def main():
    req_books = get_mam_requests()
    for book in filter(should_search_for_book, req_books):
        if not book['authors']:
            continue
        hits = search_calishot(book["title"], book["authors"][0])
        if hits:
            pretty_print_hits(book, hits)


# get a working calishot host
for CALISHOT_URL in ['https://eng.calishot.xyz/index-eng/summary.json', 'https://calishot-eng-2.herokuapp.com/index-eng/summary.json']:
    if test_url(CALISHOT_URL, sess=sess):
        break


if __name__ == '__main__':
    main()

