from flask import Flask, request, render_template, session, redirect, url_for
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
from fiobank import FioBank

from functions import *

app = Flask(__name__)
app.secret_key = "SECRET_KEY"  # replaced the actual key
app.config.from_pyfile("app.cfg")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)

auth = HTTPBasicAuth()  # For /administration
db = SQLAlchemy(app)
mail = Mail(app)


class ticket(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    table = db.Column(db.Integer)
    is_for_standing = db.Column(db.Boolean)  # standing - True / sitting - False
    
    is_booked = db.Column(db.Boolean)  # Booked / available
    is_paid = db.Column(db.Boolean)
    was_collected = db.Column(db.Boolean)
    time_of_booking = db.Column(db.Integer)

    def __init__(self, id, table, standing):
        self._id = id
        self.table = table
        self.is_for_standing = standing
        
        self.user_id = None
        self.is_booked = False
        self.is_paid = False
        self.was_collected = False
        self.time_of_booking = 0


class user(db.Model):
    id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100))
    phone_number = db.Column(db.String(100))
    place_of_picking_up = db.Column(db.String(100))

    is_paid = db.Column(db.Boolean)
    was_collected = db.Column(db.Boolean)

    def __init__(self, jmeno, email, phone_number, place):
        self.name = jmeno
        self.email = email
        self.phone_number = phone_number
        self.place_of_picking_up = place
        
        self.is_paid = False
        self.was_collected = False


def return_table_availability():
    """When loading the tables on the hall's map
        Returns dictionary {table ID: available seats at the table (int)}
    """

    # Finds available seats at each table
    groupped_tables = db.session.query(
        ticket.table, db.func.count(ticket._id)
    ).filter(
        ticket.is_for_standing==False, ticket.is_booked==False, ticket.is_paid==False
    ).group_by(ticket.table)

    # Fills the dict with zeroes - for tables with no free seats
    tables_dict = {table_id: 0 for table_id in range(1, 114)}
    
    for (table_id, available_seats) in groupped_tables.all():
        tables_dict[table_id] = available_seats
    return tables_dict


def save_user_to_database():
    """
    After filling the user's information - it is saved to sqlite database and to the browser's session
    Returns an ID for the user.

    """
    place_of_picking_up = request.form["place_of_picking_up"]

    new_user = user(request.form["user_name"], request.form["email"], request.form["phone_number"], place_of_picking_up)
    db.session.add(new_user)
    db.session.commit()

    db.session.refresh(new_user)
    user_id = new_user.id
    session["user_id"] = user_id
    session["email"] = new_user.email
    
    return user_id


def return_available_standing_tickets(number_of_tickets):
    """
    Querries the database for available tickets for standing (returns False if there is not enough of them)
    """
    available_standing_tickets = ticket.query.filter(ticket.is_for_standing==True, ticket.is_booked==False)
    if len(available_standing_tickets.all()) >= number_of_tickets:
        tickets_to_return = available_standing_tickets[:number_of_tickets]
    else:
        return False
    return tickets_to_return


def return_available_sitting_tickets(table_availability):
    """
    Queries the database for tickets the user chose from the hall's map
    If the tickets are not available, it returns False
    """
    tickets_chosen = []
    for table_id, number_of_tickets in table_availability.items():
        available_tickets = ticket.query.filter(ticket.table==table_id, ticket.is_booked==False)
        if len(available_tickets.all()) >= number_of_tickets:
            tickets_chosen += available_tickets[:number_of_tickets]
        else:
            return False
    return tickets_chosen


def book_tickets(tickets_list, user_id):
    """
    Sets the tickets in database to booked (and sets the time of booking)
    Saves the IDs of booked tickets to session
    """
    time_now = datetime.now()

    for ticket in tickets_list:
        ticket.is_booked = True
        ticket.user_id = user_id
        ticket.time_of_booking = time_now
    db.session.commit()


