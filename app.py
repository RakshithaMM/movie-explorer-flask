from flask import Flask, render_template, request, redirect, session
import requests
import sqlite3
import os
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = "movie_secret"

load_dotenv()
API_KEY = os.getenv("TMDB_KEY")



# ---------- DATABASE ----------

def get_db():
    conn = sqlite3.connect("watchlist.db")
    conn.row_factory = sqlite3.Row
    return conn


def create_table():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS fav(
            id TEXT,
            title TEXT,
            poster TEXT,
            rating TEXT,
            year TEXT,
            user TEXT
        )
    """)

    conn.commit()
    conn.close()

create_table()


# ---------- HOME ----------

@app.route("/")
def index():

    url = "https://api.themoviedb.org/3/trending/movie/day"

    r = requests.get(url, params={"api_key": API_KEY})
    data = r.json()

    movies = []

    for m in data.get("results", []):

        poster = ""
        if m.get("poster_path"):
            poster = "https://image.tmdb.org/t/p/w500" + m["poster_path"]

        movies.append({
            "id": m.get("id"),
            "title": m.get("title"),
            "year": m.get("release_date","")[:4],
            "rating": m.get("vote_average"),
            "overview": m.get("overview"),
            "poster": poster
        })

    return render_template("index.html", movies=movies)


# ---------- SEARCH ----------

@app.route("/search", methods=["POST"])
def search():

    name = request.form["name"]

    url = "https://api.themoviedb.org/3/search/movie"

    r = requests.get(url, params={
        "api_key": API_KEY,
        "query": name
    })

    data = r.json()

    movies = []

    for m in data.get("results", []):

        poster = ""
        if m.get("poster_path"):
            poster = "https://image.tmdb.org/t/p/w500" + m["poster_path"]

        movies.append({
            "id": m.get("id"),
            "title": m.get("title"),
            "year": m.get("release_date","")[:4],
            "rating": m.get("vote_average"),
            "overview": m.get("overview"),
            "poster": poster
        })

    return render_template("index.html", movies=movies)


# ---------- DETAIL ----------

@app.route("/movie/<id>")
def movie_detail(id):

    m = requests.get(
        f"https://api.themoviedb.org/3/movie/{id}",
        params={"api_key": API_KEY}
    ).json()

    cast_data = requests.get(
        f"https://api.themoviedb.org/3/movie/{id}/credits",
        params={"api_key": API_KEY}
    ).json()

    video_data = requests.get(
        f"https://api.themoviedb.org/3/movie/{id}/videos",
        params={"api_key": API_KEY}
    ).json()

    cast = []
    for c in cast_data.get("cast", [])[:6]:
        img = ""
        if c.get("profile_path"):
            img = "https://image.tmdb.org/t/p/w200" + c["profile_path"]

        cast.append({
            "name": c.get("name"),
            "character": c.get("character"),
            "image": img
        })

    trailer = ""
    for v in video_data.get("results", []):
        if v.get("type") == "Trailer":
            trailer = "https://www.youtube.com/watch?v=" + v["key"]
            break

    poster = ""
    if m.get("poster_path"):
        poster = "https://image.tmdb.org/t/p/w500" + m["poster_path"]

    movie = {
        "title": m.get("title"),
        "rating": m.get("vote_average"),
        "year": m.get("release_date","")[:4],
        "overview": m.get("overview"),
        "poster": poster,
        "runtime": m.get("runtime"),
        "cast": cast,
        "trailer": trailer
    }

    return render_template("detail.html", movie=movie)


# ---------- AUTH ----------

@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        u = request.form["username"]
        p = request.form["password"]

        conn = get_db()
        conn.execute(
            "INSERT INTO users(username,password) VALUES(?,?)",(u,p)
        )
        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        u = request.form["username"]
        p = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (u,p)
        ).fetchone()

        conn.close()

        if user:
            session["user"] = u
            return redirect("/")
        else:
            return "Invalid Login"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# ---------- WATCHLIST ----------

@app.route("/addfav", methods=["POST"])
def addfav():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()

    conn.execute(
      "INSERT INTO fav VALUES(?,?,?,?,?,?)",
      (
        request.form["id"],
        request.form["title"],
        request.form["poster"],
        request.form["rating"],
        request.form["year"],
        session["user"]
      )
    )

    conn.commit()
    conn.close()

    return redirect("/watchlist")


@app.route("/watchlist")
def watchlist():

    if "user" not in session:
        return redirect("/login")

    conn = get_db()
    movies = conn.execute(
        "SELECT * FROM fav WHERE user=?",
        (session["user"],)
    ).fetchall()

    conn.close()

    return render_template("watchlist.html", movies=movies)


@app.route("/remove/<id>")
def remove(id):

    conn = get_db()
    conn.execute("DELETE FROM fav WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/watchlist")


if __name__ == "__main__":
    app.run(debug=True)
