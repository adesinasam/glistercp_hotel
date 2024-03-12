# -*- coding: utf-8 -*-
# Copyright (c) 2024, Glistercp and Contributors
# For license information, please see license.txt

from __future__ import unicode_literals
# import frappe
from frappe.model.document import Document

class RoomType(Document):
  def before_save(self):
    self.create_item_group()

  def on_save(self):
    pass

  def create_item_group(self):
  	if frappe.db.exists('Item Group', {'item_group_name': self.type}):
       	# If the Room Type exists, update the item_group_name
       	existing_item_group_name = frappe.get_doc('Item Group', {'item_group_name': self.type})
       	existing_item_group_name.item_group_name = self.type
       	existing_item_group_name.save()
    else:
       	# If the Room Type does not exist, create a new document and insert it
       	item_group = frappe.new_doc('Item Group')
       	item_group.item_group_name = self.type
       	item_group.parent_item_group = "All Item Groups"
       	item_group_name.insert()

  
