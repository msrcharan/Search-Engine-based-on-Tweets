

consumer_key = ""  #same as api key
consumer_secret = ""  #same as api secret
access_key = ""
access_secret = ""


import tweepy

from requests_oauthlib import OAuth1
import json
import requests
from collections import Counter
import sys
import re
import pandas as pd
import csv
import string

BEARER_TOKEN = ''

CACHE_FILENAME = '/content/drive/MyDrive/tweets_cache_tweet.json'
AUTHOR_PATH = '/content/drive/'

def load_authors(new=False):
    if AUTHOR_PATH and new==False:
        print('Loading created author file')
    elif not AUTHOR_PATH or new==True:
        print('Creating new author file')
        with open(AUTHOR_PATH, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(
                ['author_handle', 'author_id', 'author_bio', 'author_name', 'following_count','follower_count'])
    authors = pd.read_csv(AUTHOR_PATH)
    return authors

def open_cache():
    try:
        cache_file = open(CACHE_FILENAME, 'r')
        cache_contents = cache_file.read()
        cache_dict = json.loads(cache_contents)
        cache_file.close()
    except:
        cache_dict = {}
    return cache_dict

def save_cache(cache_dict):
    dumped_json_cache = json.dumps(cache_dict)
    fw = open(CACHE_FILENAME,"w")
    fw.write(dumped_json_cache)
    fw.close()

def create_stream_url():
    return "https://api.twitter.com/2/tweets/sample/stream?tweet.fields=lang&expansions=author_id&user.fields=description,name,public_metrics"

def bearer_oauth(r):
    r.headers["Authorization"] = f"Bearer {BEARER_TOKEN}"
    r.headers["User-Agent"] = "v2SampledStreamPython"
    return r

def connect_to_endpoint(url, n_users): 
    response = requests.request("GET", url, auth=bearer_oauth, stream=True)
    output_file = open(AUTHOR_PATH, 'a')
    writer = csv.writer(output_file)
    
    count = 0
    for response_line in response.iter_lines():
        if count >= n_users:
            output_file.close()
            sys.exit('Got all users')
        if response_line:
            print("yes, response line")
            json_response = json.loads(response_line)
            if json_response['data']['lang'] == 'en' and not json_response['data']['text'].startswith(('RT', '@')):
                author_handle = json_response['includes']['users'][0]['username']
                author_desc = json_response['includes']['users'][0]['description']
                author_name = json_response['includes']['users'][0]['name']
                author_tweet_count = json_response['includes']['users'][0]['public_metrics']['tweet_count']
                followers = json_response['includes']['users'][0]['public_metrics']['followers_count']
                following = json_response['includes']['users'][0]['public_metrics']['following_count']
                author_id = json_response['data']['author_id']
                #['author_handle', 'author_id', 'author_bio', 'author_name', 'following_count','follower_count']
                writer.writerow([author_handle, author_id, author_desc, author_name, followers, following])
                count += 1  
    return None

def run_stream(n_users):
    url = create_stream_url()
    timeout = 0
    while True:
        connect_to_endpoint(url, n_users=n_users)
        timeout += 1

def create_user_url(user_id, max_results):
    tweet_fields = "tweet.fields=lang,text,referenced_tweets,public_metrics,in_reply_to_user_id,author_id,entities"
    max_results = "max_results={}".format(max_results)
    return "https://api.twitter.com/2/users/{}/tweets?&{}&{}".format(user_id,tweet_fields, max_results)

def get_user_tweets(author_id):
    filtered_tweets = []
    author_url = create_user_url(user_id=author_id, max_results=50)
    response = requests.get(author_url, auth=bearer_oauth)
    resp_json = json.loads(response.text)
    try:
        user_tweet_data = resp_json['data']
    except:
        return filtered_tweets

    return user_tweet_data

def create_user_bio_url(user_id):
    user_fields = "user.fields=description,public_metrics"
    return "https://api.twitter.com/2/users?ids={}&{}".format(user_id, user_fields)
                                                                       
    
def get_user_bio(author_id):
    bios = []
    author_bio_url = create_user_bio_url(user_id=author_id)
    response = requests.get(author_bio_url, auth=bearer_oauth)
    resp_json = json.loads(response.text)
    try:
        user_bio_data = resp_json['data'][0]
    except:
        return bios

    return user_bio_data  

def clean_all_tweets(tweet_cache):
    clean_tweets_all = []
    for user_tweets in tweet_cache.values():
        for sample_tweet in user_tweets:
            clean_tweet_dict = {}
            try:
                if sample_tweet['lang'] == 'en':
                    if 'referenced_tweets' not in sample_tweet.keys():
                        #remove links
                        clean_text = re.sub(r'https?:\/\/\S*', "", sample_tweet['text']).strip()
                        #remove punctuation
                        clean_text = clean_text.translate(str.maketrans('', '', string.punctuation))
                        #remove one-word or one-character tweets
                        if len(clean_text.split()) > 1:      
                            clean_tweet_dict['text'] = clean_text
                            clean_tweet_dict['author_id'] = sample_tweet['author_id']
                            clean_tweets_all.append(clean_tweet_dict)
            except:
                continue
    return clean_tweets_all

all_author_df = load_authors(new=False)
tweet_cache = open_cache()

all_author_df = all_author_df[~all_author_df.duplicated()]
all_author_df['author_id'] = all_author_df['author_id'].astype(str)
all_authors = list(all_author_df['author_id'])
print(f"Loaded data for {len(all_author_df)} authors")
new_authors = [str(author) for author in all_authors if str(author) not in tweet_cache.keys()]
print(f"Found {len(new_authors)} new authors in df")

#Get tweets for authors we don't have tweets for yet
if len(new_authors) > 0:
    for new_author_id in new_authors:
        author_tweets = get_user_tweets(author_id=new_author_id)
        tweet_cache[new_author_id] = author_tweets

save_cache(tweet_cache)

clean_tweets_all = clean_all_tweets(tweet_cache=tweet_cache)
print(clean_tweets_all)
# tweet_df = pd.DataFrame(clean_tweets_all)
# tweet_df_clean = tweet_df.drop_duplicates(keep="first")
# authors_with_tweets = tweet_df_clean['author_id'].unique()

# author_df_filtered = all_author_df[all_author_df['author_id'].isin(authors_with_tweets)]
# author_df_filtered = author_df_filtered.reset_index(drop=True).drop('Unnamed: 0', axis=1)

def update_author_info(dataset):
    id = []
    name = []
    followers = []
    following = []
    count = 1
    count_a = 0
    count_b = 100

    for i in range(0,len(dataset)+1):
        ids = dataset['author_id'][count_a:count_b]
        converted_list = [str(element) for element in ids]
        joined_string = ",".join(converted_list)

        author_bio_url = create_user_bio_url(joined_string)
        response = requests.get(author_bio_url, auth=bearer_oauth)
        resp_json = json.loads(response.text)
        count += 1

        for j in range(0, len(resp_json['data'])):
            id.append(resp_json['data'][j]['id'])
            name.append(resp_json['data'][j]['name'])
            followers.append(resp_json['data'][j]['public_metrics']['followers_count'])
            following.append(resp_json['data'][j]['public_metrics']['following_count'])


        if count_b > len(dataset):
            break
        elif count >= 1:
            count_a += 100
            count_b += 100
        else:
            count_a = count_a
            count_b = count_b

    res = pd.DataFrame(
      {
        'author_id': id,
        'author_name': name,
        'followers_count': followers,
        'following_count': following
      }
    )

    return res

author_df_updated = update_author_info(author_df_filtered)

author_df_new = x.merge(author_df_filtered[['author_id', 'author_bio', 'handle']], on="author_id")
author_df_new = author_df_new[['handle', 'author_id', 'author_bio', 'author_name', 'following_count', 'followers_count']]
author_df_new.columns = ['author_handle', 'author_id', 'author_bio', 'author_name', 'following_count','follower_count']
tweet_df_new = tweet_df_clean[tweet_df_clean['author_id'].isin(list(author_df_new['author_id']))]

tweet_df_new.to_csv(data_path + '../all_tweets_updated.csv', index=True)
author_df_new.to_csv(data_path + '../all_author_df.csv', index=True)

date_tweets = tweepy.Cursor(api.search, since="2020-5-31", tweet_mode='extended').items(5)

for i in date_tweets:
  print(i)


# Method-II
import tweepy
import os
import json
import sys

consumer_key = ""  #same as api key
consumer_secret = ""  #same as api secret
access_key = ""
access_secret = ""


# API Keys and Tokens

access_token = ""
access_token_secret = ""

# Authorization and Authentication
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, access_token_secret)
api = tweepy.API(auth)

