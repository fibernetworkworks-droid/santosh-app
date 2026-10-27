"""v0.131 The data model for a complex app: entities picked by the app's modules, written in a small field language, turned
into a robust relational schema:

  * every table: id uuid (made on the phone = offline-safe, UUIDv7 recommended), tenant_id, created_at / created_by,
    updated_at / updated_by, deleted_at (soft delete = sync tombstone), version (optimistic locking / conflict check);
    append-only tables (audit log, telemetry, location pings, stock moves, payments) keep only created_*;
  * org-scoped tables carry org_unit_id; PostgreSQL row-level security keeps each tenant (and each person's units) apart;
  * foreign keys indexed, unique keys per tenant, enum CHECKs, money as numeric(14,2), geo as PostGIS geography (or plain
    lat / lng + GeoJSON without PostGIS), ID / bank numbers only encrypted with a last-4 copy;
  * N:M as join tables; (tenant_id, updated_at) index on every table for delta sync.

Outputs: PostgreSQL DDL (server), SQLite DDL (the phone's Room database), Kotlin Room entities, a Mermaid erDiagram, an
ER page (cards per table grouped by module) and the checks (every FK has a target and an index, names <= 63 characters, no
reserved words, every table has a primary key, no orphan join)."""
from __future__ import annotations

import copy
import html
import re
from typing import Any

# field language: "name type[!][*][~]" ; ! = required, * = unique per tenant, ~ = indexed
# types: text long int decimal money bool date datetime time phone email url uuid json file pii enum(a,b) ref(entity)
#        many(entity) point line polygon
# entity options: o = org-scoped (org_unit_id), a = append-only, s = sensitive (screens block screenshots, views logged)
E = dict[str, tuple[str, str, str, str]]          # entity -> (module, label, fields, opts)

