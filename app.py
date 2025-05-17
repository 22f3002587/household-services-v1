from flask import Flask, request, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime as dt, timedelta
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required

app=Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"]="sqlite:///Household_Database.sqlite3"
app.config["SECRET_KEY"]="userdata"
db=SQLAlchemy(app)
app.app_context().push()

login=LoginManager(app)

class Admin(db.Model, UserMixin):
    __tablename__='admin'
    admin_id=db.Column(db.Integer, autoincrement=True)
    email_id=db.Column(db.String(), primary_key=True)
    name=db.Column(db.String(), nullable=False)
    password=db.Column(db.String(), nullable=False)

    def get_id(self):
        return self.email_id

class Customer(db.Model, UserMixin):
    __tablename__='customer'
    email=db.Column(db.String(), primary_key=True)
    password=db.Column(db.String(), nullable=False)
    fullname=db.Column(db.String(), nullable=False)
    address=db.Column(db.String(), nullable=False, unique=True)
    contact=db.Column(db.Integer, unique=True, nullable=False)
    pin_code=db.Column(db.Integer, nullable=False)
    status=db.Column(db.String(), default='Unblock')
    
    def get_id(self):
        return self.email

class Service_Request(db.Model):
    __tablename__='service_request'
    request_id=db.Column(db.String(), primary_key=True)
    service_id=db.Column(db.Integer,db.ForeignKey('services.service_id') ,nullable=False)
    service_name=db.Column(db.String(), nullable=False)
    customer_id=db.Column(db.String(), db.ForeignKey('customer.email'), nullable=False)
    professional_id=db.Column(db.String(), db.ForeignKey('professional.email'), nullable=False)
    requested_date=db.Column(db.DateTime, unique=False, default=dt.utcnow)
    scheduled_date=db.Column(db.DateTime, )
    closed_date=db.Column(db.DateTime, unique=False, default=None)
    status=db.Column(db.String(), default='Requested')

class Professional(db.Model, UserMixin):
    __tablename__='professional'
    email=db.Column(db.String(), primary_key=True)
    password=db.Column(db.String(), nullable=False)
    fullname=db.Column(db.String(), nullable=False)
    service_category=db.Column(db.String(), nullable=False)
    service_name=db.Column(db.String(), nullable=False, unique=True)
    rating=db.Column(db.Integer, default=0)
    experience=db.Column(db.Integer)
    address=db.Column(db.String(), nullable=False, unique=True)
    pin_code=db.Column(db.Integer, nullable=False)
    status=db.Column(db.String(), default="Waiting for admin approval..")

    def get_id(self):
        return self.email

class Services(db.Model):
    __tablename__='services'
    service_id=db.Column(db.Integer, primary_key=True)
    service_category=db.Column(db.String(), nullable=False)
    service_name=db.Column(db.String(), nullable=False, unique=True)
    expected_time=db.Column(db.String(), nullable=False, unique=False)
    description=db.Column(db.String(), nullable=False)
    base_price=db.Column(db.Float, nullable=False)

def date_increment(start_date):
    schedule=start_date+ timedelta(days=2)
    return schedule


@login.user_loader
def load_user(email):
    if session['role']=='customer':
        return Customer.query.filter_by(email=email).first()
    
    if session['role']=='admin':
        return Admin.query.filter_by(email_id=email).first()
    
    if session['role']=='professional':
        return Professional.query.filter_by(email=email).first()


@app.route('/')
def home():
    return render_template("index.html")


@app.route("/customer_login", methods=["GET","POST"])  # Working Fine
def user_login():
    if request.method=="GET":
        return render_template('customer_login.html')
    
    if request.method=="POST":
        email=request.form['email']
        password=request.form['password']
        customer=Customer.query.filter_by(email=email).first()
        if customer:
            if customer.password==password:
                if customer.status=='Unblock':
                    login_user(customer)
                    session['role']='customer'
                    return redirect("/customer_home")

                elif customer.status=='Block':
                    return render_template("customer_login.html", alert2='You are blocked by admin')
            else:
                return render_template("customer_login.html", alert1="Incorrect Password!! ")
            
        else:
            return render_template("customer_login.html", alert2="Customer doesn't exist!! ")    


