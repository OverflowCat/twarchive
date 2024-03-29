from itertools import count
from typing import List
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
import pickledb
import time
from utils import retry

dotenv.load_dotenv()

# key: user_id_str str -> val: timestamp int
saved_db = pickledb.load('saved.db', False)
# names_db = pickledb.load('names.db', False) # key: user_id_str str -> val: screename str
print(colored(f"{saved_db.totalkeys()} users have been saved.", "magenta", "on_black", ["bold"]))

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


api = auth(use_proxy=False)


@retry(5)
def create_dir(folder_path: str):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)


@retry(3)
def download_file(url: str, filename: str) -> None:
    if os.path.exists(filename):
        print(colored(f"{filename} exists, skipping…",
              "blue", attrs=['bold']) + url)
        return

    print(colored("Downloading ", "yellow") + url)
    with open(filename, 'wb') as f:
        f.write(requests.get(url).content)


def get_following_ids_from_archive(filename: str) -> List[int]:
    with open(filename, 'r') as file:
        content = file.read()
        start_index = content.index('[')
        data = json.loads(content[start_index:])

    res = [int(d['following']['accountId']) for d in data]
    index = res.index(322420627)
    print(f"Found at index {index}.")
    sleep(5)
    return res[index:] # 从该用户之后开始，不包括该用户


def archive_user(user):
    print(colored("============================", "dark_grey"))
    if isinstance(user, int):
        v = saved_db.get(str(user))
        if v:
            print(
                colored(
                    f"User has been saved at {v}, skipped.", "blue", "on_white", ['bold'])
            )
            return

    username = str(user) if isinstance(user, int) else user
    print(
        colored("Archiving", 'green'),
        colored(username, 'green', attrs=['bold', 'blink']),
        "…"
    )

    archive_dir = "../twasl"
    create_dir(archive_dir)
    user_dir = archive_dir + '/' + username
    create_dir(user_dir)
    images_dir = f"{user_dir}/images"
    create_dir(images_dir)
    videos_dir = f"{user_dir}/videos"
    create_dir(videos_dir)

    all_tweets = []
    newest_id = 1622294944739877777
    newest_id = 1625808601414599333
    while len(all_tweets) < 114514:
        tweets = None
        try:
            if user == username:
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
            else:
                tweets = api.user_timeline(
                    user_id=user,
                    count=200,
                    include_rts=True,
                    max_id=newest_id - 1,
                    tweet_mode='extended'
                )
        except tweepy.Unauthorized as e:
            print(e)
            saved_db.set(str(user), -401)
            return
        if len(tweets) == 0:
            # print(colored('No more tweets found.', 'light_red', attrs=['bold']))
            break
        newest_id = tweets[-1].id
        all_tweets.extend(tweets)
        print('{} tweets have been downloaded…'.format(len(all_tweets)))

    # ARCHIVE TWEETS JSON

    json_path = user_dir + '/' + 'tweets.json'
    with codecs.open(json_path, 'w', encoding='utf-8') as f:
        json.dump([tweet._json for tweet in all_tweets], f, ensure_ascii=False)

    # DOWNLOAD IMAGES

    for tweet in all_tweets:
        if 'media' in tweet.entities:
            for image in tweet.entities['media']:
                filename = images_dir + "/" + image['media_url'].split('/')[-1]
                try:
                    sleep(0.5)
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
                print(
                    f"At bitrate {max_bitrate} as {filename} in tweet {tweet.id},")
                try:
                    download_file(max_bitrate_url, f"{videos_dir}/{filename}")
                except:
                    print(colored(f"Could not download {filename}."))

    # ADD SAVED USER_ID_STR TO SAVED_DB

    saved_db.set(str(user), int(time.time()))
    saved_db.dump()


def parse_args(arguments):
    if len(arguments) == 0 or arguments[0] == "following":
        user_ids = get_following_ids_from_archive('following.js')
        for user in user_ids:
            print(user)
            archive_user(user)
    else:
        for user in arguments:
            archive_user(user)


def main():
    parse_args(sys.argv[1:])


main()
