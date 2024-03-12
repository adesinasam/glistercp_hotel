# -*- coding: utf-8 -*-
# Copyright (c) 2024, Glistercp and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Rooms(Document):
    def after_save(self):
        self.create_or_update_item()

    def create_or_update_item(self):
        if frappe.db.exists('Item', {'item_code': self.room_number}):
            # If the Room Type exists, update the item
            existing_item = frappe.get_doc('Item', {'item_code': self.room_number})
            existing_item.item_name = self.room_name
            existing_item.item_group = self.room_type
            existing_item.standard_rate = self.price
            existing_item.save()
        else:
            # If the Room Type does not exist, create a new item
            new_item = frappe.new_doc('Item')
            new_item.item_code = self.room_number
            new_item.item_name = self.room_name
            new_item.item_group = self.room_type
            new_item.standard_rate = self.price
            new_item.is_stock_item = 0  # Assuming rooms are not stock items
            new_item.insert()
