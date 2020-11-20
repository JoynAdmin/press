from datetime import datetime, timedelta

import frappe
from frappe.desk.form.load import get_attachments


def remove_baggage():
	"""Remove any remote files attached to the Site doc if older than 12 hours"""
	half_day = datetime.now() - timedelta(hours=12)
	or_filters = [
		["database_file", "!=", ""],
		["public_file", "!=", ""],
		["private_file", "!=", ""],
		["remote_config_file", "!=", ""],
		["remote_database_file", "!=", ""],
		["remote_public_file", "!=", ""],
		["remote_private_file", "!=", ""],
	]
	filters = [
		["creation", "<", half_day],
		["status", "not in", "Pending,Installing,Updating,Active,Broken"],
	]
	fields = [
		"remote_config_file",
		"remote_database_file",
		"remote_public_file",
		"remote_private_file",
	]

	sites = frappe.get_all(
		"Site", fields=["name"] + fields, filters=filters, or_filters=or_filters
	)

	for site in sites:
		# remove remote files attached to site
		remote_files = {x: site.get(x) for x in fields}

		for remote_file_type, remote_file_name in remote_files.items():
			# s3 uploads.frappe.cloud has a 1 day expiry rule for all objects, so we'll let it handle that
			frappe.db.set_value("Site", site.name, remote_file_type, None, for_update=False)


def cleanup_backups():
	"""Delete expired offsite backups and set statuses for old local ones"""
	from press.utils import chunk
	from frappe.utils.password import get_decrypted_password
	from boto3 import resource

	s3_objects = {}
	files_to_drop = []

	offsite_bucket = {
		"bucket": frappe.db.get_single_value("Press Settings", "aws_s3_bucket"),
		"access_key_id": frappe.db.get_single_value(
			"Press Settings", "offsite_backups_access_key_id"
		),
		"secret_access_key": get_decrypted_password(
			"Press Settings",
			"Press Settings",
			"offsite_backups_secret_access_key",
			raise_exception=False,
		),
	}
	s3 = resource(
		"s3",
		aws_access_key_id=offsite_bucket["access_key_id"],
		aws_secret_access_key=offsite_bucket["secret_access_key"],
		region_name="ap-south-1",
	)
	sites = frappe.get_all("Site", filters={"status": ("!=", "Archived")}, pluck="name")
	offsite_keep_count = (
		frappe.db.get_single_value("Press Settings", "offsite_backups_count") or 30
	)
	local_keep_hours = (
		frappe.parse_json(
			frappe.db.get_single_value("Press Settings", "bench_configuration")
		).keep_backups_for_hours
		or 24
	)

	for site in sites:
		expired_local_backups = frappe.get_all(
			"Site Backup",
			filters={
				"site": site,
				"status": "Success",
				"files_availability": "Available",
				"offsite": False,
				"creation": ("<", datetime.now() - timedelta(hours=local_keep_hours)),
			},
		)

		expired_offsite_backups = frappe.get_all(
			"Site Backup",
			filters={
				"site": site,
				"status": "Success",
				"files_availability": "Available",
				"offsite": True,
			},
			order_by="creation desc",
		)[offsite_keep_count:]

		for local_backup in expired_local_backups:
			# we're assuming each site's Frappe does it's work and marking them as available
			frappe.db.set_value(
				"Site Backup", local_backup["name"], "files_availability", "Unavailable"
			)

		for offsite_backup in expired_offsite_backups:
			remote_files = frappe.db.get_value(
				"Site Backup",
				offsite_backup["name"],
				["remote_database_file", "remote_private_file", "remote_public_file"],
			)
			files_to_drop.extend(remote_files)
			frappe.db.set_value(
				"Site Backup", offsite_backup["name"], "files_availability", "Unavailable"
			)

	for remote_file in set(files_to_drop):
		if remote_file:
			s3_objects[remote_file] = frappe.db.get_value(
				"Remote File", remote_file, "file_path"
			)

	if not s3_objects:
		return

	for objects in chunk([{"Key": x} for x in s3_objects.values()], 1000):
		s3.Bucket(offsite_bucket["bucket"]).delete_objects(Delete={"Objects": objects})

	for key in s3_objects:
		frappe.db.set_value("Remote File", key, "status", "Unavailable")

	frappe.db.commit()


def remove_logs():
	for doctype in (
		"Site Uptime Log",
		"Site Request Log",
		"Site Job Log",
	):
		frappe.db.delete(doctype, {"modified": ("<", datetime.now() - timedelta(days=10))})
		frappe.db.commit()

	frappe.db.delete(doctype, {"modified": ("<", datetime.now() - timedelta(days=1))})
	frappe.db.commit()
