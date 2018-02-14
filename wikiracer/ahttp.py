'''
Main handler for wikiracer.
'''

import asyncio
import re

from aiohttp import ClientSession
from aiohttp.client_exceptions import ServerDisconnectedError
from bs4 import BeautifulSoup

from .redis_utils import redis_get, redis_set
from .settings import WIKI_PREFIX, WIKI_IGNORE_EXP

# Semaphore that limits number of calls to wikipedia
sem_fetch_url = asyncio.Semaphore(750)
# Semaphore to limit number of sub tasks in do_work
sem_do_work = asyncio.Semaphore(500)
# NOTE: Setting to higher value for above variables leads slowing down of do_work due to high
# number of pagefaults and async operations overhead.

def construct_url(title):
    '''
    Contruct the wiki url from title
    '''
    return WIKI_PREFIX + title


async def url_exists(url):
    '''
    Verify if url exists
    '''
    url = construct_url(url)
    async with ClientSession() as session:
        async with session.get(url) as response:
            return response.status == 200


async def url_contents(url, lock):
    '''
    Get contents from url
    '''
    url = construct_url(url)
    response_text = None
    # for rate limiting.
    async with sem_fetch_url:
        if lock.is_set():
            return
        async with ClientSession() as session:
            try:
                async with session.get(url) as response:
                    # Ignore urls that don't return a 200 response
                    if response.status == 200:
                        response_text = await response.text()
                        return response_text
            except ServerDisconnectedError as sde:
                print('Server disconnected for url:%s', url)
                # site is refusing connections. No use trying further??
                lock.set()
    return response_text


async def get_links(url, lock, dest_link=None):
    '''
    Parse wiki page links
    '''
    hrefs = []
    # Avoid request to url if data is available in redis.
    redis_data = await redis_get(url)
    # If lock is set, no need to proceed further
    if lock.is_set():
        return hrefs
    elif redis_data:
        print('url data fetched from redis:%s' % url)
        return redis_data
    response_text = await url_contents(url, lock)
    print('url data fetched from source:%s' % url)
    # If lock is set at this point, avoid further cpu processsing.
    if lock.is_set():
        return hrefs
    # TODO: Perhaps use an async parser.
    if response_text:
        soup = BeautifulSoup(response_text, 'html.parser')
        # Handle orphan pages.
        if soup.find('table', {'class': re.compile('ambox-Orphan')}):
            print('Orphan page found:%s' % url)
            return []
        # select all hrefs linking to other wiki pages
        links = soup.find_all(href=re.compile('^/wiki/'))
        hrefs = [item.get('href').lstrip('/wiki/') for item in links]
        # remove duplicates
        hrefs = set(hrefs)
        # set lock and return immediately if target is found.
        # no need to wait for redis_set...
        if dest_link and dest_link in hrefs:
            lock.set()
            return hrefs
        # ignore wikipedia related special urls.
        hrefs = [item for item in hrefs if not WIKI_IGNORE_EXP.match(item)]
        # remove source url to avoid unnecessary recursion.
        if url in hrefs:
            hrefs.remove(url)
        # store data in redis to avoid parsing next time.
        await redis_set(url, hrefs)
        print('Got %d links for source:%s' % (len(hrefs), url))
    return hrefs


async def get_sorted_links(url, dest_link, dest_links, lock, traversed):
    '''
    Parse wiki page links and sort links to so that items intersecting with dest_links are at the
    front.
    '''
    print('called get_sorted_links for url:%s' % url)
    if url in traversed:
        print('url already traversed:%s' % url)
        return []
    links = await get_links(url, lock, dest_link)
    if links and url not in traversed:
        traversed.append(url)
    # put items found in dest_links at the front of links list returned.
    # get intersection between two lists and give the intersection links priority by placing them
    # ahead in the returned links
    if links and dest_links:
        intersection_links = list(set(links) & set(dest_links))
        if intersection_links:
            remaining_links = [item for item in links if item not in dest_links]
            links = intersection_links + remaining_links
    return links


