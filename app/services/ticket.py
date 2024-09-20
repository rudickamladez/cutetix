"""Module for easier ticket management"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from app import models
from app.schemas import ticket, ticket_group
from datetime import datetime
import sys

# Here are the email package modules we'll need.
from .mail import get_default_sender, get_mail_client

def can_create_ticket_in_ticket_group(
        group_id: int,
        db: Session
    ):
    # Get ticket group from database
    tg: ticket_group.TicketGroup = models.TicketGroup.get_by_id(db_session=db, id=group_id)

    # Ticket group is not in database
    if tg is None:
        print(
            "Ticket group is not in database",
            file=sys.stderr,
        )
        return False

    # Prepare event for checks
    event = models.Event.get_by_id(db_session=db, id=tg.event_id)
    # Event is not in database
    if event is None:
        print(
            "Event is not in database.",
            file=sys.stderr
        )
        return False

    # Check if it's not end of reservations for the event
    if event.tickets_sales_end < datetime.now():
        print(
            "Reservations are closed.",
            file=sys.stderr
        )
        return False

    # Check if reservations started for the event
    if event.tickets_sales_start > datetime.now():
        print(
            "Reservations are not opened yet.",
            file=sys.stderr
        )
        return False
    
    # Check if there is place for the ticket in ticket group
    count_of_tickets_in_tg = db.query(func.count(models.Ticket.id)).filter(models.Ticket.group_id == group_id).scalar()
    if count_of_tickets_in_tg >= tg.capacity:
        print(
            "Ticket group is already full.",
            file=sys.stderr
        )
        return False
    return True

def create_ticket_easily(
        t: ticket.Ticket,
        db: Session
    ):

    if "@" not in t.email:
        return None
    
    # Check if they can create ticket
    if not can_create_ticket_in_ticket_group(t.group_id, db=db):
        return None

    # Write ticket to database
    t_db: ticket.Ticket = models.Ticket.create(db_session=db, **t.model_dump())

    # Prepare SMTP sender address
    smtp_sender = t_db.group.event.smtp_mail_from or get_default_sender()

    # Send the email via SMTP server
    smtp_client = get_mail_client()
    smtp_client.send(
        subject="Vaše vstupenka",
        sender=smtp_sender,
        receivers=[t_db.email],
        text=t_db.group.event.mail_text_new_ticket,
        html=t_db.group.event.mail_html_new_ticket,
    )
    return t_db