if __name__ == "__main__":
    # Available Locations
    #available_loc = api.trends_available()
    woeid= 23424848 #india
    available_loc2= api.trends_place(woeid)
    # writing a JSON file that has the available trends around the world
    with open("available_locs_for_trend2.json","w") as wp:
        wp.write(json.dumps(available_loc2, indent=1))

import json
name=[]
query=[]
with open('/content/available_locs_for_trend2.json') as f:
    data = json.load(f)
    # data = json.loads


for p_id in data:
    u_name = p_id.get('name')
    name.append(u_name)
    u_qry = p_id.get('query')
    query.append(u_qry)

search_words = "#"      #enter your words
new_search = search_words + " -filter:retweets"

from tweepy import *
import csv
import pandas as pd
import csv
import re 
import string
# import preprocessor as p

# Method - III
consumer_key = ""  #same as api key
consumer_secret = ""  #same as api secret
access_key = ""
access_secret = ""

auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_key, access_secret)
api = tweepy.API(auth,wait_on_rate_limit=True)

api = tweepy.API(auth)
csvFile = open('/content/tweets.csv', 'a')
csvWriter = csv.writer(csvFile)

limit=200
for i in name:
  search_words = i     #enter your words
  new_search = search_words + " -filter:retweets"

  for tweet in tweepy.Cursor(api.search,q=new_search,count=100,
                            lang="en",
                            since_id=0).items(limit):
      csvWriter.writerow([tweet.created_at, tweet.text.encode('utf-8'),tweet.user.screen_name.encode('utf-8'), tweet.user.location.encode('utf-8')])

