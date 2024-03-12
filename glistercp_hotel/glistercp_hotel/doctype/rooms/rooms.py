# -*- coding: utf-8 -*-
# Copyright (c) 2024, Glistercp and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document

class Rooms(Document):
  def before_save(self):
    self.create_item()

  def on_save(self):
    pass

  def create_item(self):
  	if frappe.db.exists('Item', {'item_code': self.room_number}):
       	# If the Room Type exists, update the item_group_name
       	existing_item_name = frappe.get_doc('Item Group', {'item_group_name': self.room_number})
       	existing_item_name.item_name = self.room_name
       	existing_item_name.item_group = self.room_type
       	existing_item_name.save()
    else:
       	# If the Room Type does not exist, create a new document and insert it
       	item_name = frappe.new_doc('Item Group')
       	item_name.item_code = self.room_number
       	item_name.item_name = self.room_name
       	item_name.item_group = self.room_type
       	item_name.price = self.standard_rate
       	item_name.is_stock_item = 0
       	item_name.insert()
