import flask
import random
import string
import arrow
import json
import os
import threading
import time
import pickle

import timeit


def chunk_list(input_list: list, chunk_size: int) -> list[list]:
    return [input_list[i:i + chunk_size] for i in range(0, len(input_list), chunk_size)]

class LinkManager():
    class Link():
        REDIRECT_ID: str = None
        ENDPOINT: str = None
        OWNER: str = None
        EXPIRE: arrow.Arrow = None

        def __init__(self, redirect_id: str, endpoint: str, owner: str, expire: dict[str, int]):
            self.REDIRECT_ID = redirect_id
            self.ENDPOINT = endpoint
            self.OWNER = owner
            self.EXPIRE = arrow.now().shift(**expire)

        def is_valid(self):
            return not arrow.now() > self.EXPIRE


    LINKS: list[Link] = []

    def register_link(self, owner: str, endpoint: str, expire: dict[str, int], prefered_id: str = '', max_user_links: int = 5):
        user_link_count: int = 0
        is_prefered_id_taken: bool = False
        redirect_id: str = None

        for link in self.LINKS:
            if link.OWNER == owner:
                user_link_count += 1
            if prefered_id and (not is_prefered_id_taken) and link.REDIRECT_ID == prefered_id:
                is_prefered_id_taken = True

        if user_link_count > max_user_links:
            return
        
        if is_prefered_id_taken:
            is_redirect_id_taken = True

            i = 0
            while is_redirect_id_taken or i > 10:
                redirect_id = prefered_id+''.join(random.choices(string.ascii_letters+string.digits, k=5))

                is_redirect_id_taken = False
                if self.get_endpoint(redirect_id):
                    is_redirect_id_taken = True
                i += 1
            if i > 10:
                return None
        else:
            redirect_id = prefered_id

        new_link = self.Link(redirect_id, endpoint, owner, expire)
        self.LINKS.append(new_link)
        return new_link

    def get_endpoint(self, redirect_id: str):
        for link in self.LINKS:
            if link.REDIRECT_ID == redirect_id:
                return link.ENDPOINT
        return None

    def filter_expired(self):
        list(filter(lambda link: link.is_valid(), self.LINKS))

    def debug_fill_links(self):
        for _ in range(100_000):
            self.LINKS.append(self.Link('', '', str(random.randint(1000, 9999)), {'days':random.randint(0, 1)}))

    def save_links(self):
        with open('links.database', 'wb') as f:
            pickle.dump(self.LINKS, f)
        
    def load_links(self):
        if not os.path.exists('links.database'):
            return
        with open('links.database', 'rb') as f:
            self.LINKS = pickle.load(f)


app = flask.Flask(__name__)
lm = LinkManager()
lm.load_links()

MAX_USER_LINKS = 5

@app.route('/')
def index():
    return flask.render_template('index.html')

@app.route('/show_link/<redirect_id>')
def show_link(redirect_id):
    return flask.render_template('generated.html', redirect_id=redirect_id)

@app.route('/failed_to_generate')
def failed_to_generate():
    return flask.render_template('failed_to_generate.html')

@app.route('/r/<redirect_id>')
def redirect(redirect_id: str):
    url = lm.get_endpoint(redirect_id)
    if not url: url = flask.url_for('index')
    return flask.redirect(url)

@app.route('/api/register_redirect')
def api_register_link():
    prefered_id = flask.request.args.get('prefered_id')
    endpoint = flask.request.args.get('endpoint')
    new_link = lm.register_link(flask.request.remote_addr, endpoint, {'days':1}, prefered_id, MAX_USER_LINKS)
    if not new_link:
        return flask.redirect(flask.url_for('failed_to_generate'))
    print(new_link.REDIRECT_ID)
    return flask.redirect(flask.url_for('show_link', redirect_id = new_link.REDIRECT_ID))

if __name__ == '__main__':
    threading.Thread(target=app.run, args=('0.0.0.0', 5000)).start()
    while True:
        lm.filter_expired()
        lm.save_links()
        time.sleep(5)