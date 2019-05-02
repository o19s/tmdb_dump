**NOTE This project is sporadically maintained by OpenSource Connections. We'll do our best to be responsive, but its largely on the back burner/here as demo code**

[TheMovieDB](http://themoviedb.org) is a Movie Database, useful for NLP, rescsys, and search experimentation. This repo crawls the TMDB API following the TMDB API rules, and places them into local gzipped JSON files so you can go forth and experiment with movie data.

# Dependencies

- Python 3
- [Requests library](https://2.python-requests.org//en/master/)

# To Run

```
export TMDB_API_KEY=<get an API key from TMDB>
python tmdb.py
```

This script will crawl TMDB from 0 to the latest movie added to TMDB. Every 1000 movies will be dumped to the `chunks/` folder in gzipped form. 