ENTITIES: E = {
    # ------------------------------------------------------------ core (every app)
    "org_unit": ("core", "Org unit", "name text!, code text*, level int!, parent ref(org_unit)~, address long, location point, "
                 "manager ref(app_user)", ""),
    "app_user": ("core", "User", "name text!, phone phone*, email email*, employee_code text*, org_unit ref(org_unit)!, "
                 "status enum(invited,active,suspended,left)!, photo file, last_seen datetime, language text", "o"),
    "role": ("core", "Role", "code text!*, label text!, base enum(super_admin,admin,manager,supervisor,staff,field,customer,auditor,"
             "viewer)!, approve_limit money", ""),
    "user_role": ("core", "User role", "user ref(app_user)!, role ref(role)!, org_unit ref(org_unit)!, valid_until date", "o"),
    "permission": ("core", "Permission", "role ref(role)!, module text!, action enum(read,create,update,delete,approve,export)!, "
                   "scope enum(none,own,unit,parent,all)!", ""),
    "device": ("core", "Device", "user ref(app_user)!, name text, platform enum(android,ios,web)!, push_token text, "
               "key_id text, trusted bool, last_seen datetime", ""),
    "user_session": ("core", "Session", "user ref(app_user)!, device ref(device), refresh_hash text!*, expires_at datetime!, "
                     "revoked_at datetime", ""),
    "audit_log": ("core", "Audit log", "actor ref(app_user)~, action text!, entity text!~, record_id uuid~, before json, "
                  "after json, device ref(device)", "a"),
    "file_obj": ("core", "File", "name text!, mime text, size int, storage_key text!*, sha256 text~, entity text, record_id uuid~", "o"),
    "notification": ("core", "Notification", "user ref(app_user)!, kind text!, title text!, body long, entity text, record_id uuid, "
                     "read_at datetime", ""),
    "setting": ("core", "Setting", "key text!*, value json", ""),
    "invite": ("core", "Invite", "phone phone, email email, role ref(role)!, org_unit ref(org_unit)!, code_hash text!*, "
               "expires_at datetime!, accepted_by ref(app_user)", "o"),
    "sync_conflict": ("core", "Sync conflict", "entity text!, record_id uuid!~, mine json, theirs json, "
                      "status enum(open,kept_mine,kept_theirs,merged)!, resolved_by ref(app_user)", ""),
    # ------------------------------------------------------------ approvals
    "approval_rule": ("approvals", "Approval rule", "module text!, kind text!, min_amount money, max_amount money, step int!, "
                      "approver_role ref(role)!, sla_hours int", ""),
    "approval_request": ("approvals", "Approval request", "module text!, kind text!, entity text!, record_id uuid!~, "
                         "amount money, requested_by ref(app_user)!, status enum(pending,approved,rejected,cancelled)!, "
                         "current_step int!, note long", "o"),
    "approval_step": ("approvals", "Approval step", "request ref(approval_request)!, step int!, approver ref(app_user), "
                      "decision enum(pending,approved,rejected,info)!, comment long, decided_at datetime", ""),
    "delegation": ("approvals", "Delegation", "from_user ref(app_user)!, to_user ref(app_user)!, starts date!, ends date!, "
                   "modules json", ""),
    # ------------------------------------------------------------ crm
    "customer": ("crm", "Customer", "name text!, phone phone~, email email, gstin text, address long, location point, "
                 "segment text, credit_limit money, owner ref(app_user)~, tags json", "o"),
    "contact": ("crm", "Contact person", "customer ref(customer)!, name text!, phone phone, email email, designation text", "o"),
    "lead": ("crm", "Lead", "name text!, phone phone~, email email, source enum(walk_in,website,call,whatsapp,referral,portal,ads,"
             "event,other)!, stage enum(new,contacted,qualified,proposal,won,lost)!, value money, owner ref(app_user)~, "
             "next_at datetime~, lost_reason text, customer ref(customer), location point", "o"),
    "deal": ("crm", "Deal", "customer ref(customer)!, title text!, stage enum(open,proposal,negotiation,won,lost)!, value money, "
             "probability int, close_on date, owner ref(app_user)~", "o"),
    "activity": ("crm", "Activity", "kind enum(call,visit,email,whatsapp,meeting,note)!, lead ref(lead)~, customer ref(customer)~, "
                 "by_user ref(app_user)!, at datetime!, outcome text, note long", "oa"),
    "quote": ("crm", "Quotation", "number text!*, customer ref(customer)!, deal ref(deal), status enum(draft,pending,sent,accepted,"
              "rejected,expired)!, valid_until date, subtotal money, discount money, tax money, total money!", "o"),
    "quote_line": ("crm", "Quotation line", "quote ref(quote)!, item ref(item), description text!, qty decimal!, rate money!, "
                   "discount_pct decimal, tax_pct decimal, amount money!", ""),
    # ------------------------------------------------------------ sales, billing, payments
    "item": ("sales", "Item / product", "name text!, sku text*, barcode text*, hsn text, unit text!, price money!, tax_pct decimal, "
             "category text~, active bool, image file", ""),
    "price_list": ("sales", "Price list", "name text!, customer_group text, starts date, ends date", ""),
    "price_list_item": ("sales", "Price list item", "price_list ref(price_list)!, item ref(item)!, price money!, min_qty decimal", ""),
    "sales_order": ("sales", "Order", "number text!*, customer ref(customer)!, status enum(draft,confirmed,packed,dispatched,"
                    "delivered,cancelled)!, ordered_by ref(app_user), total money!, need_by date, address long, location point", "o"),
    "order_line": ("sales", "Order line", "order_id ref(sales_order)!, item ref(item)!, qty decimal!, rate money!, tax_pct decimal, "
                   "amount money!", ""),
    "invoice": ("sales", "Invoice", "number text!*, customer ref(customer)!, order_id ref(sales_order), date date!, "
                "status enum(draft,issued,part_paid,paid,cancelled)!, place_of_supply text, irn text, subtotal money, "
                "cgst money, sgst money, igst money, total money!, due_on date", "o"),
    "invoice_line": ("sales", "Invoice line", "invoice ref(invoice)!, item ref(item), description text!, hsn text, qty decimal!, "
                     "rate money!, tax_pct decimal, amount money!", ""),
    "payment": ("sales", "Payment received", "number text!*, customer ref(customer)~, invoice ref(invoice)~, amount money!, "
                "mode enum(upi,cash,cheque,bank,card_gateway,other)!, ref_tail text, received_by ref(app_user), at datetime!, "
                "status enum(claimed,confirmed,bounced,refunded)!", "oa"),
    # ------------------------------------------------------------ inventory
    "warehouse": ("inventory", "Warehouse / godown", "name text!, code text*, address long, location point", "o"),
    "bin": ("inventory", "Bin / rack", "warehouse ref(warehouse)!, code text!, capacity decimal", ""),
    "stock": ("inventory", "Stock", "item ref(item)!, warehouse ref(warehouse)!, bin ref(bin), batch ref(batch), qty decimal!, "
              "reserved decimal, reorder_at decimal", "o"),
    "batch": ("inventory", "Batch / lot", "item ref(item)!, code text!, made_on date, expires_on date~, mrp money", ""),
    "serial_no": ("inventory", "Serial number", "item ref(item)!, serial text!*, warehouse ref(warehouse), "
                  "status enum(in_stock,issued,installed,returned,faulty)!, customer ref(customer)", ""),
    "stock_move": ("inventory", "Stock movement", "item ref(item)!, from_wh ref(warehouse), to_wh ref(warehouse), batch ref(batch), "
                   "qty decimal!, kind enum(receipt,issue,transfer,adjust,sale,return,count)!, reason text, ref_entity text, "
                   "ref_id uuid, by_user ref(app_user)", "oa"),
    "stock_count": ("inventory", "Stock count", "warehouse ref(warehouse)!, status enum(open,submitted,approved)!, "
                    "counted_by ref(app_user), blind bool", "o"),
    "stock_count_line": ("inventory", "Count line", "count ref(stock_count)!, item ref(item)!, expected decimal, counted decimal!, "
                         "bin ref(bin)", ""),
    # ------------------------------------------------------------ purchase
    "supplier": ("purchase", "Supplier", "name text!, phone phone, email email, gstin text, address long, msme bool, "
                 "payment_days int", ""),
    "purchase_order": ("purchase", "Purchase order", "number text!*, supplier ref(supplier)!, status enum(draft,pending,approved,"
                       "sent,part_received,received,cancelled)!, total money!, need_by date", "o"),
    "po_line": ("purchase", "PO line", "po ref(purchase_order)!, item ref(item)!, qty decimal!, rate money!, tax_pct decimal, "
                "amount money!", ""),
    "goods_receipt": ("purchase", "Goods receipt", "number text!*, po ref(purchase_order), supplier ref(supplier)!, "
                      "warehouse ref(warehouse)!, received_on date!, note long", "o"),
    "grn_line": ("purchase", "Receipt line", "receipt ref(goods_receipt)!, item ref(item)!, qty decimal!, damaged decimal, "
                 "batch ref(batch)", ""),
    # ------------------------------------------------------------ hr
    "employee": ("hr", "Employee", "user ref(app_user)*, code text!*, name text!, designation text, department text, "
                 "joined_on date, manager ref(employee), pan pii, bank_account pii, uan text, status enum(active,notice,left)!", "os"),
    "attendance": ("hr", "Attendance", "employee ref(employee)!, day date!~, in_at datetime, out_at datetime, in_point point, "
                   "out_point point, inside_fence bool, selfie file, status enum(present,absent,half_day,leave,holiday,week_off)!, "
                   "late_min int", "o"),
    "leave_type": ("hr", "Leave type", "code text!*, label text!, days_per_year decimal, carry_forward bool, paid bool", ""),
    "leave_request": ("hr", "Leave request", "employee ref(employee)!, leave_type ref(leave_type)!, starts date!, ends date!, "
                      "half_day bool, reason long, status enum(pending,approved,rejected,cancelled)!", "o"),
    "shift": ("hr", "Shift", "name text!, starts time!, ends time!, grace_min int", ""),
    "roster": ("hr", "Roster", "employee ref(employee)!, shift ref(shift)!, day date!~", "o"),
    "payslip": ("hr", "Payslip", "employee ref(employee)!, month text!~, gross money!, deductions money!, net money!, file file", "os"),
    "expense_claim": ("hr", "Expense claim", "employee ref(employee)!, category text!, amount money!, spent_on date!, receipt file, "
                      "km decimal, status enum(draft,pending,approved,rejected,paid)!", "o"),
    # ------------------------------------------------------------ tasks, projects, checklists
    "project": ("tasks", "Project", "name text!, code text*, starts date, ends date, status enum(planned,active,on_hold,done)!, "
                "owner ref(app_user)", "o"),
    "task": ("tasks", "Task", "title text!, project ref(project)~, assignee ref(app_user)~, due_at datetime~, "
             "priority enum(low,normal,high,urgent)!, status enum(todo,doing,review,done,cancelled)!, parent ref(task), "
             "location point, estimate_h decimal", "o"),
    "task_dependency": ("tasks", "Task dependency", "task ref(task)!, depends_on ref(task)!", ""),
    "comment": ("tasks", "Comment", "entity text!, record_id uuid!~, by_user ref(app_user)!, body long!", "a"),
    "checklist_template": ("tasks", "Checklist template", "name text!, kind text, items json!", ""),
    "checklist_run": ("tasks", "Checklist run", "template ref(checklist_template)!, entity text, record_id uuid~, "
                      "by_user ref(app_user)!, score decimal, status enum(open,submitted,approved)!, location point, "
                      "signature file", "o"),
    "checklist_answer": ("tasks", "Checklist answer", "run ref(checklist_run)!, item_key text!, result enum(pass,fail,na)!, "
                         "value text, photo file, note text", ""),
    "timesheet": ("tasks", "Timesheet entry", "user ref(app_user)!, task ref(task), project ref(project), day date!~, hours decimal!, "
                  "status enum(draft,submitted,approved)!", "o"),
    # ------------------------------------------------------------ service, tickets, assets
    "asset": ("service", "Asset", "name text!, tag text*, kind text~, customer ref(customer), serial ref(serial_no), "
              "location point, installed_on date, warranty_until date, status enum(active,faulty,retired)!", "o"),
    "sla_policy": ("service", "SLA policy", "name text!, priority enum(low,normal,high,urgent)!, respond_min int!, resolve_min int!", ""),
    "ticket": ("service", "Ticket", "number text!*, customer ref(customer)~, asset ref(asset), title text!, category text~, "
               "priority enum(low,normal,high,urgent)!, status enum(new,assigned,in_progress,on_hold,resolved,closed)!, "
               "assignee ref(app_user)~, sla ref(sla_policy), due_at datetime~, source enum(app,phone,whatsapp,email,web,system)!, "
               "location point", "o"),
    "work_order": ("service", "Work order", "number text!*, ticket ref(ticket), asset ref(asset), customer ref(customer), "
                   "technician ref(app_user)~, window_start datetime, window_end datetime, status enum(assigned,travelling,"
                   "on_site,done,cancelled)!, started_at datetime, done_at datetime, signature file, location point", "o"),
    "part_used": ("service", "Part used", "work_order ref(work_order)!, item ref(item)!, qty decimal!, serial ref(serial_no)", ""),
    "kb_article": ("service", "Help article", "title text!, body long!, category text, tags json", ""),
    # ------------------------------------------------------------ field, visits, location
    "visit": ("field", "Visit", "user ref(app_user)!, customer ref(customer)~, planned_at datetime, in_at datetime, out_at datetime, "
              "in_point point, distance_m int, outcome text, photo file, status enum(planned,done,missed,cancelled)!", "o"),
    "route": ("field", "Route / beat", "name text!, user ref(app_user), day enum(mon,tue,wed,thu,fri,sat,sun), path line", "o"),
    "route_stop": ("field", "Route stop", "route ref(route)!, seq int!, customer ref(customer), point point, time_window text", ""),
    "location_ping": ("field", "Location ping (duty only)", "user ref(app_user)!~, at datetime!, point point!, accuracy_m int, "
                      "battery int, on_duty bool!", "a"),
    "geofence": ("field", "Geofence", "name text!, org_unit ref(org_unit), area polygon!, radius_m int, purpose enum(attendance,"
                 "alert,patrol)!", "o"),
    # ------------------------------------------------------------ gis
    "map_layer": ("gis", "Map layer", "name text!, kind enum(point,line,polygon)!, style json, visible bool, source text", ""),
    "feature": ("gis", "Map feature", "layer ref(map_layer)!, code text~, name text, geom_point point, geom_line line, "
                "geom_area polygon, props json, status text", "o"),
    "survey_form": ("gis", "Survey form", "name text!, form_version int!, schema json!", ""),
    "survey_response": ("gis", "Survey response", "form ref(survey_form)!, by_user ref(app_user)!, point point, feature ref(feature), "
                        "answers json!, photos json, status enum(draft,queued,submitted,approved,rejected)!", "o"),
    "measurement": ("gis", "Measurement", "name text, geom_line line, geom_area polygon, length_m decimal, area_sqm decimal, "
                    "by_user ref(app_user)", "o"),
    "offline_area": ("gis", "Offline map area", "name text!, bounds polygon!, zoom_max int, size_mb decimal", ""),
    # ------------------------------------------------------------ logistics
    "vehicle": ("logistics", "Vehicle", "number text!*, kind text, capacity_kg decimal, rc_until date, insurance_until date~, "
                "fitness_until date, permit_until date, puc_until date, status enum(active,repair,retired)!", "o"),
    "driver": ("logistics", "Driver", "user ref(app_user)*, name text!, phone phone, licence_until date~", "o"),
    "trip": ("logistics", "Trip", "number text!*, vehicle ref(vehicle)~, driver ref(driver)~, starts_at datetime, ends_at datetime, "
             "status enum(planned,loading,on_road,delivered,closed,cancelled)!, km decimal, path line", "o"),
    "trip_stop": ("logistics", "Trip stop", "trip ref(trip)!, seq int!, order_id ref(sales_order), customer ref(customer), "
                  "point point, eta datetime, status enum(pending,arrived,done,failed,skipped)!", ""),
    "delivery": ("logistics", "Delivery", "stop ref(trip_stop)!, receiver text, photo file, signature file, otp_ok bool, "
                 "cod_amount money, failed_reason text, at datetime", "a"),
    "fuel_entry": ("logistics", "Fuel entry", "vehicle ref(vehicle)!, litres decimal!, amount money!, odometer int!, bill file, "
                   "at datetime!", "oa"),
    # ------------------------------------------------------------ comms
    "chat": ("comms", "Chat", "kind enum(direct,group,record)!, title text, entity text, record_id uuid", "o"),
    "chat_member": ("comms", "Chat member", "chat ref(chat)!, user ref(app_user)!, muted bool, last_read_at datetime", ""),
    "message": ("comms", "Message", "chat ref(chat)!~, by_user ref(app_user)!, body long, file file, reply_to ref(message)", "a"),
    "announcement": ("comms", "Notice", "title text!, body long!, audience json, pinned bool, needs_ack bool, by_user ref(app_user)", "o"),
    "announcement_ack": ("comms", "Notice read", "announcement ref(announcement)!, user ref(app_user)!, at datetime!", "a"),
    "poll": ("comms", "Poll", "question text!, options json!, closes_at datetime, anonymous bool", "o"),
    "poll_vote": ("comms", "Poll vote", "poll ref(poll)!, user ref(app_user), option_key text!", "a"),
    # ------------------------------------------------------------ reports
    "report_def": ("reports", "Report", "name text!, module text!, query json!, chart json, owner ref(app_user)", ""),
    "report_schedule": ("reports", "Report schedule", "report ref(report_def)!, cron text!, to_roles json, format enum(pdf,xlsx,csv)!", ""),
    "export_job": ("reports", "Export", "report ref(report_def), what text!, format enum(pdf,xlsx,csv)!, rows int, file file, "
                   "status enum(waiting_approval,running,ready,failed)!, by_user ref(app_user)!", "o"),
    # ------------------------------------------------------------ health (staff only, role-limited)
    "patient": ("health", "Patient", "mrn text!*, name text!, phone phone~, sex enum(female,male,other), birth_date date, "
                "abha_address text, allergies long, guardian text", "os"),
    "encounter": ("health", "Visit / admission", "patient ref(patient)!, doctor ref(app_user)!, kind enum(opd,ipd,emergency,tele)!, "
                  "starts_at datetime!, ends_at datetime, ward text, bed text, notes long, status enum(open,closed)!", "os"),
    "prescription": ("health", "Prescription", "encounter ref(encounter)!, items json!, advice long, by_doctor ref(app_user)!", "os"),
    "lab_order": ("health", "Lab order", "patient ref(patient)!, encounter ref(encounter), tests json!, sample_barcode text*, "
                  "collected_at datetime, status enum(ordered,collected,processing,reported,cancelled)!", "os"),
    "lab_result": ("health", "Lab result", "lab_order ref(lab_order)!, test text!, value text!, unit text, ref_range text, "
                   "flag enum(normal,low,high,critical), approved_by ref(app_user)", "os"),
    "consent_record": ("health", "Consent", "patient ref(patient)!, purpose text!, given bool!, given_at datetime!, "
                       "withdrawn_at datetime, file file", "osa"),
    # ------------------------------------------------------------ education
    "student": ("education", "Student", "admission_no text!*, name text!, birth_date date, class_section ref(class_section)~, "
                "guardian ref(guardian), photo file, status enum(active,left,passed_out)!", "os"),
    "guardian": ("education", "Parent / guardian", "name text!, phone phone!~, email email, user ref(app_user)", "o"),
    "class_section": ("education", "Class / section", "grade text!, section text!, class_teacher ref(app_user), year text!", "o"),
    "class_attendance": ("education", "Class attendance", "class_section ref(class_section)!, student ref(student)!, day date!~, "
                         "period int, status enum(present,absent,late,leave)!, by_user ref(app_user)", "o"),
    "exam": ("education", "Exam / test", "name text!, class_section ref(class_section)!, subject text!, max_marks decimal!, on_date date", "o"),
    "mark": ("education", "Marks", "exam ref(exam)!, student ref(student)!, marks decimal, grade text, remark text", "o"),
    "fee_plan": ("education", "Fee plan", "name text!, class_section ref(class_section), amount money!, instalments json", ""),
    "fee_due": ("education", "Fee due", "student ref(student)!, fee_plan ref(fee_plan)!, due_on date!~, amount money!, paid money, "
                "status enum(due,part_paid,paid,waived)!", "o"),
    # ------------------------------------------------------------ iot
    "device_node": ("iot", "Device", "name text!, serial text*, mac text*, kind text~, model text, firmware text, site ref(feature), "
                    "parent ref(device_node), location point, status enum(online,offline,alarm,maintenance)!, last_seen datetime", "o"),
    "telemetry": ("iot", "Reading", "device ref(device_node)!~, at datetime!~, metric text!, value decimal!", "a"),
    "alarm": ("iot", "Alarm", "device ref(device_node)!, severity enum(info,minor,major,critical)!, code text!, message text, "
              "raised_at datetime!, cleared_at datetime, acked_by ref(app_user), ticket ref(ticket)", "o"),
    "command": ("iot", "Command", "device ref(device_node)!, name text!, params json, by_user ref(app_user)!, "
                "status enum(pending,sent,done,failed,refused)!, result text", "oa"),
    # ------------------------------------------------------------ isp / ftth
    "plan_package": ("isp", "Internet plan", "name text!, speed_mbps int!, price money!, validity_days int!, data_gb int", ""),
    "subscriber": ("isp", "Subscriber", "account_no text!*, customer ref(customer)!, plan ref(plan_package)~, "
                   "status enum(lead,active,suspended,disconnected)!, renews_on date~, address long, location point", "o"),
    "olt": ("isp", "OLT", "name text!, ip text, vendor text, site ref(feature), pon_ports int, status enum(up,down,degraded)!", "o"),
    "pon_port": ("isp", "PON port", "olt ref(olt)!, port text!, splitter text, onts int", ""),
    "ont": ("isp", "ONT / router", "serial text!*, mac text*, subscriber ref(subscriber)~, pon ref(pon_port)~, rx_dbm decimal, "
            "tx_dbm decimal, status enum(online,offline,los,dying_gasp)!, last_seen datetime", "o"),
    "fiber_route": ("isp", "Fiber route", "name text!, cores int, path line!, from_feature ref(feature), to_feature ref(feature), "
                    "length_m decimal", "o"),
    # ------------------------------------------------------------ hospitality
    "room": ("hospitality", "Room", "number text!*, kind text!, floor text, rate money!, status enum(free,booked,occupied,dirty,"
             "maintenance)!", "o"),
    "room_booking": ("hospitality", "Room booking", "room ref(room)!, guest ref(customer)!, check_in date!~, check_out date!, "
                     "guests int, status enum(booked,checked_in,checked_out,cancelled,no_show)!, total money", "o"),
    "housekeeping_task": ("hospitality", "Housekeeping task", "room ref(room)!, by_user ref(app_user), kind enum(clean,deep_clean,"
                          "turn_down,inspect)!, status enum(todo,doing,done,inspected)!", "o"),
    # ------------------------------------------------------------ society
    "unit": ("society", "Flat / unit", "code text!*, wing text, floor text, area_sqft decimal, owner_name text", "o"),
    "resident": ("society", "Resident", "unit ref(unit)!, user ref(app_user), name text!, phone phone, kind enum(owner,tenant,family)!", "o"),
    "maintenance_bill": ("society", "Maintenance bill", "unit ref(unit)!, month text!~, amount money!, due_on date!, paid money, "
                         "status enum(due,part_paid,paid)!", "o"),
    "visitor_pass": ("society", "Visitor pass", "unit ref(unit)!, name text!, phone phone, valid_from datetime!, valid_to datetime!, "
                     "code_hash text!*, used_at datetime", "o"),
    # ------------------------------------------------------------ agri / dairy
    "farmer": ("agri", "Farmer", "member_no text!*, name text!, phone phone~, village text~, user ref(app_user)", "os"),
    "plot": ("agri", "Plot / farm", "farmer ref(farmer)!, survey_no text, area polygon, area_acres decimal, soil text", "o"),
    "crop_season": ("agri", "Crop season", "plot ref(plot)!, crop text!, season enum(kharif,rabi,zaid,perennial)!, sown_on date, "
                    "expected_harvest date", "o"),
    "procurement": ("agri", "Procurement", "farmer ref(farmer)!, crop text!, qty_kg decimal!, rate money!, grade text, amount money!, "
                    "at datetime!", "oa"),
    "input_issue": ("agri", "Input issue", "farmer ref(farmer)!, item ref(item)!, qty decimal!, amount money!, on_credit bool", "oa"),
    "milk_collection": ("dairy", "Milk collection", "member ref(farmer)!, shift enum(morning,evening)!, day date!~, litres decimal!, "
                        "fat decimal!, snf decimal!, rate money!, amount money!", "oa"),
    "rate_chart": ("dairy", "Rate chart", "name text!, starts date!, rows json!", ""),
    # ------------------------------------------------------------ finance
    "ledger_account": ("finance", "Ledger", "code text!*, name text!, kind enum(asset,liability,income,expense,equity)!, "
                       "parent ref(ledger_account)", ""),
    "journal": ("finance", "Journal entry", "number text!*, date date!~, narration long, source_entity text, source_id uuid, "
                "posted_by ref(app_user)", "oa"),
    "journal_line": ("finance", "Journal line", "journal ref(journal)!, account ref(ledger_account)!, debit money, credit money", "a"),
    "expense": ("finance", "Expense", "account ref(ledger_account)!, amount money!, spent_on date!, vendor ref(supplier), bill file, "
                "status enum(draft,pending,approved,paid)!", "o"),
    "budget": ("finance", "Budget", "account ref(ledger_account)!, month text!, amount money!", "o"),
    # ------------------------------------------------------------ events
    "event": ("events", "Event", "name text!, starts_at datetime!, ends_at datetime, venue text, location point, capacity int", "o"),
    "ticket_type": ("events", "Ticket type", "event ref(event)!, name text!, price money, quota int", ""),
    "pass_ticket": ("events", "Pass", "event ref(event)!, ticket_type ref(ticket_type)!, holder text!, phone phone, "
                    "code_hash text!*, status enum(valid,used,cancelled)!", "o"),
    "checkin": ("events", "Check-in", "pass ref(pass_ticket)!, gate text, by_user ref(app_user)!, at datetime!, offline bool", "a"),
    # ------------------------------------------------------------ v0.138 product apps: media, social, personal, market
    "media_artist": ("media", "Artist / creator", "name text!, bio long, photo file, verified bool", ""),
    "media_album": ("media", "Album / show", "title text!, artist ref(media_artist)~, kind enum(album,single,ep,show,season,podcast,"
                    "audiobook,series)!, cover file, released_on date, language text~", ""),
    "media_item": ("media", "Song / episode / video", "title text!, kind enum(song,episode,movie,clip,podcast_episode,chapter,lesson)!, "
                   "artist ref(media_artist)~, album ref(media_album)~, duration_s int, media file!, cover file, language text~, "
                   "genre text~, age_rating enum(u,ua7,ua13,ua16,a), explicit bool, licence_note text, released_on date", ""),
    "playlist": ("media", "Playlist", "name text!, owner ref(app_user)~, public bool, cover file", ""),
    "playlist_item": ("media", "Playlist item", "playlist ref(playlist)!~, item ref(media_item)!, position int!", ""),
    "play_event": ("media", "Play", "item ref(media_item)!~, by_user ref(app_user)~, seconds int, device ref(device), at datetime!", "a"),
    "watch_progress": ("media", "Continue watching", "by_user ref(app_user)!~, item ref(media_item)!, position_s int!, finished bool", ""),
    "media_download": ("media", "Download", "by_user ref(app_user)!~, item ref(media_item)!, device ref(device)!, expires_at datetime", ""),
    "subscription": ("media", "Subscription", "by_user ref(app_user)!~, plan text!, status enum(trial,active,grace,cancelled,expired)!, "
                     "store enum(play,app_store,web)!, renews_at datetime, store_token_hash text*", ""),
    "viewer_profile": ("media", "Viewer profile", "owner ref(app_user)!~, name text!, kids bool, max_rating enum(u,ua7,ua13,ua16,a), "
                       "pin_set bool", ""),
    "post": ("social", "Post", "by_user ref(app_user)!~, kind enum(photo,video,text,reel,story)!, caption long, media file, "
             "visibility enum(public,followers,private)!, ai_label bool, expires_at datetime", ""),
    "post_reaction": ("social", "Reaction", "post ref(post)!~, by_user ref(app_user)!, kind enum(like,love,laugh,wow)!", "a"),
    "post_comment": ("social", "Comment", "post ref(post)!~, by_user ref(app_user)!, body long!, reply_to ref(post_comment)", ""),
    "user_follow": ("social", "Follow", "follower ref(app_user)!~, following ref(app_user)!~, status enum(active,requested,blocked)!", ""),
    "content_report": ("social", "Report", "entity text!, record_id uuid!~, by_user ref(app_user), reason enum(spam,abuse,nudity,"
                       "violence,hate,fake,copyright,child_safety,other)!, status enum(open,actioned,dismissed)!, acted_at datetime, "
                       "note long", ""),
    "user_block": ("social", "Block", "by_user ref(app_user)!~, blocked ref(app_user)!", ""),
    "hashtag": ("social", "Hashtag", "tag text!*, uses int", ""),
    "note": ("personal", "Note", "title text, body long, pinned bool, colour text, reminder_at datetime", ""),
    "todo_item": ("personal", "To-do", "title text!, done bool, due_on date, priority enum(low,normal,high), list_name text~", ""),
    "habit": ("personal", "Habit", "name text!, target_per_week int, reminder_at time, colour text", ""),
    "habit_log": ("personal", "Habit tick", "habit ref(habit)!~, day date!, done bool", "a"),
    "expense": ("personal", "Expense", "amount money!, category text!~, spent_on date!, note text, paid_by text, group_name text~", ""),
    "budget": ("personal", "Budget", "category text!, month text!, limit_amount money!", ""),
    "workout_log": ("personal", "Workout", "kind text!, minutes int, calories int, distance_km decimal, at datetime!", "a"),
    "store": ("market", "Store / restaurant", "name text!, kind text~, location point, address long, open_now bool, rating decimal, "
              "fssai text, gstin text", "o"),
    "ride": ("market", "Ride", "rider ref(app_user)!~, driver ref(app_user)~, pickup point!, dropoff point!, pickup_text text, "
             "dropoff_text text, status enum(searching,accepted,arriving,on_trip,completed,cancelled)!, fare money, otp_hash text, "
             "sos bool", ""),
    "listing": ("market", "Listing / ad", "by_user ref(app_user)!~, title text!, price money, category text~, location point, "
                "photos json, status enum(active,sold,removed)!", ""),
    "job_post": ("market", "Job", "title text!, company text!, place text~, salary_min money, salary_max money, "
                 "kind enum(full_time,part_time,internship,contract,gig)!, status enum(open,closed)!", "o"),
    "job_application": ("market", "Application", "job ref(job_post)!~, applicant ref(app_user)!, resume file, "
                        "status enum(applied,shortlisted,interview,offer,rejected)!", ""),
}

