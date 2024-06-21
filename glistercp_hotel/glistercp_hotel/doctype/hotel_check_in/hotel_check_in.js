// Copyright (c) 2020, Glistercp and contributors
// For license information, please see license.txt
frappe.provide("glistercp_hotel.glistercp_hotel");

frappe.ui.form.on("Hotel Check In", {
  setup: function(frm) {
    // Set query for available rooms
    frm.set_query('room_no', 'rooms', function() {
      return {
        filters: {
          room_status: 'Available'
        }
      };
    });

    // Set query for all customer groups
    frm.set_query("customer", function() {
      return {
        filters: {
          customer_group: "All Customer Groups"
        }
      };
    });
  },

  guest_id: function(frm) {
    update_guest_photo(frm);
  },

  refresh: function(frm) {
    update_guest_photo(frm);
  },

  validate: function(frm) {
    validate_rooms(frm);
    validate_dates(frm);
  },

  from_date: function(frm) {
    validate_past_date(frm, 'from_date');
    update_rooms_dates(frm, 'from_date');
  },

  check_in: function(frm) {
    validate_past_date(frm, 'check_in');
  },

  to_date: function(frm) {
    validate_past_date(frm, 'to_date');
    calculate_stay_days_and_update(frm);
  },

  is_complimentary: function(frm) {
    update_customer(frm);
    frm.trigger("total_amount");
  },

  discount: function(frm) {
    frm.trigger("total_amount");
  },

  total_amount: function(frm) {
    update_total_amount(frm);
  },

  amount_paid: function(frm) {
    frm.trigger("total_amount");
  }
});

frappe.ui.form.on('Hotel Check In Room', {
  room_no: function(frm, cdt, cdn) {
    handle_room_selection(frm, cdt, cdn);
  },

  rooms_remove: function(frm) {
    frm.trigger('total_amount');
  },

  form_render: function(frm, cdt, cdn) {
    update_room_dates(frm, cdt, cdn);
  },

  from_date: function(doc, cdt, cdn) {
    validate_child_past_date(cdt, cdn, 'from_date');
  },

  to_date: function(doc, cdt, cdn) {
    validate_child_to_date(cdt, cdn);
  }
});

// Helper functions
function update_guest_photo(frm) {
  var image_html = '<img src="' + frm.doc.guest_photo_attachment + '">';
  $(frm.fields_dict['guest_photo'].wrapper).html(image_html);
  frm.refresh_field('guest_photo');
}

function validate_rooms(frm) {
  frm.doc.rooms.forEach(function(room) {
    if (!room.male && !room.female && !room.children) {
      frappe.throw('Please Enter Guests Details for Room ' + room.room_no);
    }
  });
}

function validate_dates(frm) {
  if (frm.doc.check_in < frm.doc.from_date) {
    frm.doc.check_in = "";
    frm.refresh_fields();
    frappe.throw(__("Check in cannot be before From Date"));
  }
  if (frm.doc.to_date < frm.doc.from_date) {
    frm.doc.to_date = "";
    frm.refresh_fields();
    frappe.throw(__("To Date cannot be before From Date"));
  }
}

function validate_past_date(frm, field) {
  if (frm.doc[field] < frappe.datetime.get_today()) {
    frm.doc[field] = "";
    frm.refresh_fields();
    frappe.throw(__("You cannot select a past date"));
  }
}

function update_rooms_dates(frm, field) {
  frm.doc.rooms.forEach(function(room) {
    room[field] = frm.doc[field];
  });
  frm.refresh_field("rooms");
}

function calculate_stay_days_and_update(frm) {
  frm.call('calculate_stay_days').then(r => {
    if (r.message >= 0) {
      var days = r.message || 1;
      frm.doc.rooms.forEach(function(room) {
        if (room.room_no) {
          room.to_date = frm.doc.to_date;
          room.qty = days;
          room.amount = days * room.price;
        }
      });
      frm.doc.days = days;
      frm.refresh_field('days');
      frm.refresh_field('rooms');
      frm.trigger("total_amount");
    } else {
      frm.doc.to_date = undefined;
      frm.refresh_field("to_date");
      frappe.msgprint("To Date cannot be before From Date.");
    }
  });
}

function update_customer(frm) {
  frm.doc.customer = frm.doc.is_complimentary ? "Room Complimentary" : "Hotel Walk In Customer";
  frm.refresh_field('customer');
}

function update_total_amount(frm) {
  if (frm.doc.is_complimentary) {
    frm.doc.discount = frm.doc.total_amount;
    frm.refresh_field('discount');
  }

  temp_total_amount = frm.doc.rooms.reduce((sum, room) => sum + (room.amount || 0), 0);
  temp_amount_paid = frm.doc.rooms.reduce((sum, room) => sum + (room.amt_paid || 0), 0);
  temp_net_balance_amount = Math.max(0, frm.doc.total_amount - frm.doc.discount - frm.doc.amount_paid);
  
  frm.set_value("total_amount", temp_total_amount);
  frm.set_value("amount_paid", temp_amount_paid);
  frm.set_value("net_balance_amount", temp_net_balance_amount);

  frm.refresh_field('total_amount');
  frm.refresh_field('amount_paid');
  frm.refresh_field('net_balance_amount');
}

function handle_room_selection(frm, cdt, cdn) {
  let row = frappe.get_doc(cdt, cdn);
  if (row.room_no) {
    let room_count = frm.doc.rooms.filter(room => room.room_no === row.room_no).length;
    if (room_count > 1) {
      let alert = 'Room ' + row.room_no + ' already selected';
      row.room_no = row.room_type = row.price = undefined;
      frm.refresh_field('rooms');
      frappe.throw(alert);   
    } else {
      update_room_price_and_qty(frm, row);
    }
  }
  frm.trigger('total_amount');
}

function update_room_price_and_qty(frm, row) {
  frm.call('get_room_price', { room: row.room_no }).then(r => {
    row.price = r.message;
    row.amount = r.message * row.qty;
    frappe.model.set_value(row.doctype, row.name, 'price', r.message);
    frm.refresh_field('price');
    frm.refresh_field('amount');
    frm.refresh_field('rooms');
  });
  // frm.call('calculate_stay_days').then(r => {
  //   row.qty = r.message;
  //   row.amount = r.message * row.price;
  //   frm.refresh_field('rooms');
  // });
}

function update_room_dates(frm, cdt, cdn) {
  let room = locals[cdt][cdn];
  room.from_date = frm.doc.from_date;
  room.to_date = frm.doc.to_date;
  room.qty = frm.doc.days;
  frm.refresh_field('rooms');
}

function validate_child_past_date(cdt, cdn, field) {
  var child = locals[cdt][cdn];
  if (child[field] < frappe.datetime.get_today()) {
    child[field] = "";
    cur_frm.refresh_fields();
    frappe.throw(__("You cannot select a past date"));
  }
}

function validate_child_to_date(cdt, cdn) {
  var child = locals[cdt][cdn];
  if (child.to_date < child.from_date) {
    child.to_date = "";
    cur_frm.refresh_fields();
    frappe.throw(__("Invalid Check Out date"));
  }
}