def send_mail_to_user(subject, html, email=None, user_id=0):
    error = None
    if email is None:
        if "email" in session:
            email = session["email"]
        else:
            error = "The user's email was not found in the browser's session."

    if error is None:
        try:
            with mail.connect() as conn:
            
                msg = Message(subject=subject, sender="listky@210122.cz", recipients=[email])
                msg.html = html
                mail.send(msg)
                return True
        except Exception as e:
            error = e
    
    ### Error occured -> a mail is sent to administrator
    send_mail_to_admin(user_id, error, html)
    return False  # Email nebyl poslán uživateli
    

def send_mail_to_admin(id, error, html):
    email = "admin_mailk@example.com"
    try:
        with mail.connect() as conn:
        
            msg = Message(subject=f"The mail was not sent to user {str(id)}. Error {error}", 
                sender="listky@210122.cz", recipients=[email]
            )
            msg.html = html
            mail.send(msg)

            return True
    except Exception as e:
        return False


## HOME PAGE
@app.route("/")
def home():
    return render_template("homepage.html")


## Page with the form
@app.route("/form_standing", methods=["POST", "GET"])
def form_standing():
    if request.method == "POST":
        ## SAVE DATA TO DATABASE
        user_id = save_user_to_database()

        try:
            number_of_tickets = int(request.form["number_of_tickets"])
        except ValueError:
            number_of_tickets = 0
        
        
        returned_tickets = return_available_standing_tickets(number_of_tickets)
        if returned_tickets is not False and number_of_tickets < NUMBER_OF_TICKETS_LIMIT:
            book_tickets(returned_tickets, user_id)
            session["booked"] = {0: number_of_tickets}

            return redirect(url_for("summary_page"))
        else:
            return render_template("form_page.html", standing_tickets_input="", error=True)

    else:
        ## After clicking "Tickets for standing" at the homepage - redirecting to the form with input field for standing tickets
        return render_template("form_page.html", standing_tickets_input="", error=False)


@app.route("/form_sitting", methods=["POST", "GET"])
def form_sitting():
    if request.method == "POST":
        ## SAVE DATA TO DATABASE
        save_user_to_database()
        return redirect(url_for("table_map"))
    else:
        return render_template("form_page.html", standing_tickets_input=" hidden", error_code=False)


@app.route("/show_table_map", methods=["POST", "GET"])
def show_table_map():
    availability = return_table_availability()
    return render_template("table_map.html", tables=availability, error="")


## A hall's map for choosing seats for sitting
@app.route("/table_map", methods=["POST", "GET"])
def table_map():
    if request.method == "POST":
        error = None
        tables_chosen = dict()
        
        ## Reads the values from text fields for each chosen table
        for elem_key in request.form.keys():
            if "field" == elem_key[:5]:  ## Deletes 'field' from the element name - it is used only for sellecting the right elements
                try:
                    tables_chosen[elem_key[5:]] = int(request.form[elem_key])
                except Exception:
                    error = "Wrongly entered table."
        if tables_chosen == {}:
            error = "Choose at least one table."
        
        returned_tickets = return_available_sitting_tickets(tables_chosen)
        if returned_tickets is False:
            error = "Tickets could not be booked (someone was probably faster). Please, try it again."
        
        if len(returned_tickets) > NUMBER_OF_TICKETS_LIMIT:
            error = f"You choose too many seats. The limit is {NUMBER_OF_TICKETS_LIMIT}."

        if error is None:
            if "user_id" in session:
                book_tickets(returned_tickets, session["user_id"])

                session["booked"] = tables_chosen

            return redirect(url_for("summary_page"))
        

        ## Tickets were not booked
        availability = return_table_availability()
        return render_template("table_map.html", tables=availability, error=error)

    else:  ## For "GET" method
        if "user_id" not in session:
            return redirect(url_for("home"))
        availability = return_table_availability()
        return render_template("table_map.html", tables=availability, error="")



