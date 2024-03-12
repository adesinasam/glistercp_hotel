# -*- coding: utf-8 -*-
# Copyright (c) 2024, Glistercp and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import date_diff

class HotelCheckOut(Document):
    def validate(self):
        room_doc = frappe.get_doc('Rooms', self.room)
        if room_doc.room_status != 'Checked In' and room_doc.check_in_id == self.check_in_id:
            frappe.throw('Room Status is not Checked In')

    def on_submit(self):
        room_doc = frappe.get_doc('Rooms', self.room)
        room_doc.db_set('room_status', 'Available')
        room_doc.db_set('check_in_id', None)
        check_in_doc = frappe.get_doc('Hotel Check In', self.check_in_id)
        all_checked_out = 1

        # Setting Food Orders and Laundry Orders to Complete
        self.update_orders_status('Hotel Food Order', 'To Check Out')
        self.update_orders_status('Hotel Laundry Order', 'To Check Out')

        # Setting Check In doc to Complete
        for room in check_in_doc.rooms:
            if frappe.db.get_value('Rooms', room.room_no, 'room_status') == 'Checked In':
                all_checked_out = 0
        if all_checked_out == 1:
            check_in_doc.db_set('status', 'Completed')

        # Creating Additional Hotel Payment Vouchers
        if self.amount_paid > 0 and self.customer == 'Hotel Walk In Customer':
            self.create_payment_entry(self.amount_paid - self.refund)
        
        if self.amount_paid == 0 and self.refund > 0:
            self.create_payment_entry(self.refund, entry_type='Refund')

        # Creating Sales Invoice
        self.create_sales_invoice(all_checked_out)

    def update_orders_status(self, doctype, status):
        order_list = frappe.get_list(doctype, filters={
            'status': status,
            'room': self.room,
            'check_in_id': self.check_in_id
        })

        for order in order_list:
            order_doc = frappe.get_doc(doctype, order.name)
            order_doc.db_set('status', 'Completed')

    def create_payment_entry(self, amount_paid, entry_type='Receive'):
        payment_doc = frappe.new_doc('Hotel Payment Entry')
        payment_doc.update({
            'room': self.room,
            'amount_paid': amount_paid,
            'guest_id': self.guest_id,
            'check_in_id': self.check_in_id,
            'guest_name': self.guest_name,
            'contact_no': self.contact_no
        })
        payment_doc.save()
        payment_doc.submit()

    def create_sales_invoice(self, all_checked_out):
        if self.customer == 'Hotel Walk In Customer':
            self.create_invoice('Hotel Walk In Customer', self.check_in_id)

        if all_checked_out == 1 or self.customer != 'Hotel Walk In Customer':
            create_walk_in_invoice = any(item.is_pos == 1 for item in self.items)
            if create_walk_in_invoice:
                self.create_invoice('Hotel Walk In Customer', self.check_in_id)

            check_out_list = frappe.get_list('Hotel Check Out', filters={
                'docstatus': 1,
                'check_in_id': self.check_in_id,
                'customer': ['not like', 'Hotel Walk In Customer']
            }, order_by='name asc')
            if all_checked_out == 1 and check_out_list:
                self.create_invoice(check_out_list[0].customer, self.check_in_id)

    def create_invoice(self, customer, check_in_id):
        sales_invoice_doc = frappe.new_doc('Sales Invoice')
        company = frappe.get_doc('Company', self.company)
        sales_invoice_doc.update({
            'customer': customer,
            'check_in_id': check_in_id,
            'check_in_date': frappe.get_value('Hotel Check In', check_in_id, 'check_in'),
            'due_date': frappe.utils.data.today(),
            'debit_to': company.default_receivable_account
        })

        for item in self.items:
            item_doc = frappe.get_doc('Item', item.item)
            default_income_account = company.default_income_account

            if item.is_pos == 1:
                default_income_account = item_doc.get_income_account()

            sales_invoice_doc.append('items', {
                'item_code': item_doc.item_code,
                'item_name': item_doc.item_name,
                'description': item_doc.description,
                'qty': item.qty,
                'uom': item_doc.stock_uom,
                'rate': item.rate,
                'amount': item.amount,
                'income_account': default_income_account
            })

        if self.discount:
            sales_invoice_doc.discount_amount += self.discount
        if self.food_discount != 0:
            sales_invoice_doc.discount_amount += self.food_discount

        sales_invoice_doc.insert(ignore_permissions=True)
        sales_invoice_doc.submit()

    @frappe.whitelist()
    def get_check_in_details(self):
        room_doc = frappe.get_doc('Rooms', self.room)
        check_in_doc = frappe.get_doc('Hotel Check In', room_doc.check_in_id)
        return [check_in_doc.name, check_in_doc.cnic, check_in_doc.guest_name, check_in_doc.check_in, check_in_doc.contact_no, check_in_doc.guest_id]

    @frappe.whitelist()
    def calculate_stay_days(self):
        return date_diff(self.check_out, self.check_in)

    @frappe.whitelist()
    def get_items(self):
        # Getting Hotel Check In Details
        hotel_check_in = frappe.get_doc('Hotel Check In', self.check_in_id)
        check_in_dict = {}
        for room in hotel_check_in.rooms:
            if room.room_no == self.room:
                check_in_dict['room'] = room.room_no
                check_in_dict['price'] = room.price

        # Geting Hotel Food Order Details
        total_food_discount = 0
        total_service_charges = 0
        food_order_list = []
        room_food_order_list = frappe.get_list('Hotel Food Order', filters={
            'status': 'To Check Out',
            'room': self.room,
            'check_in_id': self.check_in_id,
            'is_paid': 0
        })
        for food_order in room_food_order_list:
            food_order_dict = {}
            food_order_doc = frappe.get_doc('Hotel Food Order', food_order.name)
            food_order_dict['name'] = food_order_doc.name
            food_order_dict['date'] = food_order_doc.posting_date
            food_order_dict['order_type'] = food_order_doc.order_type
            food_order_dict['items'] = []
            total_service_charges += food_order_doc.service_charges
            total_food_discount += food_order_doc.discount_amount
            # Looping through items
            for item in food_order_doc.items:
                food_item_dict = {}
                food_item_dict['item'] = item.item
                food_item_dict['qty'] = item.qty
                food_item_dict['rate'] = item.rate
                food_item_dict['amount'] = item.amount
                food_order_dict['items'].append(food_item_dict)
            food_order_list.append(food_order_dict)

        # Getting Hotel Laundry Order Details
        laundry_order_list = []
        room_laundry_order_list = frappe.get_list('Hotel Laundry Order', filters={
            'status': 'To Check Out',
            'room': self.room,
            'check_in_id': self.check_in_id
        })
        for laundry_order in room_laundry_order_list:
            laundry_order_dict = {}
            laundry_order_doc = frappe.get_doc(
                'Hotel Laundry Order', laundry_order.name)
            laundry_order_dict['name'] = laundry_order_doc.name
            laundry_order_dict['date'] = laundry_order_doc.posting_date
            laundry_order_dict['order_type'] = laundry_order_doc.order_type
            laundry_order_dict['items'] = []
            # Looping through items
            for item in laundry_order_doc.items:
                laundry_item_dict = {}
                laundry_item_dict['item'] = item.item
                laundry_item_dict['qty'] = item.qty
                laundry_item_dict['rate'] = item.rate
                laundry_item_dict['amount'] = item.amount
                laundry_order_dict['items'].append(laundry_item_dict)
            laundry_order_list.append(laundry_order_dict)
        stay_days = frappe.utils.data.date_diff(self.check_out, self.check_in)

        # Getting Payments
        payment_entry_list = []
        room_payment_entry_list = frappe.get_list('Hotel Payment Entry',filters={
            'check_in_id' : self.check_in_id,
            'docstatus': 1,
            'room': self.room
        }, order_by='name asc')

        for payment in room_payment_entry_list:
            payment_entry_dict = {}
            payment_doc = frappe.get_doc('Hotel Payment Entry', payment)
            payment_entry_dict['payment_entry'] = payment_doc.name
            if payment_doc.entry_type == 'Receive':
                payment_entry_dict['amount_paid'] = payment_doc.amount_paid
            else:
                payment_entry_dict['amount_paid'] = -payment_doc.amount_paid
            payment_entry_dict['posting_date'] = payment_doc.posting_date
            payment_entry_list.append(payment_entry_dict)

        return [stay_days, check_in_dict, food_order_list, laundry_order_list, payment_entry_list, total_food_discount, total_service_charges]