@app.route("/customer_signup", methods=["GET","POST"])   # Working Fine
def user_signup():
    if request.method=="GET":
        return render_template("customer_signup.html")
    
    if request.method=="POST":
        email=request.form['email_id']
        password=request.form['password']
        fullname=request.form['fullname']
        address=request.form['address']
        pincode=request.form['pincode']
        contact=request.form['contact']
        if Customer.query.filter_by(email=email).first() is None:
            customer=Customer(email=email, password=password, fullname=fullname, address=address, pin_code=pincode, contact=contact)  
            db.session.add(customer)
            db.session.commit()
            return render_template("customer_signup.html",success="Registered Successfully")
    
        return render_template("customer_signup.html", not_exist="Customer already exist.")


@app.route('/customer_home',methods=["GET","POST"])
@login_required
def custom_home():
        serv=Service_Request.query.filter_by(customer_id=current_user.email).all()
        services=Services.query.all()
        data=Customer.query.filter_by(email=current_user.email).first()

        if request.method=="GET":
            alert=request.args.get('alert')
            if alert:
                return render_template('customer_home.html',service_request=serv, user_data=data, services=services, alert=alert)
            return render_template('customer_home.html',service_request=serv, user_data=data, services=services)


        if request.method=="POST":
            if request.form['form_id']=='clean':
                serv=Services.query.filter_by(service_id=request.form['service_id']).first()
                pro=Professional.query.filter_by(service_name=serv.service_name).first()
                req=Service_Request.query.filter_by(service_id=serv.service_id, request_id=f'{request.form["customer_email"][:3]}{request.form["service_id"][0]}').first()
                if req:
                    return redirect(url_for('custom_home',alert="You already booked this service"))

                if pro and pro.status=='Accepted by admin':
                    schedule=date_increment(dt.utcnow())
                    req=Service_Request(request_id=f'{request.form["customer_email"][:3]}{request.form["service_id"][0]}',service_name=serv.service_name, service_id=serv.service_id, customer_id=current_user.email, professional_id=pro.email, scheduled_date=schedule)
                    db.session.add(req)
                    db.session.commit()
                    return redirect('/customer_home')
                    
                else:
                    return redirect(url_for('custom_home',alert="No professional assigned"))   

            if request.form['form_id']=='home_decore':
                serv=Services.query.filter_by(service_id=request.form['service_id']).first()
                pro=Professional.query.filter_by(service_name=serv.service_name).first()
                req=Service_Request.query.filter_by(service_id=serv.service_id, request_id=f'{request.form["customer_email"][:3]}{request.form["service_id"][0]}').first()
                if req:
                    return redirect(url_for('custom_home',alert="You already booked this service"))

                if pro and pro.status=='Accepted by admin':
                    schedule=date_increment(dt.utcnow())
                    req=Service_Request(request_id=f'{request.form["customer_email"][:3]}{request.form["service_id"][0]}',service_name=serv.service_name, service_id=serv.service_id, customer_id=current_user.email, professional_id=pro.email, scheduled_date=schedule)
                    db.session.add(req)
                    db.session.commit()
                    return redirect('/customer_home')
                    
                else:
                    return redirect(url_for('custom_home',alert="No professional assigned")) 

            if request.form['form_id']=='health':
                serv=Services.query.filter_by(service_id=request.form['service_id']).first()
                pro=Professional.query.filter_by(service_name=serv.service_name).first()
                req=Service_Request.query.filter_by(service_id=serv.service_id, request_id=f'{request.form["customer_email"][:3]}{request.form["service_id"][0]}').first()
                if req:
                    return redirect(url_for('custom_home',alert="You already booked this service"))

                if pro and pro.status=='Accepted by admin':
                    schedule=date_increment(dt.utcnow())
                    req=Service_Request(request_id=f'{request.form["customer_email"][:3]}{request.form["service_id"][0]}',service_name=serv.service_name, service_id=serv.service_id, customer_id=current_user.email, professional_id=pro.email, scheduled_date=schedule)
                    db.session.add(req)
                    db.session.commit()
                    return redirect('/customer_home')
                    
                else:
                    return redirect(url_for('custom_home',alert="No professional assigned")) 
                

            if request.form['form_id']=='saloon':
                serv=Services.query.filter_by(service_id=request.form['service_id']).first()
                pro=Professional.query.filter_by(service_name=serv.service_name).first()
                req=Service_Request.query.filter_by(service_id=serv.service_id, request_id=f'{request.form["customer_email"][:3]}{request.form["service_id"][0]}').first()
                if req:
                    return redirect(url_for('custom_home',alert="You already booked this service"))

                if pro and pro.status=='Accepted by admin':
                    schedule=date_increment(dt.utcnow())
                    req=Service_Request(request_id=f'{request.form["customer_email"][:3]}{request.form["service_id"][0]}',service_name=serv.service_name, service_id=serv.service_id, customer_id=current_user.email, professional_id=pro.email, scheduled_date=schedule)
                    db.session.add(req)
                    db.session.commit()
                    return redirect('/customer_home')
                    
                else:
                    return redirect(url_for('custom_home',alert="No professional assigned")) 


            if request.form['form_id']=='electrician':
                serv=Services.query.filter_by(service_id=request.form['service_id']).first()
                pro=Professional.query.filter_by(service_name=serv.service_name).first()
                req=Service_Request.query.filter_by(service_id=serv.service_id, request_id=f'{request.form["customer_email"][:3]}{request.form["service_id"][0]}').first()
                if req:
                    return redirect(url_for('custom_home',alert="You already booked this service"))

                if pro and pro.status=='Accepted by admin':
                    schedule=date_increment(dt.utcnow())
                    req=Service_Request(request_id=f'{request.form["customer_email"][:3]}{request.form["service_id"][0]}',service_name=serv.service_name, service_id=serv.service_id, customer_id=current_user.email, professional_id=pro.email, scheduled_date=schedule)
                    db.session.add(req)
                    db.session.commit()
                    return redirect('/customer_home')
                    
                else:
                    return redirect(url_for('custom_home',alert="No professional assigned"))       

            if request.form['form_id']=='button':        
                if request.form['action'][:5]=='close':
                    req=Service_Request.query.filter_by(request_id=request.form['action'][5:]).first()
                    if req.status!='Closed by customer': #or req.status!='Professional Dismissed':
                        req.status='Closed by customer'
                        req.closed_date=dt.now()
                        db.session.commit()
                        return redirect(url_for('rating',service_name=req.service_name, req_id=req.request_id))
            
                    else:
                        return redirect(url_for('custom_home',alert='Already Closed'))
                    
                if request.form['action'][:4]=='edit':
                    return redirect(url_for('edit_request', req_id=request.form['action'][4:]))   
                        
                if request.form['action'][:6]=='delete':
                    req=Service_Request.query.filter_by(request_id=request.form['action'][6:]).first()
                    db.session.delete(req)
                    db.session.commit()
                    return redirect('/customer_home') 


