from flask import Flask, render_template, request, jsonify

login = Flask(__name__)

users = []
ADMIN_EMAIL = ["Aadmin@system.com","Badmin@system.com","Cadmin@system.com","Dadmin@system.com","Zadmin@system.com"]

@login.route('/')