async def find_relationship(src_link, dest_link, dest_links, sem_parent, lock_parent, lock, traversed):
    '''
    Fetch links between source and dest_link in context of async lock.
    '''
    # Introduce rate-limiting to ensure that not more than configured no. of tasks are executed
    # concurrently. 
    await sem_do_work.acquire()
    # If another branch of tree has found the link, return immediately.
    if lock.is_set():
        return
    # The sem_parent and lock_parent ensure that child tasks are not started until all parent
    # tasks are completed.
    async with sem_parent:
        src_links = await get_sorted_links(src_link, dest_link, dest_links, lock, traversed)
        # When the semaphore value becomes 0, set lock so that child tasks can start.
        if sem_parent._value == 0:
            lock_parent.set()
    # if dest_link is one of the links, stop execution and return results.
    # sometimes, two sublinks can link to the original source
    if src_links and dest_link in src_links:
        print('Success. Found %s through %s' % (dest_link, src_link))
        # set the lock to prevent unnecessary executions in other async tasks.
        lock.set()
        return [src_link, dest_link]
    elif src_links and not lock.is_set():
        # Release the ratelimiting semaphore.
        sem_do_work.release()
        # wait until the lock_parent is set i.e. all parent nodes have been evaluated.
        # If this lock isn't set, the program spends most of its time traversing
        # wikipedia instead of doing any real work...
        await lock_parent.wait()
        # Remove all traversed nodes from src_links to avoid further processing
        src_links = [item for item in src_links if item not in traversed]
        # build dest_link once.
        if not dest_links:
            # The dest_link links are most likely to have a link to the actual dest_link, so
            # these are prioritised during our search.
            dest_links = await get_links(dest_link, lock)
            if len(dest_links) == 0:
                print('Destination is an orphan page:%s' % dest_link)
                return
        # create semaphore with initial value as len of dest_links. This ensures that all
        # children are evaluated before grand-children are spawned.
        sem_children = asyncio.Semaphore(len(dest_links))
        lock_children = asyncio.Event()
        # Create find_relationship futures for each of the links obtained.
        # Remember that the tasks start as soon as the future is created.
        future_tasks = [asyncio.ensure_future(find_relationship(item,
                                                                dest_link,
                                                                dest_links,
                                                                sem_children,
                                                                lock_children,
                                                                lock,
                                                                traversed))
                        for item in src_links]
        # TODO: try-except block for timeout?
        done, pending = await asyncio.wait(future_tasks, return_when=asyncio.FIRST_COMPLETED)
        # cancel all the pending tasks as they are no longer required.
        for task in pending:
            task.cancel()
        # get output from done task, prepend current source and return
        # NOTE: Possible that certain tasks are done but with no output due to return after lock check.
        for task in done:
            output = task.result()
            # return data only for task in the success path.
            if output:
                print('Success. Return %s' % ([src_link] + output))
                return [src_link] + output
    # arrgh... no source links because node has already been evaluated. Wait for lock.
    await lock.wait()
    # NOTE: If task rate-limiting is desired, check if it's easier to cancel the current task instead of
    # waiting on lock


async def do_work(src_link, dest_link):
    '''
    Starting point for the wikiracer
    '''
    # TODO: Ensure that source and dest_link are valid urls.
    source_exists = await url_exists(src_link)
    if not source_exists:
        raise Exception('Invalid source title page:' + src_link)
    dest_link_exists = await url_exists(dest_link)
    if not dest_link_exists:
        raise Exception('Invalid destination title page:' + dest_link)
    # create lock used to co-ordinate find_relationship tasks and stop other tasks when one of them
    # has successfully found the link.
    lock = asyncio.Event()
    # create a traversed list used to maintain list of traversed links that are not processed the
    # second time round.
    traversed = []
    # At the top level, value of semaphore can be one.
    sem_parent = asyncio.Semaphore(1)
    lock_parent = asyncio.Event()
    links = await find_relationship(src_link, dest_link, None, sem_parent, lock_parent, lock, traversed)
    return links


# finished = loop.run_until_complete(do_work('Giraffe', 'Beer'))
# Test for orphaned link
# finished = loop.run_until_complete(do_work('Giraffe', 'Chugaister'))