@app.route("/summary_page")
def summary_page():
    if "user_id" in session:
        user_id = session["user_id"]
    else:
        return redirect(url_for("home"))
    
    user_query = user.query.filter(user.id==user_id).first()

    if "booked" in session:
        tables_info, number_of_tickets = return_tables_info(session["booked"])
    else:
        tables_info, number_of_tickets = [], 0
        
    subject, message = create_summary_mail(user_query, tables_info, number_of_tickets)
    mail_sent = send_mail_to_user(subject, message, user_id=user_id)
    
    return render_template("summary_page.html", user=user_query, mail_sent=mail_sent, tickets=tables_info, price=number_of_tickets * PRICE, account_number=ACCOUNT_NUMBER)


###
### ADMINISTRATION PAGE
###


def edit_tickets_of_given_user(user_filter, column, value):
    """
    Edits the given user's "has paid" or "has picked up ticket" information
    column: "picked_up" / "paid"
    value: True / False
    Returns information about the change
    """
    
    user_before_changes = return_user_info(user_filter)

    if user_before_changes != ["User not found"]:
        user_query = find_user(user_filter)
        user_id = user_query.id
        if column == "picked_up":
            user_query.was_collected = value
        else:
            user_query.is_paid = value

        ticket_query = ticket.query.filter(ticket.user_id == user_id).all()
        for _ticket in ticket_query:
            if column == "picked_up":
                _ticket.was_collected = value
            else:
                _ticket.is_paid = value
        
        db.session.commit()
        user_after_change = return_user_info(user_id)

        if value == True:
            value_text = "yes"
        else:
            value_text = "no"

        user_after_change.insert(0, f"After commiting the change: {column} changed to {value_text} for the user ID {user_id}")
        return user_after_change + ["", "User before changes: "] + user_before_changes
    return user_before_changes



def find_user(name_or_id_int_str):
    """
    Returns user.query by the name or ID
    Returns None when the user was not found
    """

    name_or_id = str(name_or_id_int_str)
    if name_or_id.isdecimal():
        _user = user.query.filter(user.id == name_or_id).first()
    else:
        _user = user.query.filter(user.name.ilike("%" + name_or_id + "%")).first()

    return _user


def return_user_info(filter):
    """
    Finds the user in the database
    REturns ID, name, email, phone number, place of picking up, is_paid, was_collected + a list of his/her tickets
    """
    _user = find_user(filter)
    
    if _user is not None:
        user_id = _user.id
        returned_tickets = ticket.query.filter(ticket.user_id == user_id).all()
        list_to_return = [get_user_info_text(_user, len(returned_tickets))]

        for _listek in returned_tickets:
            list_to_return.append(get_ticket_text(_listek))

    else:
        list_to_return = ["User not found"]
    return list_to_return


def return_all_users(is_paid, was_collected, place_filter):
    """Returns information about all users
    User info with no booked tickets is written in italic
    """

    # Filtering of paid for and booked user tickets
    user_query = user.query

    paid_for_text = ""
    if is_paid != "none":
        if is_paid == "false":
            filter = False
            paid_for_text = " - not paid"
        elif is_paid == "true":
            filter = True
            paid_for_text = " - paid"
        user_query = user_query.filter(user.is_paid == filter)

    was_collected_text = ""
    if was_collected != "none":
        if was_collected == "false":
            was_collected_text = " - not picked up"
            filter = False
        elif was_collected == "true":
            was_collected_text = " - picked up"
            filter = True
        user_query = user_query.filter(user.was_collected == filter)
    
    place_text = ""
    if place_filter != "none":
        if place_filter == "office":
            place_text = " - in the office"
        elif place_filter == "eight":
            place_text = " - at class 8.C"
        elif place_filter == "four":
            place_text = " - at class 4.A"
        elif place_filter == "ideon":
            place_text = " - at IDEON"

        if place_filter == "office":
            user_query = user_query.filter(user.place_of_picking_up.in_(["office", "¨four", "eight"]))
        else:
            user_query = user_query.filter(user.place_of_picking_up == place_filter)
    
    user_query = user_query.all()
    list_to_return = []
    for _user in user_query:
        
        ## Writes info about users and his tickets (with group by)
        user_groupped_tables = db.session.query(
            ticket.table, db.func.count(ticket._id)
        ).filter(
            ticket.user_id == _user.id
        ).group_by(ticket.table)

        user_tables_dict = dict()
        for (table_number, number_of_seats) in user_groupped_tables.all():
            user_tables_dict[table_number] = number_of_seats

        user_tables_list, number_of_tickets = return_tables_info(user_tables_dict)
        user_tables_str = ", ".join(user_tables_list)

        user_info = get_user_info_text(_user, number_of_tickets)  # Returns all information
        user_info += ", seats: <b>" + user_tables_str + "</b>" # Adds tickets information

        # Users without tickets are written in italic
        if number_of_tickets == 0:
            user_info = "<i>" + user_info + "</i>"
        list_to_return.append(user_info)
    list_to_return.insert(0, f"Number of users found: {len(list_to_return)}")
    list_to_return.insert(0, f"Users filtration{paid_for_text}{was_collected_text}{place_text}")
    
    return list_to_return


