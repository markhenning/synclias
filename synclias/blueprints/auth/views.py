from flask import Blueprint
from flask import flash, redirect, render_template, url_for
from flask_login import login_required

from flask import current_app
from synclias import db


from flask_login import current_user, login_user, logout_user
import sqlalchemy as sa
from synclias.models import User

from synclias.blueprints.auth.forms import LoginForm, AdminPassForm, ChangePassForm

auth = Blueprint("auth", __name__, template_folder="templates")


## Main login form
## We only have one user - admin
## If that user doesn't exist, redirect to "Set Password" page
@auth.route('/login', methods=['GET', 'POST'])
def login():
    
    ## Boot authentiated users to /
    if current_user.is_authenticated:
        current_app.logger.debug("Bouncing logged in user")
        return redirect(url_for('core.home'))
    
    ## Simple user count check - if we don't have any, set the admin password                    
    user_count = len(db.session.query(User).all())

    if user_count != 0:

        ## Present login page and handle login
        form = LoginForm()

        if form.validate_on_submit():
            user = db.session.scalar(sa.select(User).where(User.username == 'admin'))
            
            if not user.check_password(form.password.data): # type: ignore
                current_app.logger.debug("Rejecting login")
                flash('Invalid password')
                return redirect(url_for('auth.login'))
            
            current_app.logger.debug("Logging in!")
            login_user(user, remember=form.remember_me.data)
            return redirect(url_for('core.settings'))
        
        return render_template('login.html', title='Log In', form=form)

    else:
        ## User table is empty, get/set new admin password
        form = AdminPassForm()
        if form.validate_on_submit():

            user = User(username='admin', email='admin@local', role='admin') # pyright: ignore[reportCallIssue]
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Password Set')
            
            return redirect(url_for('auth.login'))
        
        return render_template('set_admin.html', title='Set Password', form=form)

## Simple page to change admin password
@auth.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():

    form = ChangePassForm()

    if form.validate_on_submit():

        user = db.session.scalar(sa.select(User).where(User.username == 'admin'))
        
        ## Password check fail, re-direct back to login
        if not user.check_password(form.password.data): # type: ignore
            current_app.logger.debug("Password change failed - incorrect old password")
            flash('Incorrect old password')
            return redirect(url_for('auth.change_password'))
        
        ## Validated, now change the database entries
        current_app.logger.debug("Admin password changed")
        user.set_password(form.new_password.data) # pyright: ignore[reportOptionalMemberAccess]
        db.session.commit()

        ## Log them out and send them to the login screen
        flash('Password Set')
        logout_user()
        
        return redirect(url_for('auth.login'))
    
    return render_template('change_password.html', title='Change Password', form=form)

@auth.route('/logout',methods=['GET'])
def logout():
    logout_user()
    flash('Logged out')
    current_app.logger.debug("Logged out")
    return redirect(url_for('auth.login'))



