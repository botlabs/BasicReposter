import praw
import requests
import time

# Account settings (private)
USERNAME = ''
PASSWORD = ''

# OAuth settings (private)
CLIENT_ID = ''
CLIENT_SECRET = ''
REDIRECT_URI = 'http://127.0.0.1:65010/authorize_callback'
# Configuration Settings
USER_AGENT = "Reposter | /u/YOUR_MAIN_ACCOUNT_HERE"
AUTH_TOKENS = ["identity","read", "submit"]
EXPIRY_BUFFER = 60

SRC_SUBREDDIT  = "SET_ME"
DEST_SUBREDDIT = "SET_ME"
KARMA_THRESHOLD = 500
COMMENT_THRESHOLD = 100
POSTED_LOG = "posted.log"

wordsets = [
#["must", "have", "these", "together"],
#["but"],
#["can"],
#["have"],
#["these"],
#["alone"],
["update", "husband", "notice"],
[] # No comma on last entry
]

T_SUBMISSION_HEADER = "[SOURCE={0}]:#\n\n"

def get_session_data():
    response = requests.post("https://www.reddit.com/api/v1/access_token",
      auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET),
      data = {"grant_type": "password", "username": USERNAME, "password": PASSWORD},
      headers = {"User-Agent": USER_AGENT})
    response_dict = dict(response.json())
    response_dict['retrieved_at'] = time.time()
    return response_dict

def get_praw():
    r = praw.Reddit(USER_AGENT)
    r.set_oauth_app_info(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
    session_data = get_session_data()
    r.set_access_credentials(set(AUTH_TOKENS), session_data['access_token'])
    return (r, session_data)

def already_reposted(r, post):
    for d_post in r.get_subreddit(DEST_SUBREDDIT).get_new(limit=None):
        with open(POSTED_LOG, "w+") as f:
            if d_post.is_self \
            and post.id not in [l for l in f.read().split("\n") if l is not ""] \
            and T_SUBMISSION_HEADER.format(post.id) in d_post.selftext:
                return True

def mark_posted(post):
    with open(POSTED_LOG, "a") as f:
        f.write(post.id + "\n")

def main(r, session_data):
    EXPIRES_AT = session_data['retrieved_at'] + session_data['expires_in']
    while True:
        if time.time() >= EXPIRES_AT - EXPIRY_BUFFER:
            raise praw.errors.OAuthInvalidToken
        ##### MAIN CODE #####
        for post in r.get_subreddit(SRC_SUBREDDIT).get_hot(limit=None):
            if post.is_self \
            and not already_reposted(r, post) \
            and any(all(word.lower() in (post.title + post.selftext).lower() for word in wordset) for wordset in wordsets) \
            and post.score >= KARMA_THRESHOLD \
            and len(list(post.comments)) >= COMMENT_THRESHOLD:
                r.submit(DEST_SUBREDDIT, post.title, text=(T_SUBMISSION_HEADER.format(post.id) + post.selftext))
                mark_posted(post)
        time.sleep(30)
                    

if __name__ == "__main__":
    while True:
        try:
            print("Retrieving new OAuth token...")
            main(*get_praw())
        except praw.errors.OAuthInvalidToken:
            print("OAuth token expired.")
        except praw.errors.HTTPException:
            print("HTTP error. Retrying in 10...")
            time.sleep(10)
