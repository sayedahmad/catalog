from flask import Flask, render_template,\
                  request, redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc, desc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Catagories, Items, User
from flask import make_response, session as login_session
from flask import session as login_session
import random
import string
import requests
import json
import httplib2
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from sqlalchemy.pool import SingletonThreadPool


# For Oauth
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

# Google plus Secret Key
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']


app = Flask(__name__)

# Connect to database and create sessions for database
engine = create_engine('sqlite:///catalog.db?check_same_thread=False')
Base.metadata.bind = engine

DBsession = sessionmaker(bind=engine)
session = DBsession()

# Login configuration


# Create new user
def create_user(login_session):

    new_user = User(
                    name=login_session['username'],
                    email=login_session['email']
                    )
    session.add(new_user)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def get_user_id(email):

    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


@app.route('/')
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST', 'GET'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data
    print code

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
            'Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # Check if user exists if not create a new user

    user_id = get_user_id(data['email'])
    if not user_id:
        user_id = create_user(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: \
                    150px;-webkit-border-radius: 150px; \
                    -moz-border-radius:150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

    # DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session['access_token']
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps(
            'Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s'\
          % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        flash("Successfully logged out")
        return redirect('/showCatagories')
    else:
        response = make_response(json.dumps(
            'Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/showCatagories')
def showCatagories():
    catagory = session.query(Catagories)
    items = session.query(Items).order_by(desc(Items.id))
    return render_template('recentItems.html',
                           catagory=catagory, items=items,
                           message='Latest Items')


@app.route('/addCatagory', methods=['GET', 'POST'])
def addCatagory():

    if 'username' not in login_session:
        return redirect('/login')

    user_id = login_session['user_id']
    print user_id
    if request.method == 'POST':
        newCatagory = Catagories(name=request.form['name'], user_id=user_id)
        session.add(newCatagory)
        session.commit()
        return redirect(url_for('showCatagories'))

    else:
        return render_template('addCatagory.html')
        # return 'not posted'


@app.route('/category/<int:cat_id>/')
@app.route('/category/<int:category_id>/item/')
def showCatagory(cat_id):
    catagory = session.query(Catagories).filter_by(id=cat_id).one()
    items = session.query(Items).filter_by(catagory_id=cat_id).all()
    return render_template("catagory.html",
                           catagory=catagory, items=items,
                           message=catagory.name)


@app.route('/editCatagory/<int:cat_id>/', methods=['GET', 'POST'])
def editCatagory(cat_id):

    if 'username' not in login_session:
        return redirect('/login')

    catagory = session.query(Catagories).filter_by(id=cat_id).one()

    if catagory.user_id != login_session['user_id']:
        flash('Category was created by another user\
              and can only be edited with that specific user')
        return redirect(url_for('showCatagory'))

    if request.method == 'POST':
        if request.form['name']:
            catagory.name = request.form['name']
        session.add(catagory)
        session.commit()
        return redirect(url_for('showCatagory', cat_id=catagory.id))
    else:
        return render_template('editCatagory.html', catagory=catagory)


@app.route('/category/<int:cat_id>/delete/', methods=['GET', 'POST'])
def deleteCategory(cat_id):

    if 'username' not in login_session:
        return redirect('/login')

    category = session.query(Catagories).filter_by(id=cat_id).one()

    if category.user_id != login_session['user_id']:
        flash('Category was created by another user\
              and can only be deleted by creator')
        return redirect(url_for('showCatagories'))

    if request.method == 'POST':
        session.delete(category)
        session.commit()

        flash('%s Successfully Deleted' % category.name)

        return redirect(url_for('showCatagories'))
    else:
        return render_template('deleteCatagory.html', category=category)


@app.route('/addItem', methods=['GET', 'POST'])
def addItem():

    if 'username' not in login_session:
        return redirect('/login')

    user_id = login_session['user_id']

    if request.method == 'POST':

        catagory = session.query(Catagories).filter_by(
                                 name=request.form['catagory']).one()

        newItem = Items(title=request.form['title'],
                        description=request.form['description'],
                        catagory_id=catagory.id,
                        user_id=user_id)
        session.add(newItem)
        session.commit()
        flash('%s Successfully created' % (newItem.title))
        return redirect(url_for('showCatagories'))
    else:
        catagories = session.query(Catagories)
        return render_template("add_item.html",
                               catagories=catagories, message="Add New Item")


@app.route('/showItem/<int:item_id>/')
def showItem(item_id):
    item = session.query(Items).filter_by(id=item_id).one()
    return render_template("item_description.html",
                           item=item, message='Item View')


@app.route('/editItem/<int:item_id>/', methods=['GET', 'POST'])
def editItem(item_id):

    if 'username' not in login_session:
        return redirect('/login')

    item = session.query(Items).filter_by(id=item_id).one()
    current_cat = session.query(Catagories).filter_by(
                                id=item.catagory_id).one()
    catagories = session.query(Catagories)

    if item.user_id != login_session['user_id']:
        flash('Item was created by another userand\
              can only be edited by creator')
        return redirect(url_for('showItem', item_id=item_id))

    if request.method == 'POST':
        if request.form['title']:
            item.title = request.form['title']
        if request.form['description']:
            item.description = request.form['description']

        session.add(item)
        session.commit()
        flash('%s Successfully created' % (item.title))
        return redirect(url_for('showItem', item_id=item_id))
    else:
        return render_template("edit_item.html",
                               item=item, catagory=current_cat.name,
                               catagories=catagories)


@app.route('/deleteItem/<int:item_id>/', methods=['GET', 'POST'])
def deleteItem(item_id):

    if 'username' not in login_session:
        return redirect('/login')

    item = session.query(Items).filter_by(id=item_id).one()

    if item.user_id != login_session['user_id']:
        flash('Item was created by another user\
              and can only be deleted by creator')
        return redirect(url_for('showItem', item_id=item_id))

    if request.method == 'POST':
        session.delete(item)
        session.commit()
        return redirect(url_for('showCatagories'))

    else:
        return render_template('deleteItem.html',
                               item=item, message='Item View')


# JSON endpoints

@app.route('/category/JSON')
def categoriesJSON():
    """Return JSON for all the categories"""
    categorys = session.query(Catagories).all()
    return jsonify(categories=[c.serialize for c in categorys])


@app.route('/category/<int:category_id>/JSON')
def categoryJSON(category_id):
    """Return JSON of all the items for a category"""
    category = session.query(Catagories).filter_by(id=category_id).one()
    items = session.query(Items).filter_by(
        catagory_id=category_id).all()
    return jsonify(items=[i.serialize for i in items])


@app.route('/item/JSON')
def itemsJSON():
    """Return JSON for an item"""
    items = session.query(Items).all()
    return jsonify(items=[i.serialize for i in items])


@app.route('/category/<int:category_id>/item/<int:item_id>/JSON')
def itemJSON(category_id, item_id):
    """Return JSON for an item"""
    item = session.query(Items).filter_by(id=item_id).one()
    return jsonify(item=item.serialize)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8888)