MODULES: dict[str, str] = {
    "core": "Users, roles, units, devices, audit", "approvals": "Approval chains", "crm": "Leads, customers, quotes",
    "sales": "Items, orders, invoices, payments", "inventory": "Stock, godowns, batches, serials", "purchase": "Suppliers, POs, receipts",
    "hr": "Employees, attendance, leave, payslips", "tasks": "Projects, tasks, checklists, time", "service": "Tickets, work orders, assets",
    "field": "Visits, routes, duty location, geofences", "gis": "Layers, features, surveys, measurements",
    "logistics": "Vehicles, trips, deliveries", "comms": "Chats, notices, polls", "reports": "Reports and exports",
    "health": "Patients, visits, labs (sensitive)", "education": "Students, classes, marks, fees", "iot": "Devices, readings, alarms",
    "isp": "Plans, subscribers, OLT / PON / ONT, fiber", "hospitality": "Rooms, bookings, housekeeping",
    "society": "Units, residents, bills, visitor passes", "agri": "Farmers, plots, crops, procurement", "dairy": "Milk collection",
    "finance": "Ledgers, journals, expenses, budgets", "events": "Events, passes, check-ins",
    "media": "Songs, videos, shows, playlists, plays, subscriptions", "social": "Posts, follows, comments, reports, blocks",
    "personal": "Notes, to-dos, habits, expenses, workouts", "market": "Stores, rides, listings, jobs",
}

