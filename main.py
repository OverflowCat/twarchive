from itertools import count
import tweepy
import os
import dotenv
import requests
from termcolor import colored, cprint
import json
import codecs
import re
import os
import sys
dotenv.load_dotenv()

def auth(use_proxy=False):
    if use_proxy:
        os.environ['http_proxy'] = 'http://127.0.0.1:2080'
        os.environ['https_proxy'] = 'http://127.0.0.1:2080'
    # consumer_key = os.environ["T1"]
    # consumer_secret = os.environ["T2"]
    # access_token = ["T3"]
    # access_token_secret = ["T4"]
    auth = tweepy.OAuthHandler(os.environ["T1"], os.environ["T2"])
    auth.set_access_token(os.environ["T3"], os.environ["T4"])
    return tweepy.API(auth, wait_on_rate_limit=True)

def create_dir(folder_path: str):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

def retry(times: int):
    """
    Retry Decorator
    Retries the wrapped function/method `times` times if the exceptions listed
    in ``exceptions`` are thrown
    :param times: The number of times to repeat the wrapped function/method
    :type times: Int
    """
    def decorator(func):
        def newfn(*args, **kwargs):
            attempt = 0
            while attempt < times:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(colored(str(e), 'red'))
                    print(
                        'Exception thrown when attempting to run %s, attempt '
                        '%d of %d' % (func, attempt, times)
                    )
                    attempt += 1
            return func(*args, **kwargs)
        return newfn
    return decorator

@retry(3)
def download_file(url: str, filename: str) -> bool:
    print(colored("Downloading ", "yellow") + url)
    with open(filename, 'wb') as f:
        f.write(requests.get(url).content)

def archive_user(username, api):

    create_dir("./" + username)
    images_dir = f"./{username}/images"
    create_dir(images_dir)
    videos_dir = f"./{username}/videos"
    create_dir(videos_dir)

    all_tweets = []
    newest_id = 1621183597639999999
    while len(all_tweets) < 114514:
        tweets = api.user_timeline(
            screen_name=username,
            # 200 is the maximum allowed count
            count=200,
            include_rts=True,
            max_id=newest_id - 1,
            # Necessary to keep full_text
            # otherwise only the first 140 words are extracted
            tweet_mode='extended'
        )
        if len(tweets) == 0:
            break
        newest_id = tweets[-1].id
        all_tweets.extend(tweets)
        print('N of tweets downloaded till now {}'.format(len(all_tweets)))

    # ARCHIVE TWEETS JSON

    with codecs.open('all_tweets.json', 'w', encoding='utf-8') as f:
        json.dump([tweet._json for tweet in all_tweets], f, ensure_ascii=False)

    # DOWNLOAD IMAGES


    for tweet in all_tweets:
        if 'media' in tweet.entities:
            for image in tweet.entities['media']:
                print(image)
                filename = images_dir + "/" + image['media_url'].split('/')[-1]
                try:
                    download_file(image['media_url'], filename)
                except:
                    print(colored(f"Could not download {filename}."))

    # DOWNLOAD VIDEOS

    filename_patt = re.compile(r'[^/]+\.(mp4|webm|avi)+')
    for tweet in all_tweets:
        if hasattr(tweet, 'extended_entities') and 'media' in tweet.extended_entities and tweet.extended_entities['media'][0]['type'] == 'video':
            # print(tweet.extended_entities['media'][0]['video_info']['variants'])
            # get the highest quality video
            max_bitrate = 0
            max_bitrate_url = None
            for variant in tweet.extended_entities['media'][0]['video_info']['variants']:
                if variant['content_type'] != 'video/mp4':
                    continue
                if (max_bitrate < variant['bitrate']):
                    max_bitrate = variant['bitrate']
                    max_bitrate_url = variant['url']
            if max_bitrate_url is not None:
                filename = filename_patt.search(max_bitrate_url).group(0)
                print(f"At bitrate {max_bitrate} as {filename} in tweet {tweet.id},")
                try:
                    download_file(max_bitrate_url, f"{videos_dir}/{filename}")
                except:
                    print(colored(f"Could not download {filename}."))

api = auth(use_proxy=False)

for user in sys.argv[1:]:
    archive_user(user, api)