@app.route('/edit_request', methods=['GET','POST'])
def edit_request():
    if request.method=='GET':
        req_id=request.args['req_id']
        req=Service_Request.query.get(req_id)
        return render_template('service_request_edit.html',req=req)
    
    if request.method=='POST':
        req_id=request.form['done']
        req=Service_Request.query.get(req_id)
        req.scheduled_date=dt.strptime(request.form['schedule'], '%Y-%m-%d')
        req.requested_date=dt.strptime(request.form['request'], '%Y-%m-%d')
        db.session.commit()
        return render_template("service_request_edit.html",req=req , message="Updated successfully!")


@app.route('/customer_review', methods=['GET','POST'])
def rating():
    if request.method=='GET':
        service_name=request.args['service_name']
        req_id=request.args['req_id']

        pro=Professional.query.filter_by(service_name=service_name).first()
        return render_template('service_remarks.html', pro=pro, req_id=req_id)
    
    if request.method=="POST":
        pro_id=request.form['submit']
        pro=Professional.query.filter_by(email=pro_id).first()
        pro.rating=request.form['rating']
        db.session.commit()
        return redirect('/customer_home')


@app.route("/customer_search", methods=["GET", "POST"])
def search_service():
    if request.method=="GET":
        service=Services.query.all()
        return render_template("customer_search.html", service=service, user_data=current_user)
    
    if request.method=="POST":
        if request.form['form_id']=='search':
            search_type=request.form['search_type']
            service=request.form['service'].title()
            if search_type=='service_name':
                rec=Services.query.filter(Services.service_name.ilike(f'{service}%')).all()
                return render_template('customer_search.html', service=rec, user_data=current_user)

            if search_type=='service_category':
                rec=Services.query.filter(Services.service_category.ilike(f'{service}%')).all()
                return render_template('customer_search.html', service=rec, user_data=current_user)
            
        if request.form['action']=='Book':
            serv=Services.query.filter_by(service_id=request.form['service_id']).first()
            pro=Professional.query.filter_by(service_name=serv.service_name).first()
            req=Service_Request.query.filter_by(service_id=serv.service_id, request_id=f'{request.form["customer_email"][:3]}{request.form["service_id"][0]}').first()
            if req:
                return redirect(url_for('custom_home',alert="You already booked this service"))

            if pro:
                req=Service_Request(request_id=f'{request.form["customer_email"][:3]}{request.form["service_id"][0]}',service_name=serv.service_name, service_id=serv.service_id, customer_id=current_user.email, professional_id=pro.email, scheduled_date=date_increment(dt.utcnow()))
                db.session.add(req)
                db.session.commit()
                return redirect('/customer_home')
                    
            else:
                return redirect(url_for('custom_home',alert="No professional assigned")) 