RESERVED = {"user", "order", "group", "select", "table", "check", "column", "default", "grant", "limit", "offset", "primary",
            "references", "window", "end", "case", "when", "from", "to", "desc", "asc", "all", "any", "do", "on", "in", "for",
            "with", "where", "null", "true", "false", "unique", "using", "into", "cast", "both", "only", "some", "array", "as",
            "and", "or", "not", "else", "then", "having", "union", "fetch", "constraint", "create", "foreign", "lateral"}
RESERVED_TABLES = {"user", "order", "group", "select", "table", "check", "column", "default", "grant", "limit", "offset",
                   "primary", "references", "window", "end", "case", "when", "from", "to", "desc", "asc", "all", "any"}

FIELD_RE = re.compile(r"^([a-z][a-z0-9_]*)\s+([a-z]+)(?:\(([^)]*)\))?([!*~]*)$")


class ModelError(Exception):
    pass


def parse_fields(spec: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    depth, cur, parts = 0, "", []
    for ch in spec:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    for p in parts:
        p = p.strip()
        if not p:
            continue
        m = FIELD_RE.match(p)
        if not m:
            raise ModelError(f"bad field: {p}")
        name, typ, arg, flags = m.groups()
        f = {"name": name, "type": typ, "arg": (arg or "").strip(), "required": "!" in flags, "unique": "*" in flags,
             "index": "~" in flags}
        if typ == "enum":
            f["values"] = [v.strip() for v in f["arg"].split(",") if v.strip()]
        out.append(f)
    return out


def entities_for(modules: list[str]) -> list[str]:
    mods = ["core", *[m for m in modules if m in MODULES and m != "core"]]
    ents = [e for e, v in ENTITIES.items() if v[0] in mods]
    # closure: a referenced entity from another module comes along (customer for tickets, item for orders...)
    changed = True
    while changed:
        changed = False
        for e in list(ents):
            for f in parse_fields(ENTITIES[e][2]):
                if f["type"] in ("ref", "many") and f["arg"] not in ents and f["arg"] in ENTITIES:
                    ents.append(f["arg"])
                    changed = True
    return ents


def _col(name: str) -> str:
    return name + "_id" if not name.endswith("_id") else name


def build(modules: list[str], extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """modules (+ her extra entities / fields) -> {tables, relations, modules, problems}."""
    spec: dict[str, tuple[str, str, str, str]] = {k: v for k, v in ENTITIES.items()}
    extra = extra or {}
    for e in extra.get("entities", []):
        eid = re.sub(r"[^a-z0-9_]", "_", str(e.get("id") or e.get("name") or "").lower()).strip("_")[:40]
        if eid and eid not in spec:
            spec[eid] = ("custom", str(e.get("label") or e.get("name") or eid)[:60], str(e.get("fields") or "name text!"),
                         "o" if e.get("org", True) else "")
    added_fields = extra.get("fields", {})
    ents = entities_for(modules) + [e for e in spec if spec[e][0] == "custom"]
    tables: dict[str, dict[str, Any]] = {}
    relations: list[dict[str, str]] = []
    problems: list[str] = []
    for e in ents:
        mod, label, fs, opts = spec[e]
        try:
            fields = parse_fields(fs + ("," + added_fields[e] if added_fields.get(e) else ""))
        except ModelError as x:
            problems.append(f"{e}: {x}")
            continue
        cols: list[dict[str, Any]] = [{"name": "id", "type": "uuid", "pk": True, "required": True, "kind": "system"},
                                      {"name": "tenant_id", "type": "uuid", "required": True, "kind": "system"}]
        if "o" in opts and e != "org_unit" and not any(f["name"] == "org_unit" for f in fields):
            cols.append({"name": "org_unit_id", "type": "ref", "ref": "org_unit", "required": False, "kind": "system"})
        joins: list[dict[str, Any]] = []
        seen = {c["name"] for c in cols}
        for f in fields:
            if f["type"] == "many":
                joins.append({"table": f"{e}_{f['name']}", "a": e, "b": f["arg"]})
                continue
            name = _col(f["name"]) if f["type"] == "ref" else f["name"]
            if f["type"] == "pii":
                c = {"name": name + "_enc", "type": "bytes", "required": False, "kind": "pii", "label": f["name"]}
                cols.append(c)
                cols.append({"name": name + "_last4", "type": "text", "required": False, "kind": "pii_hint"})
                seen |= {name + "_enc", name + "_last4"}
                continue
            if name in seen:
                problems.append(f"{e}.{name}: duplicate column")
                continue
            seen.add(name)
            c = {"name": name, "type": f["type"], "required": f["required"], "unique": f["unique"], "index": f["index"], "kind": "field"}
            if f["type"] == "ref":
                c["ref"] = f["arg"]
                relations.append({"from": e, "to": f["arg"], "col": name, "required": f["required"]})
            if f["type"] == "enum":
                c["values"] = f["values"]
            cols.append(c)
        if "a" in opts:
            cols += [{"name": "created_at", "type": "datetime", "required": True, "kind": "audit", "default": "now"},
                     {"name": "created_by", "type": "ref", "ref": "app_user", "required": False, "kind": "audit"}]
        else:
            cols += [{"name": "created_at", "type": "datetime", "required": True, "kind": "audit", "default": "now"},
                     {"name": "created_by", "type": "ref", "ref": "app_user", "required": False, "kind": "audit"},
                     {"name": "updated_at", "type": "datetime", "required": True, "kind": "audit", "default": "now"},
                     {"name": "updated_by", "type": "ref", "ref": "app_user", "required": False, "kind": "audit"},
                     {"name": "deleted_at", "type": "datetime", "required": False, "kind": "audit"},
                     {"name": "version", "type": "int", "required": True, "kind": "audit", "default": "1"}]
        tables[e] = {"name": e, "module": mod, "label": label, "columns": cols, "append_only": "a" in opts,
                     "org_scoped": "o" in opts or e == "org_unit", "sensitive": "s" in opts, "joins": joins}
    for t in list(tables.values()):
        for j in t["joins"]:
            tables[j["table"]] = {"name": j["table"], "module": t["module"], "label": f"{t['label']} <-> {j['b']}",
                                  "columns": [{"name": "tenant_id", "type": "uuid", "required": True, "kind": "system"},
                                              {"name": _col(j["a"]), "type": "ref", "ref": j["a"], "required": True, "kind": "field", "pk": True},
                                              {"name": _col(j["b"]), "type": "ref", "ref": j["b"], "required": True, "kind": "field", "pk": True},
                                              {"name": "created_at", "type": "datetime", "required": True, "kind": "audit", "default": "now"}],
                                  "append_only": True, "org_scoped": False, "sensitive": False, "joins": [], "join": True}
            relations += [{"from": j["table"], "to": j["a"], "col": _col(j["a"]), "required": True},
                          {"from": j["table"], "to": j["b"], "col": _col(j["b"]), "required": True}]
    for t in tables.values():
        for c in t["columns"]:
            if c.get("ref") and c["kind"] in ("system", "audit") and c["ref"] in tables:
                if not any(r["from"] == t["name"] and r["col"] == c["name"] for r in relations):
                    relations.append({"from": t["name"], "to": c["ref"], "col": c["name"], "required": c["required"], "system": True})
    model = {"tables": tables, "relations": relations, "modules": sorted({t["module"] for t in tables.values()}),
             "problems": problems}
    model["problems"] += validate(model)
    return model


def validate(model: dict[str, Any]) -> list[str]:
    p: list[str] = []
    tables = model["tables"]
    for t in tables.values():
        n = t["name"]
        if n in RESERVED_TABLES:
            p.append(f"{n}: reserved word")
        if len(n) > 63 or not re.match(r"^[a-z][a-z0-9_]*$", n):
            p.append(f"{n}: bad table name")
        cols = [c["name"] for c in t["columns"]]
        if len(cols) != len(set(cols)):
            p.append(f"{n}: duplicate columns")
        if not any(c.get("pk") for c in t["columns"]):
            p.append(f"{n}: no primary key")
        for c in t["columns"]:
            if len(c["name"]) > 63 or c["name"] in RESERVED:
                p.append(f"{n}.{c['name']}: bad column name")
            if c.get("ref") and c["ref"] not in tables:
                p.append(f"{n}.{c['name']}: references missing table {c['ref']}")
            if c["type"] == "enum" and not c.get("values"):
                p.append(f"{n}.{c['name']}: enum without values")
    return p


# ---------------------------------------------------------------- SQL
PG = {"text": "text", "long": "text", "int": "integer", "decimal": "numeric(14,3)", "money": "numeric(14,2)", "bool": "boolean",
      "date": "date", "datetime": "timestamptz", "time": "time", "phone": "varchar(16)", "email": "varchar(254)", "url": "text",
      "uuid": "uuid", "json": "jsonb", "file": "uuid", "bytes": "bytea", "enum": "text", "ref": "uuid"}
SQLITE = {"text": "TEXT", "long": "TEXT", "int": "INTEGER", "decimal": "REAL", "money": "REAL", "bool": "INTEGER", "date": "TEXT",
          "datetime": "TEXT", "time": "TEXT", "phone": "TEXT", "email": "TEXT", "url": "TEXT", "uuid": "TEXT", "json": "TEXT",
          "file": "TEXT", "bytes": "BLOB", "enum": "TEXT", "ref": "TEXT", "point": "TEXT", "line": "TEXT", "polygon": "TEXT"}
GEO = {"point": "geography(Point,4326)", "line": "geography(LineString,4326)", "polygon": "geography(Polygon,4326)"}


def _pg_cols(c: dict[str, Any], geo: str) -> list[str]:
    n = c["name"]
    if c["type"] in GEO:
        if geo == "postgis":
            return [f"  {n} {GEO[c['type']]}" + (" NOT NULL" if c["required"] else "")]
        if c["type"] == "point":
            nn = " NOT NULL" if c["required"] else ""
            return [f"  {n}_lat double precision{nn}", f"  {n}_lng double precision{nn}"]
        return [f"  {n} jsonb" + (" NOT NULL" if c["required"] else "")]
    s = f"  {n} {PG[c['type']]}"
    if c.get("pk") and c["name"] == "id":
        s += " PRIMARY KEY DEFAULT gen_random_uuid()"
    elif c["required"]:
        s += " NOT NULL"
    if c.get("default") == "now":
        s += " DEFAULT now()"
    elif c.get("default"):
        s += f" DEFAULT {c['default']}"
    if c["type"] == "enum":
        vals = ", ".join("'" + v.replace("'", "''") + "'" for v in c["values"])
        s += f" CHECK ({n} IN ({vals}))"
    if c["type"] == "money":
        s += f" CHECK ({n} >= 0)" if not n.endswith(("discount", "adjust")) else ""
    if c["type"] == "email":
        s += f" CHECK ({n} ~* '^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$')"
    return [s]


def ddl_postgres(model: dict[str, Any], geo: str = "postgis") -> str:
    T_ = model["tables"]
    out = ["-- Hoola app schema (PostgreSQL 15+). Made by Hoola App Sahayak; review before running in production.",
           "CREATE EXTENSION IF NOT EXISTS pgcrypto;"]
    if geo == "postgis" and any(c["type"] in GEO for t in T_.values() for c in t["columns"]):
        out.append("CREATE EXTENSION IF NOT EXISTS postgis;")
    out += ["",
            "-- the API sets these per request: SET LOCAL app.tenant = '<uuid>'; SET LOCAL app.units = '<uuid>,<uuid>';",
            "-- SET LOCAL app.all_units = 'on' for roles with scope 'all'.",
            "CREATE OR REPLACE FUNCTION app_tenant() RETURNS uuid LANGUAGE sql STABLE AS",
            "  $$ SELECT NULLIF(current_setting('app.tenant', true), '')::uuid $$;",
            "CREATE OR REPLACE FUNCTION app_unit_ok(u uuid) RETURNS boolean LANGUAGE sql STABLE AS",
            "  $$ SELECT coalesce(current_setting('app.all_units', true), '') = 'on' OR u IS NULL",
            "       OR u = ANY (coalesce(string_to_array(NULLIF(current_setting('app.units', true), ''), ',')::uuid[], '{}')) $$;",
            "CREATE OR REPLACE FUNCTION app_touch() RETURNS trigger LANGUAGE plpgsql AS",
            "  $$ BEGIN NEW.updated_at := now(); NEW.version := OLD.version + 1; RETURN NEW; END $$;",
            "CREATE OR REPLACE FUNCTION app_no_change() RETURNS trigger LANGUAGE plpgsql AS",
            "  $$ BEGIN RAISE EXCEPTION 'append-only table'; END $$;", ""]
    fks, idx = [], []
    for t in T_.values():
        n = t["name"]
        lines: list[str] = []
        for c in t["columns"]:
            lines += _pg_cols(c, geo)
        pk = [c["name"] for c in t["columns"] if c.get("pk") and c["name"] != "id"]
        if pk:
            lines.append(f"  PRIMARY KEY (tenant_id, {', '.join(pk)})")
        for c in t["columns"]:
            if c.get("unique"):
                lines.append(f"  CONSTRAINT {n[:40]}_{c['name'][:18]}_uq UNIQUE (tenant_id, {c['name']})")
        out.append(f"-- {t['label']} ({t['module']}){' · sensitive' if t['sensitive'] else ''}{' · append-only' if t['append_only'] else ''}")
        out.append(f"CREATE TABLE {n} (\n" + ",\n".join(lines) + "\n);")
        for c in t["columns"]:
            if c.get("ref"):
                ref_col = "id"
                on_del = "CASCADE" if t.get("join") else "RESTRICT"
                fks.append(f"ALTER TABLE {n} ADD CONSTRAINT {_ix(n, c['name'], 'fk')} FOREIGN KEY ({c['name']}) "
                           f"REFERENCES {c['ref']} ({ref_col}) ON DELETE {on_del};")
                if c["kind"] != "audit":
                    idx.append(f"CREATE INDEX {_ix(n, c['name'], 'ix')} ON {n} (tenant_id, {c['name']});")
            elif c.get("index") and c["type"] not in GEO:
                idx.append(f"CREATE INDEX {_ix(n, c['name'], 'ix')} ON {n} (tenant_id, {c['name']});")
            if c["type"] in GEO and geo == "postgis":
                idx.append(f"CREATE INDEX {_ix(n, c['name'], 'gx')} ON {n} USING gist ({c['name']});")
            if c["name"] == "status" and c["type"] == "enum":
                idx.append(f"CREATE INDEX {_ix(n, 'status', 'ix')} ON {n} (tenant_id, status)"
                           + (" WHERE deleted_at IS NULL;" if not t["append_only"] else ";"))
        if not t.get("join"):
            tcol = "updated_at" if not t["append_only"] else "created_at"
            idx.append(f"CREATE INDEX {_ix(n, 'sync', 'ix')} ON {n} (tenant_id, {tcol});")
        pol = "tenant_id = app_tenant()" + (" AND app_unit_ok(org_unit_id)" if t["org_scoped"] and n != "org_unit" else "")
        idx.append(f"ALTER TABLE {n} ENABLE ROW LEVEL SECURITY;")
        idx.append(f"CREATE POLICY {n[:50]}_tenant ON {n} USING ({pol}) WITH CHECK ({pol});")
        if t["append_only"]:
            idx.append(f"CREATE TRIGGER {n[:45]}_append BEFORE UPDATE OR DELETE ON {n} FOR EACH ROW EXECUTE FUNCTION app_no_change();")
        elif not t.get("join"):
            idx.append(f"CREATE TRIGGER {n[:45]}_touch BEFORE UPDATE ON {n} FOR EACH ROW EXECUTE FUNCTION app_touch();")
        out.append("")
    out.append("-- foreign keys (added after all tables so circular references work)")
    out += fks
    out.append("")
    out.append("-- indexes, row-level security, triggers")
    out += idx
    return "\n".join(out) + "\n"


def _ix(table: str, col: str, kind: str) -> str:
    name = f"{table}_{col}_{kind}"
    if len(name) <= 63:
        return name
    import hashlib
    return f"{table[:30]}_{col[:20]}_{hashlib.sha1(name.encode()).hexdigest()[:6]}_{kind}"


def ddl_sqlite(model: dict[str, Any]) -> str:
    """The phone's own database (Room / SQLite): same tables, geo as text (GeoJSON), no RLS (one user's slice of data)."""
    out = ["PRAGMA foreign_keys = ON;"]
    for t in model["tables"].values():
        n = t["name"]
        lines = []
        for c in t["columns"]:
            s = f"  {c['name']} {SQLITE[c['type']]}"
            if c.get("pk") and c["name"] == "id":
                s += " PRIMARY KEY NOT NULL"
            elif c["required"]:
                s += " NOT NULL"
            if c.get("default") == "now":
                s += " DEFAULT CURRENT_TIMESTAMP"
            elif c.get("default"):
                s += f" DEFAULT {c['default']}"
            if c["type"] == "enum":
                vals = ", ".join("'" + v + "'" for v in c["values"])
                s += f" CHECK ({c['name']} IN ({vals}))"
            if c.get("ref"):
                s += f" REFERENCES {c['ref']}(id)" + (" ON DELETE CASCADE" if t.get("join") else "")
            lines.append(s)
        lines.append("  _dirty INTEGER NOT NULL DEFAULT 0")
        pk = [c["name"] for c in t["columns"] if c.get("pk") and c["name"] != "id"]
        if pk:
            lines.append(f"  PRIMARY KEY ({', '.join(pk)})")
        for c in t["columns"]:
            if c.get("unique"):
                lines.append(f"  UNIQUE (tenant_id, {c['name']})")
        out.append(f"CREATE TABLE {n} (\n" + ",\n".join(lines) + "\n);")
        for c in t["columns"]:
            if c.get("ref") and c["kind"] != "audit":
                out.append(f"CREATE INDEX {_ix(n, c['name'], 'ix')} ON {n} ({c['name']});")
        if not t.get("join"):
            out.append(f"CREATE INDEX {_ix(n, 'dirty', 'ix')} ON {n} (_dirty);")
    return "\n".join(out) + "\n"


KT = {"text": "String", "long": "String", "int": "Int", "decimal": "Double", "money": "Double", "bool": "Boolean", "date": "String",
      "datetime": "String", "time": "String", "phone": "String", "email": "String", "url": "String", "uuid": "String",
      "json": "String", "file": "String", "bytes": "ByteArray", "enum": "String", "ref": "String", "point": "String",
      "line": "String", "polygon": "String"}


def _camel(s: str, upper: bool = False) -> str:
    p = s.split("_")
    r = p[0] + "".join(x.capitalize() for x in p[1:])
    return r[:1].upper() + r[1:] if upper else r


def room_kotlin(model: dict[str, Any], package: str = "app.hoola.data") -> str:
    out = [f"package {package}", "", "import androidx.room.*", ""]
    for t in model["tables"].values():
        pk = [c["name"] for c in t["columns"] if c.get("pk")]
        idx = [c["name"] for c in t["columns"] if c.get("ref") and c["kind"] != "audit"]
        ann = f'@Entity(tableName = "{t["name"]}"' + (f', primaryKeys = [{", ".join(chr(34) + x + chr(34) for x in pk)}]' if len(pk) > 1 else "")
        if idx:
            ann += ", indices = [" + ", ".join(f'Index("{x}")' for x in idx[:8]) + "]"
        out.append(ann + ")")
        out.append(f"data class {_camel(t['name'], True)}(")
        fields = []
        for c in t["columns"]:
            typ = KT[c["type"]] + ("" if c["required"] else "?")
            a = "@PrimaryKey " if c.get("pk") and len(pk) == 1 else ""
            d = "" if c["required"] else " = null"
            fields.append(f'    {a}@ColumnInfo(name = "{c["name"]}") val {_camel(c["name"])}: {typ}{d}')
        fields.append('    @ColumnInfo(name = "_dirty") val dirty: Boolean = false')
        out.append(",\n".join(fields))
        out.append(")")
        out.append("")
    return "\n".join(out)


def mermaid(model: dict[str, Any], limit: int = 400) -> str:
    out = ["erDiagram"]
    names = list(model["tables"])[:limit]
    for n in names:
        t = model["tables"][n]
        out.append(f"  {n} {{")
        for c in t["columns"]:
            if c["kind"] == "audit":
                continue
            typ = {"ref": "uuid", "enum": "text"}.get(c["type"], c["type"])
            key = " PK" if c.get("pk") else (" FK" if c.get("ref") else (" UK" if c.get("unique") else ""))
            out.append(f"    {typ} {c['name']}{key}")
        out.append("  }")
    for r in model["relations"]:
        if r.get("system") or r["from"] not in names or r["to"] not in names:
            continue
        card = "||--|{" if r["required"] else "||--o{"
        out.append(f"  {r['to']} {card} {r['from']} : {r['col']}")
    return "\n".join(out) + "\n"


def summary(model: dict[str, Any]) -> dict[str, Any]:
    T_ = model["tables"]
    return {"tables": len(T_), "columns": sum(len(t["columns"]) for t in T_.values()),
            "relations": len([r for r in model["relations"] if not r.get("system")]),
            "sensitive": [n for n, t in T_.items() if t["sensitive"]], "append_only": [n for n, t in T_.items() if t["append_only"]],
            "geo": [n for n, t in T_.items() if any(c["type"] in GEO for c in t["columns"])],
            "modules": {m: [n for n, t in T_.items() if t["module"] == m] for m in model["modules"]},
            "problems": model["problems"]}


def er_html(model: dict[str, Any], title: str = "") -> str:
    """A self-contained ER page: one card per table grouped by module, keys marked, relations listed. No scripts."""
    esc = html.escape
    S = summary(model)
    parts = []
    for m in model["modules"]:
        cards = []
        for n in S["modules"][m]:
            t = model["tables"][n]
            rows = []
            for c in t["columns"]:
                if c["kind"] == "audit":
                    continue
                badge = "PK" if c.get("pk") else ("FK" if c.get("ref") else ("UQ" if c.get("unique") else ""))
                typ = f"→ {c['ref']}" if c.get("ref") else ("enum" if c["type"] == "enum" else c["type"])
                rows.append(f"<li><b class='k {badge.lower()}'>{badge}</b><span class='c'>{esc(c['name'])}</span>"
                            f"<span class='t'>{esc(typ)}{'' if not c['required'] else ' ·req'}</span></li>")
            tags = "".join(f"<i>{x}</i>" for x, on in (("sensitive", t["sensitive"]), ("append-only", t["append_only"]),
                                                       ("org", t["org_scoped"]), ("join", t.get("join"))) if on)
            cards.append(f"<div class='card'><h3>{esc(n)}</h3><p>{esc(t['label'])} {tags}</p><ul>{''.join(rows)}</ul></div>")
        parts.append(f"<section><h2>{esc(m)} <small>{esc(MODULES.get(m, ''))}</small></h2><div class='grid'>{''.join(cards)}</div></section>")
    css = """body{margin:0;font:13px/1.4 system-ui,sans-serif;background:#f6f7f9;color:#1b1f24}header{padding:18px 20px;background:#11161c;color:#fff}
header b{font-size:18px}header span{opacity:.75;margin-left:10px}section{padding:12px 20px}h2{font-size:15px;margin:10px 0}
h2 small{font-weight:400;color:#5b6570}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px}
.card{background:#fff;border:1px solid #dde2e8;border-radius:10px;padding:10px 12px}.card h3{margin:0;font-size:14px;font-family:ui-monospace,monospace}
.card p{margin:2px 0 6px;color:#5b6570}.card i{font-style:normal;font-size:11px;background:#eef1f5;border-radius:6px;padding:1px 6px;margin-left:4px}
ul{list-style:none;margin:0;padding:0}li{display:flex;gap:6px;padding:2px 0;border-top:1px dashed #eef1f5;align-items:baseline}
.k{display:inline-block;min-width:22px;font-size:10px;color:#fff;border-radius:4px;text-align:center}.k.pk{background:#b4232c}.k.fk{background:#1f6feb}
.k.uq{background:#7a5af5}.c{font-family:ui-monospace,monospace}.t{margin-left:auto;color:#5b6570;font-size:12px}"""
    head = (f"<header><b>{esc(title or 'Data model')}</b><span>{S['tables']} tables · {S['relations']} relations · "
            f"{S['columns']} columns · every table: id, tenant, created / updated by + at, soft delete, version</span></header>")
    return (f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{esc(title or 'Data model')}</title><style>{css}</style></head><body>{head}{''.join(parts)}</body></html>")


def change(extra: dict[str, Any], ops: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Her data changes: {add_entities: [{name, label, fields}], add_fields: [{entity, fields}]} (field language)."""
    x = copy.deepcopy(extra or {})
    done: list[str] = []
    for e in ops.get("add_entities") or []:
        try:
            parse_fields(str(e.get("fields") or "name text!"))
        except ModelError as er:
            done.append(f"skip {e.get('name')}: {er}")
            continue
        x.setdefault("entities", []).append({"id": e.get("id") or e.get("name"), "label": e.get("label") or e.get("name"),
                                             "fields": e.get("fields") or "name text!", "org": e.get("org", True)})
        done.append(f"table + {e.get('name')}")
    for f in ops.get("add_fields") or []:
        ent, fs = str(f.get("entity") or ""), str(f.get("fields") or "")
        try:
            parse_fields(fs)
        except ModelError as er:
            done.append(f"skip {ent}: {er}")
            continue
        if ent:
            cur = x.setdefault("fields", {}).get(ent)
            x["fields"][ent] = f"{cur}, {fs}" if cur else fs
            done.append(f"{ent} + {fs}")
    return x, done


def counts() -> dict[str, int]:
    return {"entities": len(ENTITIES), "data_modules": len(MODULES)}
