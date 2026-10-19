"""Phiên bản cấu trúc cache tín hiệu.

Chức năng: thống nhất phiên bản manifest giữa reader, writer và fingerprint.
Sửa tại đây khi: thay định dạng dữ liệu cache không tương thích với bản cũ.
Liên kết: identity.py, writer.py và reader.py cùng dùng SCHEMA_VERSION.
"""
# COMPONENT: storage.schema

SCHEMA_VERSION = 1