@app.route("/prof_login", methods=["GET","POST"])   
def pro_login():
    if request.method=="GET":
        return render_template("professional_login.html")
    
    if request.method=="POST":
        email=request.form['email']
        password=request.form['password']
        pro=Professional.query.filter_by(email=email).first()
        if pro:
            if pro.password==password:
                if pro.status=='Accepted by admin':
                    login_user(pro)
                    session['role']='professional'
                    return redirect('/prof_home')
                
                elif pro.status=="Rejected by admin":
                    return render_template('professional_login.html', alert2="You've been rejected by admin")
                
                elif pro.status=="Waiting for admin approval..":
                    return render_template('professional_login.html', alert2="Admin hasn't approved you")
                
                elif pro.status=="Blocked by admin":
                    return render_template('professional_login.html', alert2="You are blocked by admin")
            
            else:
                return render_template('professional_login.html',alert2="Incorrect password")

        else:
            return render_template('professional_login.html', alert1="Professional doesn't exist")    


@app.route("/prof_signup", methods=["GET","POST"])    
def pro_signup():
    services=Services.query.all()
    if request.method=="GET":
        return render_template("professional_signup.html",services=services)
    
    if request.method=="POST":
        email=request.form['email']
        password=request.form['password']
        fullname=request.form['fullname']
        category=request.form['category']
        service=request.form['service']
        experience=request.form['experience']
        address=request.form['address']
        pincode=request.form['pincode']
        pro=Professional(email=email, password=password, fullname=fullname, service_category=category, service_name=service, experience=experience, address=address, pin_code=pincode)
        if Professional.query.filter_by(email=email).first() is None:
            if Professional.query.filter_by(service_name=service).first() is None:
                db.session.add(pro)
                db.session.commit()
        
                return render_template("professional_signup.html", message2="Registered successfully", services=services)
            return render_template("professional_signup.html",message1="Service Already Assigned",services=services)
        return render_template("professional_signup.html",message1="Professional Already Exist",services=services)    