def return_all_booked_tickets(paid, picked_up):
    """
    Returns a list of all booked tickets - their description
    """

    # Filtration of paid and picked_up tickets
    tickets_query = ticket.query.filter(ticket.is_booked == True)

    paid_for_text = ""
    if paid != "none":
        if paid == "false":
            filter = False
            paid_for_text = " - not paid"
        elif paid == "true":
            filter = True
            paid_for_text = " - paid"
        tickets_query = tickets_query.filter(ticket.is_paid == filter)

    picked_up_text = ""
    if picked_up != "none":
        if picked_up == "false":
            picked_up_text = " - not picked up"
            filter = False
        elif picked_up == "true":
            picked_up_text = " - picked up"
            filter = True
        tickets_query = tickets_query.filter(ticket.was_collected == filter)


    tickets_query = tickets_query.all()
    list_to_return = []
    for _ticket in tickets_query:
                list_to_return.append(get_ticket_text(_ticket))
    list_to_return.insert(0, f"Number of tickets found: {len(list_to_return)}")
    list_to_return.insert(0, f"Tickets filtration{paid_for_text}{picked_up_text}")
    return list_to_return


def show_payments(begin, end):
    """
    Returns a list of all received payments in the given time period
    """
    if FIO_TOKEN is None:
        return ["Could not connect to API"]
    try:
        client = FioBank(FIO_TOKEN)
        transactions = client.period(begin, end)
    except Exception:
        return ["Could not connect to API"]

    data_to_return = []
    incomes = 0
    expenses = 0
    for transaction in transactions:
        amount = transaction["amount"]
        if amount > 0:
            incomes += amount
        else:
            expenses += amount

        message = ""
        if transaction["recipient_message"] is not None:
            message += f', message: {transaction["recipient_message"]}'
        
        date = transaction["date"]
        date_string = f"{date.day}. {date.month}. {date.year}"

        transaction_text = f"VS (ID): <b>{transaction['variable_symbol']}</b>, name: {transaction['user_identification']}, amount: <b>{transaction['amount']} Kč</b>, account: {transaction['account_number_full']}{message}, date: {date_string}"
        data_to_return.append(transaction_text)
    data_to_return.insert(0, f"Received <b>{int(incomes):,} Kč</b> ({int(incomes/PRICE):,} tickets), expenses: {int(expenses):,} Kč, total balance: {int(incomes + expenses):,} Kč")
    return data_to_return


def pay_for_user(user_query, tickets_query):
    """
    Sets tickets and user as "paid"
    Sends an email confirming the booking's payment.
    """
    total_payment = 0
    user_query.is_paid = True
    for _ticket in tickets_query:
        _ticket.is_paid = True
        total_payment += PRICE
    db.session.commit()

    mail = user_query.email
    subject, html_mail = create_payment_mail(user_query, total_payment)
    send_mail_to_user(subject, html_mail, mail, user_query.id)


