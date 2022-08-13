from flask import render_template

## Constants
PRICE = 300
ACCOUNT_NUMBER = "XXXXXXXX/XXXX"
NUMBER_OF_TICKETS_LIMIT = 21
BOOKING_DAYS_LIMIT = 3
FIO_TOKEN = ""


def create_summary_mail(user, tables_info, number_of_tickets):
    tables_info_text = ', '.join(tables_info)

    subject = "Confirmation of ticket booking for Gyholi Maturita Prom"

    html_body = render_template("confirmation_mail.html", user=user, 
            tables_info=tables_info_text, number_of_tickets=number_of_tickets, price=PRICE, account_number=ACCOUNT_NUMBER
    )

    return subject, html_body


def create_payment_mail(user, total_payment):
    subject = "Your Prom tickets were paid for"

    html_body = render_template("payment_mail.html", uzivatel=user, total_price=total_payment)

    return subject, html_body


def create_cancellation_mail():
    subject = "Booking of your tickets was cancelled"
    html_body = render_template("cancellation_mail.html")
    return subject, html_body



def get_ticket_text(_ticket):
    if _ticket.is_paid == False:
        pay_text = "not paid"
    else:
        pay_text = "paid"
    if _ticket.was_collected == False:
        pick_text = "not picked up"
    else:
        pick_text = "picked up"

    if _ticket.table is None:
        table = "standing"
    elif _ticket.table <= 43:
        table = f"table {str(_ticket.table)} (Great Hall)"
    elif _ticket.table <= 65:
        table = f"table {str(_ticket.table)} (Left Hall)"
    elif _ticket.table <= 83:
        table = f"table {str(_ticket.table)} (Right Hall)"
    else:
        table = f"table {str(_ticket.table - 83)} (Second Floor) <i>({_ticket.table})</i>"

    return f" ID: {_ticket._id}, user ID: {_ticket.user_id}, time: {str(_ticket.time_of_booking).split('.')[0]}, {table}, \
{pay_text}, {pick_text}"



def get_user_info_text(user, number_of_tickets):
    if user.is_paid == False:
        pay_text = "<b>not paid</b>"
    else:
        pay_text = "paid"
    if user.was_collected == False:
        pick_text = "<b>not picked up</b>"
    else:
        pick_text = "picked up"
    
    if user.place_of_picking_up == "office":
        place_text = "in the school's office"
    elif user.place_of_picking_up == "eight":
        place_text = "at 8.C"
    elif user.place_of_picking_up == "four":
        place_text = "at 4.A"
    elif user.place_of_picking_up == "ideon":
        place_text = "at IDEON"
    else:
        place_text = ""

    text_to_return = f"ID <b>{user.id}</b>, \nname: <b>{user.name}</b>, \n \
    picking up {place_text},\n {pay_text}, \n{pick_text}, \nnumber of tickets: {number_of_tickets}"
    return text_to_return


def return_tables_info(tables_tickets_dict):
    info_list = []
    number_of_tickets = 0
    if None in tables_tickets_dict.keys():
        tables_tickets_dict[0] = tables_tickets_dict[None]
        del tables_tickets_dict[None]
    
    for table_id, table_seats in sorted(tables_tickets_dict.items()):
        number_of_tickets += table_seats

        table_id = int(table_id)
        if table_id == 0:
            info_list.append(f"({table_seats} tickets for standing)")
            continue
        elif table_id <= 43:
            hall = "Great Hall"
        elif table_id <= 65:
            hall = "Left Hall"
        elif table_id <= 83:
            hall = "Right Hall"
        else:
            hall = "Second Floor"
            table_id = table_id - 83
        info_list.append(f"table no. {str(table_id)} ({hall}, {str(table_seats)} seats)")

    return info_list, number_of_tickets