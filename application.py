import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# For Time
import datetime
time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///secret.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show All recived Secret notification and gifts"""
    # Get cash from userdata
    user_id = session["user_id"]

    # Get all userdatas data from database
    new = db.execute("SELECT * FROM names")

    # Get all userdatas data from database
    portfolio = db.execute("SELECT message, gift, datetime FROM notification WHERE user_id= ? ORDER BY datetime DESC", user_id)
    if not portfolio:
        return render_template("index.html", portfolio=portfolio, usersname=new)

    # Get add total value of holdings in total value of available cash
    total = 0
    for data in portfolio:
        messages = data['message']
        total += 1

    return render_template("index.html", notifications=portfolio, totals=total, usersname=new)


@app.route("/")
@app.route('/<int:uid>/visit/')
@login_required
def visit(uid):
    """Show Profile """
    # Store current opened profile ID
    session["uid"] = uid

    # Get all userdata from database
    user_profile = db.execute("SELECT id,username FROM user WHERE id= ? ", uid)
    notification = db.execute("SELECT message,gift,datetime FROM notification where user_id = ? ORDER BY datetime DESC", uid)

    return render_template("visit.html", profile=user_profile, notifications=notification)


@app.route("/profile")
@login_required
def profile():
    """Show Profile """
    user_id = session["user_id"]

    # Get all userdata from database
    user_profile = db.execute("SELECT id,username FROM user WHERE id= ? ", user_id)
    notification = db.execute("SELECT message,gift,datetime FROM notification where user_id = ? ORDER BY datetime DESC", user_id)

    return render_template("profile.html", profile=user_profile, notifications=notification)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any userdata_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return flash("must provide username!")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return flash("must provide password!")

        username = request.form.get("username")

        # Query database for username
        rows = db.execute("SELECT * FROM user WHERE username = ?", username)

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return flash("invalid username and/or password!")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        flash("Logged in Successfully!")

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/all_notification")
@login_required
def notification():
    """Get Notification."""

    user_id = session["user_id"]

    # Get user's Notifications from database
    notification = db.execute("SELECT message,gift,datetime FROM notification where user_id = ? ORDER BY datetime DESC", user_id)

    # Get total number of notification
    total = 0
    for data in notification:
        messages = data['message']
        total += 1
    return render_template("notification.html", notifications=notification, total=total)


@app.route("/gift")
@login_required
def gift():
    """Get Gift."""

    user_id = session["user_id"]

    # Get user's Gifts from database
    gift = db.execute("SELECT gift, datetime FROM notification where user_id = ? ORDER BY datetime DESC", user_id)

    # Get total worth of gifts recieved
    total = 0
    for cash in gift:
        total += cash['gift']

    return render_template("gift.html", gifts=gift, total=total)


@app.route("/text", methods=["GET", "POST"])
@login_required
def text():
    """ Send a Text & Gift """
    user = session["user_id"]

    # Get Current Profile id
    uid = session["uid"]

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure text was submitted
        if not request.form.get("text"):
            return flash("must provide text!")

        # Ensure gift was submitted
        elif not request.form.get("gift"):
            return flash("must provide gift!")

        # Get Message and Gift
        message = request.form.get("text")
        gift = request.form.get("gift")

        # Get current profile's  name  from database
        current_user = db.execute("SELECT username FROM names WHERE user_id= ? ", uid)
        current_user = (list(current_user)[-1])
        current_user = current_user.get('username')

        # store messaage in sender's  "sent" and receiver's Notification
        db.execute("INSERT INTO sent (user_id, to_username, message, gift, datetime)values(?, ?, ?, ?, ?)",
                   user, current_user, message, gift, time)

        db.execute("INSERT INTO notification (user_id, message, gift, datetime) values(?, ?, ?, ?) ", uid, message, gift, time)

        flash("Message Sent!")

        return redirect("/")
    else:
        # Get username of current profile from database
        new = db.execute("SELECT username FROM names where user_id= ?", uid)
        return render_template("text.html", their=new)


@app.route("/sent")
@login_required
def sent():
    """Show Profile """
    # Get Current Profile id
    user_id = session["user_id"]

    # Get all userdata from database
    notification = db.execute("SELECT  to_username, message, gift, datetime FROM sent WHERE user_id = ? ORDER BY datetime DESC", user_id)

    # Get total spend on gifts and notification count
    total = 0
    messagetotal = 0
    for cash in notification:
        total += cash['gift']
        messages = cash['message']
        messagetotal += 1

    return render_template("sent.html", sent=notification,  spent=total, message=messagetotal)


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():

    # Get Current Profile id
    user = session["user_id"]

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure user wants to Delete Account
        if "CONFIRM" == request.form.get("confirmation"):

            # Delete all userdata from database
            db.execute("DELETE FROM user WHERE id= ? ", user)
            db.execute("DELETE FROM names WHERE user_id= ? ", user)
            db.execute("DELETE FROM sent WHERE user_id= ? ", user)
            db.execute("DELETE FROM notification WHERE user_id= ? ", user)

            flash("Account Deleted!")
            # Forget any user_id
            session.clear()

            # Redirect user to login form
            return redirect("/")

    else:
        return render_template("settings.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any userdata_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        name = request.form.get("username")

        # Ensure username was submitted
        if not request.form.get("username"):
            return flash("must provide username!")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return flash("must provide password!")

         # Ensure password (again) was submitted
        elif not request.form.get("confirmation"):
            return flash("must provide password(again)!")

        # Ensure passwords match
        elif request.form.get("password") != request.form.get("confirmation"):
            return flash("Passwords didn't match!")

        # Check if username is taken
        row = db.execute("SELECT count(id) as count FROM user WHERE username = ?", name)

        if row[0]["count"] > 0:
            return flash("Username alreday taken!")

        # Create Hash password
        hash_password = generate_password_hash(request.form.get("confirmation"))

        # Register database for username Ensure username doesn't exists
        new_user = db.execute("INSERT INTO user (username, hash) VALUES(?, ?)", name, hash_password)
        db.execute("INSERT INTO names (username) VALUES(?)", name)

        session["user_id"] = new_user

        flash("Registered!")
        # Redirect user to home page
        return redirect("/")

    # user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