def set_payments():
    # Returns ["User X paid", "User Y overpaid XXX KČ", "User Z did not pay"]
    
    if FIO_TOKEN is None:
        return False
    # API connection
    try:
        client = FioBank(FIO_TOKEN)
        transactions = client.period("2021-07-01", "2022-12-31")
    except Exception:
        return False
    
    payments_dict = {}  # {(user)2: 20000(Kč)}
    for transaction in transactions:
        if transaction["currency"] == "CZK" and transaction["variable_symbol"] is not None:
            variable_symbol = int(transaction["variable_symbol"])
            amount = int(transaction["amount"])
            payments_dict[variable_symbol] = payments_dict.get(variable_symbol, 0) + amount

    result_payment = []
    
    not_paid_users = user.query.filter(user.is_paid==False).all()
    for user_query in not_paid_users:
        user_id = user_query.id

        if user_id in payments_dict.keys():
            user_tickets = ticket.query.filter(ticket.user_id==user_id).all()
            price = len(user_tickets) * PRICE

            if price == payments_dict[user_id]:
                result_payment.append(f"User {user_id} paid ({price} Kč).")
                pay_for_user(user_query, user_tickets)
            elif price < payments_dict[user_id]:
                result_payment.append(f"User {user_id} OVERPAID ({payments_dict[user_id]} X {price}).")
                pay_for_user(user_query, user_tickets)
            elif price > payments_dict[user_id]:
                result_payment.append(f"!!!User {user_id} paid too little ({payments_dict[user_id]} X {price}).")
        else:
            result_payment.append(f"User {user_id} has not paid yet.")
    return result_payment


def send_mail_cancellation(users_id):
    for user_id in users_id:
        user_query = user.query.filter(user.id==user_id).first()
        
        subject, mail_html = create_cancellation_mail()
        if user_query is not None:
            email = user_query.email
            send_mail_to_user(subject, mail_html, email, user_id)
        else:
            send_mail_to_admin(user_id, "Booking cancellation mail was not sent", mail_html)


def cancel_ticket(_ticket):
    ticket_info = get_ticket_text(_ticket)
    
    session["cancelled_tickets"][_ticket.user_id] = session["cancelled_tickets"].get(_ticket.user_id, []) + [_ticket._id]
    _ticket.user_id = None
    _ticket.is_booked = False
    _ticket.is_paid = False
    db.session.commit()

    return ticket_info

    
def return_invalid_booking():
    session["cancelled_tickets"] = {}
    cancelled_bookings = []
    not_paid = ticket.query.filter(ticket.is_booked==True, ticket.is_paid==False, ticket.was_collected==False).all()
    today = datetime.now()

    users_with_cancelled_tickets_ids = []

    for _ticket in not_paid:
        booking_time = datetime.strptime(_ticket.booking_time, "%Y-%m-%d %H:%M:%S.%f")    
        delta = (today - booking_time).days
    
        if delta > BOOKING_DAYS_LIMIT:
            if _ticket.user_id not in users_with_cancelled_tickets_ids:
                users_with_cancelled_tickets_ids.append(_ticket.user_id)
            
            # Cancelling the booking
            ticket_info = cancel_ticket(_ticket)
            cancelled_bookings.append(ticket_info)
            
    cancelled_bookings.insert(0, f"Number of cancelled tickets: {len(cancelled_bookings)}")

    send_mail_cancellation(users_with_cancelled_tickets_ids)
    return cancelled_bookings


def cancel_specific_ticket(user_id, ticket_id):
    _ticket = ticket.query.filter(ticket.is_booked==True, ticket.user_id==user_id, ticket._id==ticket_id).first()
    if _ticket is not None:
        session["cancelled_tickets"] = {}
        data_to_return = ["Ticket: " + cancel_ticket(_ticket) + " cancelled"]
    else:
        data_to_return = [f"Ticket {ticket_id} was not found at user with ID {user_id}"]
    return data_to_return


