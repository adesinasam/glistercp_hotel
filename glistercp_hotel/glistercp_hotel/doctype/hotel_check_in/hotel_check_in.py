# -*- coding: utf-8 -*-
# Copyright (c) 2024, Glistercp and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, flt
from frappe.core.doctype.sms_settings.sms_settings import send_sms


class HotelCheckIn(Document):
    def validate(self):
        for room in self.rooms:
            room_doc = frappe.get_doc('Rooms', room.room_no)
            if room_doc.room_status != 'Available':
                frappe.throw('Room {} is not Available'.format(room.room_no))

    def on_submit(self):
        self.status = 'To Check Out'
        doc = frappe.get_doc('Hotel Check In', self.name)
        doc.db_set('status', 'To Check Out')
        for room in self.rooms:
            room_doc = frappe.get_doc('Rooms', room.room_no)
            room_doc.db_set('check_in_id', self.name)
            room_doc.db_set('room_status', 'Checked In')
        check_in_doc = frappe.get_doc('Hotel Check In', self.name)
        all_checked_in = 1
        # send_payment_sms(self)

        # Setting Check In doc to Complete
        for room in check_in_doc.rooms:
            if frappe.db.get_value('Rooms', room.room_no, 'room_status') == 'Available':
                all_checked_in = 0

        # Creating Additional Hotel Payment Vouchers
        if self.amount_paid > 0 and self.customer == 'Hotel Walk In Customer':
            self.create_payment_entry(self.amount_paid)
        
        # Creating Sales Invoice
        self.create_sales_invoice(all_checked_in)

    def on_cancel(self):
        self.status = "Cancelled"
        doc = frappe.get_doc('Hotel Check In', self.name)
        doc.db_set('status', 'Cancelled')
        for room in self.rooms:
            room_doc = frappe.get_doc('Rooms', room.room_no)
            room_doc.db_set('check_in_id', None)
            room_doc.db_set('room_status', 'Available')

    def create_payment_entry(self, amount_paid, entry_type='Receive'):
        for item in self.rooms:
            payment_doc = frappe.new_doc('Hotel Payment Entry')
            payment_doc.update({
                'room': item.room_no,
                'amount_paid': item.amt_paid,
                'guest_id': self.guest_id,
                'check_in_id': self.name,
                'guest_name': self.guest_name,
                'contact_no': self.contact_no,
                'mode_of_payment': self.mode_of_payment
                'mode_of_payment': self.reference_no
                'mode_of_payment': self.reference_date
            })
            payment_doc.save()
            payment_doc.submit()

    def create_sales_invoice(self, all_checked_in):
        if self.customer == 'Hotel Walk In Customer':
            self.create_invoice('Hotel Walk In Customer', self.name)

        # if all_checked_in == 1 or self.customer != 'Hotel Walk In Customer':
        #     create_walk_in_invoice = any(item.is_pos == 1 for item in self.rooms)
        #     if create_walk_in_invoice:
        #         self.create_invoice('Hotel Walk In Customer', self.name)

        #     check_out_list = frappe.get_list('Hotel Check In', filters={
        #         'docstatus': 1,
        #         'check_in_id': self.name,
        #         'customer': ['not like', 'Hotel Walk In Customer']
        #     }, order_by='name asc')
        #     if all_checked_in == 1 and check_out_list:
        #         self.create_invoice(check_out_list[0].customer, self.name)

    def create_invoice(self, customer, check_in_id):
        sales_invoice_doc = frappe.new_doc('Sales Invoice')
        company = frappe.get_doc('Company', self.company)
        sales_invoice_doc.update({
            'customer': customer,
            'check_in_id': check_in_id,
            'guest_id': self.guest_id,
            'check_in_date': frappe.get_value('Hotel Check In', check_in_id, 'check_in'),
            'due_date': frappe.utils.data.today(),
            'debit_to': company.default_receivable_account
        })

        for item in self.rooms:
            item_doc = frappe.get_doc('Item', item.room_no)
            default_income_account = company.default_income_account

            # if item.is_pos == 1:
            #     default_income_account = item_doc.get_income_account()

            sales_invoice_doc.append('items', {
                'item_code': item_doc.item_code,
                'item_name': item_doc.item_name,
                'description': item_doc.description,
                'qty': item.qty,
                'uom': item_doc.stock_uom,
                'rate': item.price,
                'amount': item.amount,
                'income_account': default_income_account
            })

        if self.discount:
            sales_invoice_doc.discount_amount = self.discount

        sales_invoice_doc.insert(ignore_permissions=True)
        sales_invoice_doc.submit()

    @frappe.whitelist()
    def calculate_stay_days(self):
        stay_days = date_diff(self.to_date, self.from_date)
        return stay_days

    @frappe.whitelist()
    def get_room_price(self, room):
        room_price = frappe.get_value('Rooms', {'room_number': room}, 'price')
        return room_price


def send_payment_sms(self):
    sms_settings = frappe.get_doc('SMS Settings')
    if sms_settings.sms_gateway_url:
        msg = 'Dear '
        msg += self.guest_name
        msg += ''',\nWe are delighted that you have selected our hotel. The entire team at the Hotel PakHeritage welcomes you and trust your stay with us will be both enjoyable and comfortable.\nRegards,\nHotel Management'''
        send_sms([self.contact_no], msg = msg)