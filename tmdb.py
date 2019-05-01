import gzip
import requests
import json
import os
import time
from requests.exceptions import ConnectionError

# you'll need to have an API key for TMDB
# to run these examples,
# run export TMDB_API_KEY=<YourAPIKey>
tmdb_api_key = os.environ["TMDB_API_KEY"]
# Setup tmdb as its own session, caching requests
# (we only want to cache tmdb, not elasticsearch)
# Get your TMDB API key from
#  https://www.themoviedb.org/documentation/api
# then in shell do export TMDB_API_KEY=<Your Key>
tmdb_api = requests.Session()
tmdb_api.params={'api_key': tmdb_api_key}

TMDB_SLEEP_TIME_SECS=1
CHUNK_SIZE=1000

class TaintedDataException(RuntimeError):
    pass


def getCastAndCrew(movieId, movie):
    httpResp = tmdb_api.get("https://api.themoviedb.org/3/movie/%s/credits" % movieId)
    if int(httpResp.headers['x-ratelimit-remaining']) < 10:
        print(" (CAST) Sleeping due to rate limit, (%s remaining API TMDB requests allowed)" % \
            (httpResp.headers['x-ratelimit-remaining']))
        time.sleep(TMDB_SLEEP_TIME_SECS)
    credits = json.loads(httpResp.text) #C
    try:
        crew = credits['crew']
        directors = []
        for crewMember in crew: #D
            if crewMember['job'] == 'Director':
                directors.append(crewMember)
    except KeyError as e:
        print(e)
        print(credits)
    movie['cast'] = credits['cast']
    movie['directors'] = directors

def extract(startChunk=0, movieIds=[], chunkSize=5000, existing_movies={}):
    movieDict = {}
    missing = 0
    local = 0
    fetched = 0
    for idx, movieId in enumerate(movieIds):
        # Read ahead to the current chunk
        if movieId < (startChunk * chunkSize):
            continue

        # Try an existing tmdb.json
        if str(movieId) in existing_movies:
            movieDict[str(movieId)] = existing_movies[str(movieId)]
            local += 1
        else: # Go to the API
            try:
                httpResp = tmdb_api.get("https://api.themoviedb.org/3/movie/%s" % movieId)
                if httpResp.status_code == 429:
                    print(httpResp.text)
                    raise TaintedDataException
                if httpResp.status_code <= 300:
                    movie = json.loads(httpResp.text)
                    getCastAndCrew(movieId, movie)
                    movieDict[str(movieId)] = movie
                    fetched += 1
                elif httpResp.status_code == 404:
                    missing += 1
                else:
                    print("Error %s for %s" % (httpResp.status_code, movieId))
                if int(httpResp.headers['x-ratelimit-remaining']) < 10:
                    print(" (EXTR) Sleeping due to rate limit, On %s/%s (missing %s / local %s / fetched %s) (%s remaining API TMDB requests allowed)" % \
                        (idx, len(movieIds), missing, local, fetched, httpResp.headers['x-ratelimit-remaining']))
                    time.sleep(TMDB_SLEEP_TIME_SECS)
            except ConnectionError as e:
                print(e)

        if (movieId % chunkSize == (chunkSize - 1)):
            print("DONE CHUNK, LAST ID CHECKED %s" % movieId)
            yield movieDict
            movieDict = {}
            missing = 0
            local = 0
            fetched = 0
    yield movieDict


def lastMovieId(url='https://api.themoviedb.org/3/movie/latest'):
    try:
        print("GET ID")
        httpResp = tmdb_api.get(url)
    except Exception as e:
        print(e)
    jsonResponse = json.loads(httpResp.text)
    print("Latest movie is %s (%s)" % (jsonResponse['id'], jsonResponse['title']))
    return int(jsonResponse['id'])

def read_chunk(chunk_id):
    with gzip.GzipFile('chunks/tmdb.%s.json.gz' % chunk_id) as f:
        return json.loads(f.read().decode('utf-8'))

def write_chunk(chunk_id, movie_dict):
    with gzip.GzipFile('chunks/tmdb.%s.json.gz' % chunk_id, 'w') as f:
        f.write(json.dumps(movie_dict).encode('utf-8'))

def continueChunks(lastId):
    allTmdb = {}
    existing_movies = {}
    atChunk = 0
    try:
        with open('tmdb.json') as f:
            print("Using Existing tmdb.json")
            existing_movies = json.load(f)
    except FileNotFoundError:
        pass
    for i in range(0, int(lastId / CHUNK_SIZE) + 1):
        try:
            movies = read_chunk(i)
            allTmdb = {**movies, **allTmdb}
        except IOError:
            print("Starting at chunk %s; total %s" % (i, int(lastId/CHUNK_SIZE)))
            atChunk = i
            break

    for idx, movieDict in enumerate(extract(startChunk=atChunk, existing_movies=existing_movies,
                                            chunkSize=CHUNK_SIZE, movieIds=range(lastId))):
        currChunk = idx + atChunk
        write_chunk(currChunk, movieDict)
    return True


def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


if __name__ == "__main__":
    ensure_dir('chunks/')
    lastId = lastMovieId()
    while True:
        try:
            if (continueChunks(lastId=lastId)):
                print("YOU HAVE WON THE GAME!")
        except TaintedDataException:
            print("Chunk tainted, trying again")
            time.sleep(TMDB_SLEEP_TIME_SECS*2)
            continue