csvFile = open('file-name', 'a')
csvWriter = csv.writer(csvFile)

def clean_all_tweets(tweet_cache):
    clean_tweets_all = []
    for user_tweets in tweet_cache.values():
        for sample_tweet in user_tweets:
            clean_tweet_dict = {}
            try:
                if sample_tweet['lang'] == 'en':
                    if 'referenced_tweets' not in sample_tweet.keys():
                        #remove links
                        clean_text = re.sub(r'https?:\/\/\S*', "", sample_tweet['text']).strip()
                        #remove punctuation
                        clean_text = clean_text.translate(str.maketrans('', '', string.punctuation))
                        #remove one-word or one-character tweets
                        if len(clean_text.split()) > 1:      
                            clean_tweet_dict['text'] = clean_text
                            clean_tweet_dict['author_id'] = sample_tweet['author_id']
                            clean_tweets_all.append(clean_tweet_dict)
            except:
                continue
    return clean_tweets_all

import pandas as pd
l=[]
tweets=pd.read_csv("/content/final.csv")
for i in tweets.iloc[:,1]:
  try:
    
    j=i
    j=j[1:]
    l.append(j)
  except:
    l.append(i)

import re
import numpy as np

new_l=[]
for _ in l:
    try:
      _= _.strip()
      #_ = re.sub("@","", _) #Removing hashtags and mentions
      #_ = re.sub("#","", _)
      _ = re.sub("http\S+", "", _) #Removing links
      _ = re.sub("www.\S+", "", _)
      #_ = re.sub('[()!?\n]', ' ', _)
      #_ = re.sub('\[.*?\]',' ', _) #Removing punctuations
      #_ = re.sub("[^a-z0-9]"," ", _) #Filtering non-alphanumeric characters
      new_l.append(_)
    except:
      continue

