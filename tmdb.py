
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


def movieList(movieIds, source='https://api.themoviedb.org/3/movie/top_rated', maxMovies=1000000):
    url = source
    numPages = maxMovies / 20
    for page in range(1, int(numPages + 1)): #A
        try:
            print("GET IDS")
            httpResp = tmdb_api.get(url, params={'page': page})  #B
            if int(httpResp.headers['x-ratelimit-remaining']) < 10:
                print("  (IDs) Sleeping due to rate limit, On %s/%s (%s remaining API TMDB requests allowed)" % \
                    (page, numPages, httpResp.headers['x-ratelimit-remaining']))
                time.sleep(TMDB_SLEEP_TIME_SECS)
        except Exception as e:
            print(e)
            print(len(movieIds))
        jsonResponse = json.loads(httpResp.text) #C
        if 'results' not in jsonResponse:
            print("Got weird response, assuming done")
            print("Status %s" % httpResp.status_code)
            print(json.dumps(jsonResponse, indent=2))
            return movieIds
        movies = jsonResponse['results']
        for movie in movies: #D
            movieIds.append(str(movie['id']))
    return movieIds

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

def extract(startChunk=0, movieIds=[], chunkSize=5000):
    movieDict = {}
    missing = 0
    for idx, movieId in enumerate(movieIds):
        if movieId < (startChunk * chunkSize):
            continue
        try:
            httpResp = tmdb_api.get("https://api.themoviedb.org/3/movie/%s" % movieId)
            if httpResp.status_code == 429:
                print(httpResp.text)
                raise TaintedDataException
            if httpResp.status_code <= 300:
                movie = json.loads(httpResp.text)
                getCastAndCrew(movieId, movie)
                movieDict[str(movieId)] = movie
            elif httpResp.status_code == 404:
                missing += 1
            else:
                print("Error %s for %s" % (httpResp.status_code, movieId))
            if int(httpResp.headers['x-ratelimit-remaining']) < 10:
                print(" (EXTR) Sleeping due to rate limit, On %s/%s (missing %s) (%s remaining API TMDB requests allowed)" % \
                    (idx, len(movieIds), missing, httpResp.headers['x-ratelimit-remaining']))
                time.sleep(TMDB_SLEEP_TIME_SECS)
        except ConnectionError as e:
            print(e)

        if (movieId % chunkSize == (chunkSize - 1)):
            print("DONE CHUNK, LAST ID CHECKED %s" % movieId)
            yield movieDict
            movieDict = {}
            missing = 0
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




def getIds(rebuild=False):
    existingIds = []

    print("Already know-about movies")
    try:
        with open('ids.json') as f:
            existingIds = json.load(f)['ids']

        with open('tmdb.json') as f:
            tmdbIds = list(json.load(f).keys())

            existingIds = list(set(tmdbIds + existingIds))

        if not rebuild:
            print("Using %s cached ids" % len(existingIds))
            return existingIds
        print("Rebuild=True, thus adding new movies...")
    except IOError:
        print("No existing ids.json and tmdb.json found, rebuilding")
    print("Got %s movies" % len(existingIds))

    print("Popular movies...")
    movieIds = movieList(movieIds=existingIds, source='https://api.themoviedb.org/3/movie/popular')
    existingIds = list(set(movieIds + existingIds))
    print("Got %s movies" % len(existingIds))

    print("Now playing movies...")
    movieIds = movieList(movieIds=existingIds, source='https://api.themoviedb.org/3/movie/now_playing')
    existingIds = list(set(movieIds + existingIds))
    print("Got %s movies" % len(existingIds))


    print("Top-rated movies...")
    movieIds = movieList(movieIds=existingIds)
    f = open('tmdb_movieIds_29apr2018.json', 'w')
    existingIds = list(set(movieIds + existingIds))
    print("Got %s movies" % len(existingIds))


    print("Writing %s ids" % len(existingIds))

    print("Got All Movie Ids")
    f = open('ids.json', 'w')
    f.write(json.dumps({"ids": existingIds}))

    return existingIds


def continueChunks(lastId):
    # movieIds = getIds(rebuild=False)
    allTmdb = {}
    atChunk = 0
    for i in range(0, int(lastId / CHUNK_SIZE) + 1):
        try:
            with open("chunks/tmdb.%s.json" % i) as f:
                movies = json.load(f)
                allTmdb = {**movies, **allTmdb}
        except IOError:
            print("Starting at chunk %s; total %s" % (i, int(lastId/CHUNK_SIZE)))
            atChunk = i
            break

    for idx, movieDict in enumerate(extract(startChunk=atChunk, chunkSize=CHUNK_SIZE, movieIds=range(lastId))):
        currChunk = idx + atChunk
        with open("chunks/tmdb.%s.json" % currChunk, 'w') as f:
            print("WRITING Chunk %s" % currChunk)
            f.write(json.dumps(movieDict))
    return True



if __name__ == "__main__":
    lastId = lastMovieId()
    while True:
        try:
            if (continueChunks(lastId=lastId)):
                print("YOU HAVE WON THE GAME!")
        except TaintedDataException:
            print("Chunk tainted, trying again")
            time.sleep(TMDB_SLEEP_TIME_SECS*2)
            continue