def restore_cancelled_bookings():
    if "cancelled_tickets" not in session:
        return ["No tickets were cancelled"]
    restored_tickets = ["<i>Warning! The payment was not restored!!!</i>\n"]
    tickets_to_restore = session["cancelled_tickets"]
    for user_id, tickets in tickets_to_restore.items():
        restored_tickets.append(f"\nRestored for user {str(user_id)}:")
        for ticket_id in tickets:
            _ticket = ticket.query.filter(ticket._id==ticket_id).first()
            _ticket.user_id = user_id
            _ticket.is_booked = True
            restored_tickets.append(f"Ticket {ticket_id}")
    db.session.commit()

    
    return restored_tickets

def delete_user_if_no_bookings(user_id):
    user_info = return_user_info(user_id)

    tickets = ticket.query.filter(ticket.user_id==user_id).all()
    if len(tickets) == 0:
        user.query.filter(user.id==user_id).delete()
        db.session.commit()
        return [f"User {user_id} deleted", f"User's information before deletion:"] + [info for info in user_info]
    else:
        return [f"User {user_id} has some bookings"]


@auth.verify_password
def verify_password(username, password):
    if username == app.config["USERNAME"] and \
            check_password_hash(app.config["PASSWORD_HASH"], password):
        return username
    if username == app.config["OFFICE_USERNAME"] and \
            check_password_hash(app.config["OFFICE_HASH"], password):
        return username


@app.route("/administration", methods=["GET", "POST"])
@auth.login_required
def payments():
    if request.method == "GET":
        return render_template("administration.html", invalid=None, user_id="0", tickets_id="0", paid_filter="true", picked_filter="false", place_filter="office")
    else:
        if request.form["submit_btn"] == "payments":
            # Sets payments and deletes invalid bookings
            payments = set_payments()
            if payments is not False:
                data_to_show = payments + return_invalid_booking()
            else:
                data_to_show = ["Payments were not checked - API connection error."]
        elif request.form["submit_btn"] == "return_cancellation":
            data_to_show = restore_cancelled_bookings()
        elif request.form["submit_btn"] == "find_user":
            data_to_show = return_user_info(request.form["user_id"])
        elif request.form["submit_btn"] == "show_users":
            data_to_show = return_all_users(request.form["paid_true_false"], request.form["picked_up_true_false"], request.form["place"])
        elif request.form["submit_btn"] == "show_tickets":
            data_to_show = return_all_booked_tickets(request.form["paid_true_false"], request.form["picked_up_true_false"])
        
        elif request.form["submit_btn"] == "set_paid":
            if request.form["true_false"] == "true":
                set_value = True
            else:
                set_value = False
            data_to_show = edit_tickets_of_given_user(request.form["user_id"], "paid", set_value)
        
        elif request.form["submit_btn"] == "set_picked_up":
            if request.form["true_false"] == "true":
                set_value = True
            else:
                set_value = False
            data_to_show = edit_tickets_of_given_user(request.form["user_id"], "picked_up", set_value)
        
        elif request.form["submit_btn"] == "cancel_specific_ticket":
            data_to_show = cancel_specific_ticket(request.form["user_id"], request.form["ticket_id"])
        elif request.form["submit_btn"] == "delete_user":
            data_to_show = delete_user_if_no_bookings(request.form["user_id"])
        elif request.form["submit_btn"] == "show_payments":
            data_to_show = show_payments(request.form["start_date"], request.form["end_date"])
        
        return render_template("administration.html", output_text=data_to_show,
            user_id=request.form["user_id"], ticket_id=request.form["ticket_id"], signed_user=auth.username(),
            paid_filter=request.form["paid_true_false"], picked_filter=request.form["picked_up_true_false"], place_filter=request.form["place"]
            )


### Start the script

if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)