users=[]
for i in tweets.iloc[:,2]:
  try:
    
    j=i
    j=j[1:]
    users.append(j)
  except:
    users.append(i)
# print((tweets.iloc[:,2]))

df = pd.DataFrame(list(zip(new_l, users)),
               columns =['Tweet', 'User'])
df.head()

df.to_csv('cleaned.csv')

def clean_all_tweets(tweet_cache):
    clean_tweets_all = []
    for sample_tweet in tweet_cache:
        clean_tweet_dict = {}
        try:
            if sample_tweet['lang'] == 'en':
                if 'referenced_tweets' not in sample_tweet.keys():
                        #remove links
                    clean_text = re.sub(r'https?:\/\/\S*', "", sample_tweet['text']).strip()
                        #remove punctuation
                    clean_text = clean_text.translate(str.maketrans('', '', string.punctuation))
                        #remove one-word or one-character tweets
                    if len(clean_text.split()) > 1:      
                        clean_tweet_dict['text'] = clean_text
                        clean_tweet_dict['author_id'] = sample_tweet['author_id']
                        clean_tweets_all.append(clean_tweet_dict)
        except:
              continue
    return clean_tweets_all

for i in l:
  print(i)

# import re,string

# def strip_links(text):
#     link_regex = re.compile('((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)', re.DOTALL)
#     links = re.findall(link_regex, text)
#     for link in links:
#         text = text.replace(link[0], ', ')   
#     return text

# def strip_all_entities(text):
#     entity_prefixes = ['@','#']
#     for separator in  string.punctuation:
#         if separator not in entity_prefixes :
#             text = text.replace(separator,' ')
#     words = []
#     for word in text.split():
#         word = word.strip()
#         if word:
#             if word[0] not in entity_prefixes:
#                 words.append(word)
#     return ' '.join(words)

# for t in l:
#     strip_all_entities(strip_links(l))

import pandas as pd

tf= pd.read_csv("/content/drive/MyDrive/JAVA_Gowtham/cleaned.csv")
tf.head()

import csv  
# Open file 

with open('/content/drive/MyDrive/JAVA_Gowtham/cleaned.csv') as file_obj:
      
    # Create reader object by passing the file 
    # object to reader method
    reader_obj = csv.reader(file_obj)
    l=[]
    # Iterate over each row in the csv 
    # file using reader object
    for row in reader_obj:
        l.append(row)
# print(l[0])

for i in range(1,len(l)):
  name = '/content/drive/MyDrive/tweet_files/' + l[i][0] + '.txt'
  line1 = l[i][1]
  li="\n"
  line2= l[i][2]
  f1 = open(name, 'w')
  f1.write(line1)
  f1.write(li)
  f1.write(line2)
  f1.close()

import os

dir_path = "/content/drive/MyDrive/tweet_files"
print(len([entry for entry in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, entry))]))

import os
import sys
import re
import nltk
import operator
import pickle as pkl
# import progressbar
import time
import numpy as np
import pandas as pd

def tokenizer(text):
    text = re.sub("[^a-zA-Z]+", " ", text)
    tokens = nltk.tokenize.word_tokenize(text)
    return tokens        

def preprocessing_txt(text):
    
    tokens = tokenizer(text)
    stemmer = nltk.stem.porter.PorterStemmer()
    stopwords = nltk.corpus.stopwords.words('english')
    new_text = ""
    for token in tokens:
        token = token.lower()
        if token not in stopwords:
#             print token
            new_text += stemmer.stem(token)
            new_text += " "
        
    return new_text