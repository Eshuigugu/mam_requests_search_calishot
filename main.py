import time
import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder
import json
from bs4 import BeautifulSoup


def test_url(url, sess=requests.Session()):
    try:
        return sess.get(url, timeout=10).status_code == 200
    except:
        return False


if __name__ == '__main__':
    keepGoing = True
    start_idx = 0
    req_books = []

    sess = requests.Session()

    # fetch list of requests to search for
    while keepGoing:
        time.sleep(1)
        url = 'https://www.myanonamouse.net/tor/json/loadRequests.php'
        headers = {
            'cookie': 'get cookie header(s) and user-agent from developer tools > network activity',
            'user-agent': ''
        }

        params = {
            'tor[text]': '',
            'tor[srchIn][title]': 'true',
            'tor[viewType]': 'unful',
            'tor[cat][]': 'm14',  # search ebooks category
            'tor[startDate]': '',
            'tor[endDate]': '',
            'tor[startNumber]': f'{start_idx}',
            'tor[sortType]': 'dateD'
        }
        data = MultipartEncoder(fields=params)
        headers['Content-type'] = data.content_type
        r = sess.post(url, headers=headers, data=data)
        req_books += r.json()['data']
        total_items = r.json()['found']
        start_idx += 100
        keepGoing = total_items > start_idx

    req_books_reduced = [x for x in req_books if
                         x['cat_name'].startswith('Ebooks') and x['filled'] == 0 and x['torsatch'] == 0 and x[
                             'lang_code'] == 'ENG']

    json_columns = ['cover', 'title', 'authors', 'links', 'tags', 'identifiers', 'formats']
    hits_misses = [0, 0]
    hits_ids = []
    # get a working calishot host
    for calishot_url in ['https://eng.calishot.xyz/index-eng/summary.json', 'https://calishot-eng-2.herokuapp.com/index-eng/summary.json']:
        if test_url(calishot_url, sess=sess):
            break
    for book in req_books_reduced:
        book['url'] = 'https://www.myanonamouse.net/tor/viewRequest.php/' + str(book['id'])[:-5] + '.' + str(book['id'])[-5:]
        title = BeautifulSoup(f'<h1>{book["title"]}</h1>', features="lxml").text
        for k, author in json.loads(book['authors']).items():
            break
        request_params = {
                          '_search': f'{title} {author}',
                          '_sort': 'uuid'
                          }

        time.sleep(1)
        r = sess.get(calishot_url, params=request_params, timeout=60)
        columns = r.json()['columns']

        # restructure the json results
        results = [{k: json.loads(v) if v and k in json_columns else v for k,v in
                    zip(columns, x)} for x in r.json()['rows']]

        # try fetching the cover images to ensure the calibre libraries are online
        results = [x for x in results if test_url(x['cover']['img_src'], sess=sess)]
        if results:
            hits_misses[0] += 1
            print(book['url'], title, f'got {len(results)} hits', [x['title'] for x in results])
        else:
            hits_misses[1] += 1
    print(hits_misses)

