// Copyright (c) 2020, Glistercp and contributors
// For license information, please see license.txt

frappe.ui.form.on("Hotel Check In", {
  setup: function(frm) {
    // setting query for rooms to be visible in list
    frm.set_query('room_no','rooms', function (doc){
      return{
        filters: {
          room_status: 'Available'
        }
      }
    });
    // setting query for customers to be visible in list
    frm.set_query("customer", function(doc) {
      return {
        filters: {
          customer_group: "All Customer Groups"
        }
      };
    });
  },
  
  guest_id: function(frm){
    var image_html = '<img src="' + frm.doc.guest_photo_attachment + '">';
    $(frm.fields_dict['guest_photo'].wrapper).html(image_html);
    frm.refresh_field('guest_photo');
  },
  
  refresh: function(frm){  
    var image_html = '<img src="' + frm.doc.guest_photo_attachment + '">';
    $(frm.fields_dict['guest_photo'].wrapper).html(image_html);
    frm.refresh_field('guest_photo');
  },

  validate: function(frm){
    for (var i in frm.doc.rooms){
      if (frm.doc.rooms[i].male == 0 && frm.doc.rooms[i].female == 0 && frm.doc.rooms[i].children == 0){
        frappe.throw('Please Enter Guests Details for Room ' + frm.doc.rooms[i].room_no);
      }
    }
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
  },

  from_date: function(frm) {
    if (frm.doc.from_date < frappe.datetime.get_today()) {
      frm.doc.from_date = "";
      frm.refresh_fields();
      frappe.throw(__("You can not select past date"));
    }
    for (var i in doc.rooms) {
          doc.rooms[i].from_date = frm.doc.from_date;
          frm.refresh_field("rooms");
    }
    frm.refresh_field("rooms");
  },

  check_in: function(frm) {
    if (frm.doc.check_in < frappe.datetime.get_today()) {
      frm.doc.check_in = "";
      frm.refresh_fields();
      frappe.throw(__("You can not select past date"));
    }
  },

  to_date: function(frm) {
    if (frm.doc.to_date < frappe.datetime.get_today()) {
      frm.doc.to_date = "";
      frm.refresh_fields();
      frappe.throw(__("You can not select past date"));
    }
    frm.call('calculate_stay_days').then(r => {
      if (r.message) {
        if (r.message > -1) {
          var doc = frm.doc;
          var days = 0;
          if (r.message == 0) {
            days = 1;
          } else {
            days = r.message;
          }
          for (var i in doc.rooms) {
            if (doc.rooms[i].room_no) {
                doc.rooms[i].to_date = frm.doc.to_date;
                doc.rooms[i].qty = days;
                doc.rooms[i].amount = days * doc.rooms[i].price;
                frm.refresh_field("rooms");
            }
          }
          frm.doc.days = days;
          frm.refresh_field('days');
          frm.refresh_field('rooms');
          frm.trigger("total_amount");
        } else {
          frm.doc.to_date = undefined;
          frm.refresh_field("to_date");
          frappe.msgprint("To Date cannot be before From Date.");
        }
      }
    });
  },

  is_complimentary: function(frm){
    frm.doc.customer = "Room Complimentary";
    frm.refresh_field('customer');
  },

  discount: function(frm){
    var temp_discount = frm.doc.total_amount;
    if (is_complimentary = 1){
      frm.doc.discount = temp_discount;
    }
    frm.trigger("total");
  },

  total_amount: function(frm){
    var temp_amount_paid = 0;
    for (var i in frm.doc.rooms){
      if (frm.doc.rooms[i].price){
        temp_amount_paid += frm.doc.rooms[i].amt_paid;
      }
    }
    frm.doc.amount_paid = temp_amount_paid;

    var temp_total_amount = 0;
    for (var i in frm.doc.rooms){
      if (frm.doc.rooms[i].price){
        temp_total_amount += frm.doc.rooms[i].amount;
      }
    }
    frm.doc.total_amount = temp_total_amount;

    frm.doc.net_balance_amount = 0;
    var temp_net_balance_amount = temp_total_amount - frm.doc.discount - temp_amount_paid;
    if (temp_net_balance_amount > 0){
      frm.doc.net_balance_amount = temp_net_balance_amount;
    }

    frm.refresh_field('amount_paid');
    frm.refresh_field('total_amount');
    frm.refresh_field('net_balance_amount');
  },

  amount_paid: function(frm){
    frm.trigger("total");
  }

});

frappe.ui.form.on('Hotel Check In Room', {
  room_no: function(frm, cdt, cdn) {
    let count = 0;
    let row = frappe.get_doc(cdt, cdn)
    if (row.room_no){
      for(var i in frm.doc.rooms){
        if (frm.doc.rooms[i].room_no == row.room_no){
          count += 1;
        }
      }
      if (count>1){
        let alert = 'Room ' + row.room_no + ' already selected';
        row.room_no = undefined;
        row.room_type = undefined;
        row.price = undefined;
        frm.refresh_field('rooms')
        frappe.throw(alert)
      }
      else {
        frm.call('get_room_price',{room: row.room_no}).then( r => {
          row.price = r.message;
          // frappe.model.set_value(cdt, cdn, 'price', r.message);
          frm.refresh_field('rooms')
        });
        frm.call('calculate_stay_days').then( r => {
          row.qty = r.message;
          row.amount = r.message * row.price;
          frm.refresh_field('rooms')
        })
      }
    }
    frm.trigger('total_amount');
  },

  rooms_remove: function(frm) {
    frm.trigger('total_amount');
  },


  form_render: function(frm,cdt,cdn) {
     let item = locals[cdt][cdn]; 
     item.from_date = frm.doc.from_date;
     item.to_date = frm.doc.to_date;
     item.qty = frm.doc.days;
     frm.refresh_field('rooms');
  },

  from_date: function(doc, cdt, cdn) {
    var child = locals[cdt][cdn];
    if (child.from_date < frappe.datetime.get_today()) {
      child.from_date = "";
      cur_frm.refresh_fields();
      frappe.throw(__("You can not select past date"));
    }
  },
  to_date: function(doc, cdt, cdn) {
    var child = locals[cdt][cdn];
    if (child.to_date < child.from_date) {
      child.to_date = "";
      cur_frm.refresh_fields();
      frappe.throw(__("Invalid Check Out date"));
    }
  }
  // room_no: function(doc, cdt, cdn){
  //   var child = locals[cdt][cdn];
  //   frappe.call({
  //     method: 'hotel_management.hotel_management.doctype.hotel_booking.hotel_booking.get_bookings',
  //     args:{"start":child.from_date,
  //     "end": child.to_date,
  //     "room": child.room_no
  //   },
  //   callback: function(r){
  //     /*child.from_date = "";
  //     child.to_date = "";
  //     child.room_no = "";*/
  //     cur_frm.refresh_fields();
  //   }
  // });
  // }
})
