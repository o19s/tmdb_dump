import glob
import json
import gzip

from datetime import date

# this script requires the results of `tmdb.py`
# it shrinks the results to a reasonable size for TLRE demos (~50,000),
# by removing movies that:
#   are "Adult",
#   runtime is less than 1 hr,
#   don't have a poster,
#   don't have any votes

def scrub_chunks():
    """Collate a list of chunk paths into a single dictionary

    Keyword arguments:
    files -- list of paths to g-zipped chunks from `tmdb.py`
    """
    files = glob.glob('chunks/*')
    if len(files) == 0 :
        raise SystemExit("No chunks found in `chunks/`. Did you run `tmdb.py` already?")

    keep = dict()

    for f in files:
        with gzip.open(f, "r") as zip_ref:
            movies = json.load(zip_ref)
            for m in movies.keys():
                dat = movies[m]
                if ( not dat["adult"] and
                    dat["vote_count"] > 0 and
                    dat["poster_path"] is not None and
                    dat["runtime"] is not None and
                    dat["runtime"] > 59
                    ):
                    k = dat["id"]
                    keep.update({k : dat})
    return keep

if __name__ == "__main__":
    keep = scrub_chunks()
    filename = "tmdb_" + str(date.today()) + ".json"
    with open(filename, "w") as f:
        json.dump(keep, f)
