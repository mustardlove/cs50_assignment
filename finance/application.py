import os
import datetime

# configure sql, flask and flask session
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session

from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

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
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # extract the stocks and the number of shares the user owns
    records = db.execute("SELECT symbol, SUM(shares) AS shares FROM history WHERE user_id = :id GROUP BY symbol", id=session["user_id"])
    # extract the current cash balance of the user
    cash = db.execute("SELECT cash FROM users WHERE id = :id", id=session["user_id"])[0]['cash']
    cash = format(cash, '.2f')

    # add necessary values (price, total)
    for record in records:
        symbol = record['symbol']
        price = lookup(symbol)['price']
        record['price'] = price
        record['total'] = format(price * record['shares'], '.2f')

    return render_template("index.html", records=records, cash=cash)




@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        # check input
        symbol = request.form.get('symbol')
        if not symbol:
            return apology("You must provide symbol!")

        quote = lookup(symbol)
        if not quote:
            return apology("This symbol does not exist!")

        shares = request.form.get('shares')
        if not shares:
            return apology("You must provide how much you want to buy!")

        shares = int(shares)
        if shares <= 0:
            return apology("Please enter an integer greater than 0!")

        # handle the purchase
        balance = db.execute("SELECT cash FROM users WHERE id = :id;", id=session["user_id"])[0]['cash'] # 유저를 어떻게 알지?
        amount = shares * quote["price"]
        difference = balance - amount
        if difference > 0:
            # record the buy transaction
            db.execute("INSERT INTO history (user_id, buy, symbol, price, shares, datetime) VALUES (:id, 1, :symbol, :price, :shares, :datetime)",
                        id=session["user_id"], symbol=quote["symbol"], price=quote["price"], shares=shares, datetime=str(datetime.datetime.now()))
            # update user's balance
            db.execute("UPDATE users SET cash = :cash WHERE id = :id;", id=session["user_id"], cash=difference)

            # to homepage
            return redirect("/")

        else:
            return apology("You don't have enough balance to buy the stock!")
    else:
        return render_template("buy.html")


### for test: this works perfectly
@app.route("/gotest", methods=["GET"])
def gotest():
    return render_template("test.html")


@app.route("/test", methods=["GET"])
def test():
    user = request.args.get('q')
    print("test user: ", user)
    return jsonify({"length": len(user)})
#############


@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    username = request.args.get('q')
    print("I got: ", username)
    exist = db.execute("SELECT * FROM users WHERE username = :username;", username=username)
    print("length: ", len(exist))

    # If valid
    if len(username) >= 1 and len(exist) == 0:
        print("good!")
        return jsonify({"result": True})

    # If not valid in either case
    else:
        print("Nah!")
        return jsonify({"result": False})




@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    records = db.execute("SELECT symbol, shares, price, datetime FROM history WHERE user_id = :id;", id=session['user_id'])
    return render_template("history.html", records=records)


# login() is already implemented
@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

# logout() is already implemented
@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == 'GET':
        return render_template("quote.html")

    else:
        symbol = request.form.get('symbol')
        if not symbol:
            return apology("please enter symbol!")

        quote = lookup(symbol) # dict of name, price, symbol
        if not quote:  
            return apology("invalid symbol!")

        return render_template("quoted.html", quote=quote)



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # get input
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirmation = request.form.get('confirmation')

        # check for input
        if not username:
            return apology("Hey, Please enter username!")
        if not password or not confirmation:
            return apology("please enter password!")
        if password != confirmation:
            return apology("passwords do not match!")

        # protect user's password
        hash = generate_password_hash(password)

        # insert this new user into database (id는 어떻게 해? auto-increment 맞아?) 어 맞아
        result = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash);", username=username, hash=hash)
        if not result:
            return apology("The username is already taken. Please try with new one!")

        # once register successfully, log in the user automatically (어떻게?) 이렇게 하니 문제는 없더라
        session['user_id'] = result
        return redirect("/")

    else:
        return render_template("register.html")



@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == 'POST':
        symbol = request.form.get('symbol')
        shares = request.form.get('shares')
        if not symbol or not shares:
            return apology("missing input!")

        quote = lookup(symbol)
        if not quote:
            return apology("hey, invalid symbol!")

        shares = int(shares)

        own = db.execute("SELECT SUM(shares) AS shares FROM history WHERE user_id = :id GROUP BY symbol HAVING symbol = :symbol;",
                        id=session['user_id'], symbol=quote['symbol'])[0]['shares']

        if shares <= 0:
            return apology("please enter positive integer!")
        if shares > own:
            return apology("you don't have enough shares to sell")

        amount = shares * quote['price']
        cash = db.execute("SELECT cash FROM users WHERE id = :id", id=session['user_id'])[0]['cash']

        # record sell transaction 
        db.execute("INSERT INTO history (user_id, buy, symbol, price, shares, datetime) VALUES (:id, 0, :symbol, :price, :shares, :datetime);"
                    , id=session['user_id'], symbol=quote['symbol'], price=quote['price'], shares=-shares, datetime=str(datetime.datetime.now()))
        # update cash balance
        db.execute("UPDATE users SET cash = :cash;", cash=cash+amount)

        # to homepage
        return redirect("/")

    else:
        result = db.execute("SELECT DISTINCT symbol FROM history WHERE user_id = :id;", id=session['user_id'])
        return render_template("sell.html", stocks=result)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
