from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField
from wtforms.validators import DataRequired
import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# API parameters - loaded from environment variables
API_KEY = os.environ.get('MOVIE_DB_API_KEY')
API_BASE_URL = os.environ.get('MOVIE_DB_BASE_URL', 'https://api.themoviedb.org/3/search/')
MOVIE_DB_IMAGE_URL = os.environ.get('MOVIE_DB_IMAGE_URL', 'https://image.tmdb.org/t/p/w500')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY')
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL', 'sqlite:///movies-collection.db')

# Create the db object using the SQLAlchemy constructor
class Base(DeclarativeBase):
    pass

# Initialize extensions
bootstrap = Bootstrap5(app)
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# Database Models
class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)
    review: Mapped[str] = mapped_column(String(500), nullable=True, default="")
    img_url: Mapped[str] = mapped_column(String(200), nullable=False)

# Forms
class Edit(FlaskForm):
    rating = FloatField('Your rating (up to 10, e.g., 6.8):', validators=[DataRequired()])
    review = StringField('Your review:', validators=[DataRequired()])
    sub = SubmitField('Done')

class Add(FlaskForm):
    movie_title = StringField('Movie Title:', validators=[DataRequired()])
    sub = SubmitField('Add Movie')

# Routes
@app.route("/")
def home():
    result = db.session.execute(db.select(Movie).order_by(Movie.rating))
    all_movies = result.scalars().all()
    for i in range(len(all_movies)):
        all_movies[i].ranking = len(all_movies) - i
    db.session.commit()
    return render_template("index.html", movies=all_movies)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def editMovie(id):
    form = Edit()
    movie_edit = Movie.query.get_or_404(id)
    if form.validate_on_submit():
        movie_edit.rating = form.rating.data
        movie_edit.review = form.review.data
        db.session.commit()
        return redirect(url_for('home'))
    return render_template('edit.html', form=form, movie=movie_edit)

@app.route('/<int:id>', methods=['GET', 'POST'])
def deleteMovie(id):
    movie_to_delete = Movie.query.get_or_404(id)
    db.session.delete(movie_to_delete)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/add', methods=['GET', 'POST'])
def add_movies():
    form = Add()
    if form.validate_on_submit():
        response = requests.get(
            f'{API_BASE_URL}movie',
            params={
                'query': form.movie_title.data,
                'api_key': API_KEY
            }
        )
        response.raise_for_status()
        return render_template('select.html', movie_list=response.json()['results'])
    return render_template('add.html', form=form)

@app.route('/find')
def find_movie():
    movie_api_id = request.args.get("id")
    if movie_api_id:
        movie_api_url = f"https://api.themoviedb.org/3/movie/{movie_api_id}"
        response = requests.get(
            movie_api_url,
            params={
                "api_key": API_KEY,
                "language": "en-US"
            }
        )
        response.raise_for_status()
        data = response.json()

        year = int(data["release_date"].split("-")[0]) if data.get("release_date") else 0
        new_movie = Movie(
            title=data["title"],
            year=year,
            description=data["overview"],
            img_url=f"{MOVIE_DB_IMAGE_URL}{data['poster_path']}",
            rating=0.0,
            ranking=0,
            review=""
        )
        db.session.add(new_movie)
        db.session.commit()
        return redirect(url_for("editMovie", id=new_movie.id))
    return redirect(url_for("home"))

if __name__ == '__main__':
    app.run(debug=True)