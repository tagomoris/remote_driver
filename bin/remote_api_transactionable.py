#!/usr/bin/env python

from google.appengine.ext import db

class Name(db.Model):
    name = db.StringProperty

    def addstring(self, v):
        self.name = self.name + v

USER_PRIV_CREATED = 'created'
USER_PRIV_UPDATED = 'updated'

class User(db.Model):
    priv = db.StringProperty

class Group(db.Model):
    code = db.IntegerProperty

def update_user(user):
    user.name.addstring(v)
    user.name.put()
    user.priv = USER_PRIV_UPDATED
    user.put()

def update_names_add_char(key_names, v):
    for user in User.get_by_key_name(key_names):
        update_user(user)
    return True

def update_names_add_char_by_group(group_name, v):
    for user in User.all().ancestor(Group.get_by_key_name(group_name).key()).run():
        update_user(user)
    return True

def create_group(group_name, code, user_names):
    g = Group.get_or_insert(group_name, code=code)
    for uname in user_names:
        u = User(parent=g, key_name=uname, priv=USER_PRIV_CREATED)
        u.put()
    return g.code


pickle ( protocol = HIGHEST_PROTOCOL )


def hoge_pos(vals):
    hoge
    pos
    return "pos"

remote_db.run_in_transaction(hoge_pos, vals)
db.run_in_transaction(hoge_pos, vals)

1. check contents of hoge_pos
2. trace readline.get_history_item(num) for all lines, and get definition lines of hoge_pos
3. delete hoge_pos entry from hoge_pos.func_globals, func_dict
4. pack pickle.dumps(globals,dict) and func-definition
5. request code to appspot
