try:
    import tweepy
except:
    pass
import traceback
import time
import networkx as nx

def connect(token=None, token_secret=None):
    if not (token and token_secret):
        return tweepy.API()

    auth = tweepy.OAuthHandler("myAuthToken",token)
    auth.set_access_token("myAccessToken",token_secret)
    api = tweepy.API(auth)
    if api and api.verity_credentials():
        return api
    else:
        print("Login failed.")

query = '"someScreenName" OR "#sometag"' # a valid Twitter search query

def tsearch(query=query, api=None):
    q = {
        'q': query,
        'lang': 'en',
    }
    api = api or connect()
    try:
        for status in tweepy.Cursor(api.search, **q).items():
            if not process_tweet(status):
                return
    except tweepy.TweepError:
        traceback.print_exc()
        raise

class MyStreamListener(tweepy.StreamListener):
    def on_error(self, status_code):
        print 'An error has occured! Status code %s.' % status_code
        return True # keep stream alive

    def on_timeout(self):
        print 'Snoozing Zzzzzz'
        time.sleep(10)
        return True

    def on_delete(self, status_id, user_id):
        """Called when a delete notice arrives for a status"""
        #print "Delete notice for %s. %s" % (status_id, user_id)
        return

    def on_limit(self, track):
        """Called when a limitation notice arrvies"""
        print "!!! Limitation notice received: %s" % str(track)
        return

    def on_status(self, status):
        return process_tweet(status)


def start_stream(username, password, listener, follow=(), track=(), async=False):
    '''
    follow: list of users to follow
    track: list of keywords to track
    '''
    print 'Connecting as %s/%s' % (username, password)
    stream = tweepy.Stream(username, password, listener, timeout=60)
    if follow or track:
        print "Starting filter on %s/%s" % (','.join(follow), ','.join(track))
        stream.filter(follow=follow, track=track, async=async)
    else:
        print "Starting sample"
        stream.sample(async=async)

############ And now for something completely Requests.

import requests
import simplejson

def rsearch(query, **kwargs):
    """
    Simple Twitter query. 15 results returned by default.

    # Get more results:
    >>> rsearch('#pycon', rpp=100)
    # Get even more results:
    >>> rsearch('#pycon', rpp=100, page=2)
    """

    # Assemble query parameters:
    data = dict(q=query)
    data.update(kwargs)
    r = requests.post('http://search.twitter.com/search.json',
            data=data)
    for line in r.iter_lines():
        if line:
            json = simplejson.loads(line)
            results = json['results']
            return results
            # or, delete the line above and do this:
            for j in results:
                process_tweet(j)

def rstream(username, password, **kwargs):
    r = requests.post('https://stream.twitter.com/1/statuses/filter.json',
            data=kwargs, auth=(username, password))

    for line in r.iter_lines():
        if line: # filter out keep-alive new lines
            process_tweet(simplejson.loads(line))

def test_process():
    """
    Calls process_tweet() as a test.
    """
    process_tweet(None)

import sys
def process_tweet(tweet):
    #sys.stdout.write('.')
    print tweet
    return True


retweets=nx.DiGraph()
hashtag_net=nx.Graph()

import util
def process_retweets(tweet, retweets=retweets, hashtag_net=hashtag_net):
    """
    Process a single tweet and update retweets and hashtag_net graphs.
    """
    ### process tweet to extract information
    try:
        author=tweet['user']['screen_name']
        entities=tweet['entities']
        mentions=entities['user_mentions']
        hashtags=entities['hashtags']

        retweets.add_edges_from((author, x['screen_name']) for x in mentions)

        tags=[tag['text'].lower() for tag in hashtags]
        for t1 in tags:
            for t2 in tags:
                if t1 is not t2:
                    util.add_or_inc_edge(hashtag_net,t1,t2)
    except KeyError:
        pass
        #print ':-('
        #print tweet

def draw_core_retweets():
    """
    Draw the trimmed largest component of retweets.
    """
    comps = nx.connected_component_subgraphs(
            retweets.to_undirected())