@app.route("/prof_home",methods=["GET","POST"])
@login_required
def prof_home():    
    if request.method=="GET":
        alert=request.args.get('alert')
        close_req=Service_Request.query.filter_by(professional_id=current_user.email, status='Closed by customer').all()
        custom_data=[]
        service_close=[]
        prof=Professional.query.filter_by(email=current_user.email).first()
        serv_req=Service_Request.query.with_entities(Service_Request.customer_id).filter_by(service_name=current_user.service_name).all()
        for email_id in serv_req:
            custom_data+=[(Customer.query.filter_by(email=email_id[0]).first(),Service_Request.query.with_entities(Service_Request.scheduled_date).filter_by(customer_id=email_id[0]).first())]

        for service in close_req:
            service_close+=[service]
        if alert:
            return render_template("professional_home.html", prof_data=prof, customer_details=custom_data, closed_services=service_close, alert=alert, edit=False)
        return render_template("professional_home.html", prof_data=prof, customer_details=custom_data, closed_services=service_close, edit=False)

    if request.method=="POST":
        if request.form['action'][:6]=='Accept':
            req=Service_Request.query.filter_by(customer_id=request.form['action'][6:], professional_id=current_user.email).first()
            if req.status=='Requested':
                req.status='Professional Accepted'
                db.session.commit()
                return 'Accepted'
            
            elif req.status=='Closed by customer':
                return redirect(url_for('prof_home', alert="Already closed by customer"))
            
            elif req.status=='Professional Accepted':
                return redirect(url_for('prof_home', alert="Already accepted"))


        if request.form['action'][:7]=='Dismiss':
            req=Service_Request.query.filter_by(customer_id=request.form['action'][7:], professional_id=current_user.email).first()
            if req.status=='Requested':
                req.status='Professional Dismissed'
                req.closed_date=dt.now()
                db.session.commit()
                return 'Dismissed'
            
            elif req.status=='Closed by customer':
                return redirect(url_for('prof_home', alert="Already closed by customer"))
            
            elif req.status=='Professional Dismissed':
                return redirect(url_for('prof_home', alert="Already Dismissed"))
        
        if request.form['action'][:4]=='Edit':
            prof_id=request.form['action'][4:]
            return redirect(url_for('prof_edit',prof_id=prof_id))

    return redirect('/prof_home')        


@app.route("/prof_edit_profile", methods=["GET","POST"])
@login_required
def prof_edit():
    if request.method=="GET":
        prof_id=request.args.get('prof_id')
        return render_template('pro_profile_edit.html',prof_id=prof_id)
        
    if request.method=="POST":
        prof_id=request.form['save']
        pro=Professional.query.get(prof_id)
        pro.fullname=request.form['fullname']
        pro.experience=request.form['experience']
        pro.address=request.form['address']
        pro.pin_code=request.form['pincode']
        db.session.commit()
        return render_template('pro_profile_edit.html', message="Updated Successfully")


@app.route("/admin_login", methods=["GET","POST"])
def admin_login():
    if request.method=="GET":
        return render_template("admin_login.html")
    
    if request.method=="POST":
        name=request.form['name']
        admin_email=request.form['email']
        password=request.form['password']
        admin=Admin.query.filter_by(email_id=admin_email).first()
        if admin:
            if admin.password==password:
                login_user(admin)
                session['role']='admin'
                return redirect(url_for('admin_home'))
            else:
                return render_template("admin_login.html",message1="Incorrect Password")
        else:
            return render_template("admin_login.html",message2="Admin doesn't exist")   


@app.route('/admin_home',methods=["GET","POST"])
@login_required
def admin_home():
    if request.method=="GET":
        professional=Professional.query.all()
        services=Services.query.all()
        serv_req=Service_Request.query.all()
        customer=Customer.query.all()
        return render_template("admin_home.html", professional=professional, services=services, service_request=serv_req, customer=customer)
    
    if request.method=="POST":
        form_id=request.form.get('form_id')

        if form_id=='id1':
            button1=request.form['action']
            if button1[:6]=='Accept': 
                pro=Professional.query.filter_by(email=button1[6:]).first()
                pro.status="Accepted by admin"
                db.session.commit()
                return redirect('/admin_home')

            if button1[:6]=='Reject':
                pro=Professional.query.filter_by(email=button1[6:]).first()
                pro.status="Rejected by admin"
                db.session.commit()     
                return redirect('/admin_home')
            
            if button1[:5]=='Block':
                pro=Professional.query.filter_by(email=button1[5:]).first()
                pro.status="Blocked by admin"
                db.session.commit()
                return redirect('/admin_home')
    
        if form_id=='id2':     
            button2=request.form['button']
            if button2[:6]=='Delete':
                serv=Services.query.filter_by(service_id=button2[6:]).first()
                pro=Professional.query.filter_by(service_name=serv.service_name).first()
                db.session.delete(serv)
                if pro:
                    db.session.query(Service_Request).filter(Service_Request.professional_id == pro.email).delete()
                    db.session.delete(pro)
                db.session.commit()   
                return redirect('/admin_home')
                
            if button2[:4]=='Edit':
                service_id=button2[4:]
                return redirect(url_for('edit_service',service_id=service_id))
            
        if form_id=='id3':
            button3=request.form['button']
            if button3[:5]=='block':
                customer=Customer.query.filter_by(email=button3[5:]).first()
                customer.status='Block'
                db.session.commit()
                return redirect('/admin_home')

            if button3[:7]=='unblock':
                customer=Customer.query.filter_by(email=button3[7:]).first()
                customer.status='Unblock'
                db.session.commit()
                return redirect('/admin_home')
            
@app.route('/prof_view/<string:id>', methods=['GET','POST'])
def pro_details(id):
    pro=Professional.query.get(id)
    return render_template('prof_detail.html',pro=pro)

@app.route('/service_add', methods=["GET","POST"])
@login_required
def add_service():
    if request.method=="GET":
        return render_template("admin_service_add.html")
    
    if request.method=="POST":
        service_category=request.form['service_category']
        service_name=request.form['service_name']
        base_price=request.form['price']
        expect_time=request.form['expect_time']
        desc=request.form['description']
        
        if request.form['submit']=='Add':
            if Services.query.filter_by(service_name=service_name).first() is None:
                serv=Services(service_category=service_category, expected_time=expect_time, service_name=service_name, base_price=base_price, description=desc)
                db.session.add(serv)
                db.session.commit()
                return render_template("admin_service_add.html", add="Added Successfully")

            return render_template('admin_service_add.html', alert="Service name already present") 

        if request.form['submit']=='Cancel':
            return redirect('/admin_home')   


@app.route('/service_edit',methods=["GET","POST"])
def edit_service():
    if request.method=="GET":
        service_id=request.args.get('service_id')
        serv=Services.query.filter_by(service_id=service_id).first()
        return render_template('admin_service_edit.html', service_id=service_id, service=serv)
        
    if request.method=="POST":
        id=request.form['id']
        serv=Services.query.get(id)
        serv.service_name=request.form['service_name']
        serv.description=request.form['description']
        serv.base_price=request.form['price']
        serv.expected_time=request.form['time']
        db.session.commit()
        return render_template('admin_service_edit.html',message="Updated Succesfully", service=serv.service_category, service_id=id)
        

@app.route('/admin_search', methods=['GET', 'POST'])
@login_required
def admin_search():
    if request.method=="GET":
        pro=Professional.query.all()
        return render_template("admin_search.html", pro=pro)

    if request.method=="POST":
        if request.form['form_id']=='id1':
            search_by=request.form['search_by']
            prof_detail=request.form['pro']
            
            if search_by=='pro_email': 
                pro=Professional.query.filter(Professional.email.ilike(f'{prof_detail}%')).all()

            elif search_by=='pro_name':
                pro=Professional.query.filter(Professional.fullname.ilike(f'{prof_detail}%')).all()

            elif search_by=='pro_service':
                pro=Professional.query.filter(Professional.service_name.ilike(f'{prof_detail}%')).all()

            return render_template('admin_search.html',pro=pro)  

        if request.form['form_id']=='id2':
            button1=request.form['action']
            if button1[:6]=='Accept': 
                pro=Professional.query.filter_by(email=button1[6:]).first()
                pro.status="Accepted by admin"
                db.session.commit()
                return redirect('/admin_search')

            if button1[:6]=='Reject':
                pro=Professional.query.filter_by(email=button1[6:]).first()
                pro.status="Rejected by admin"
                db.session.commit()     
                return redirect('/admin_search')
            

@app.route('/logout_user')
def logout():
    logout_user()
    session.pop('role',None)
    return redirect('/')
 

if __name__=='__main__':
    app.run()