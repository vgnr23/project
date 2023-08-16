from bson import ObjectId
import pymongo
from flask import request
from datetime import datetime

client = pymongo.MongoClient('mongodb://127.0.0.1:27017/')
userdb = client['chatgpt']
users = userdb.users
history=userdb.history
feedback=userdb.feedback
admin=userdb.admin
def insert_data():
	if request.method == 'POST':
		name = request.form['name']
		email = request.form['email']
		password = request.form['pass']

		reg_user = {}
		reg_user['name'] = name
		reg_user['email'] = email
		reg_user['password'] = password
		reg_user['status']="active"
		if users.find_one({"email":email}) == None:
			users.insert_one(reg_user)
			return True
		else:
			return False


def check_user():

	if request.method == 'POST':
		email = request.form['email']
		password = request.form['pass']

		user = {
			"email": email,
			"password": password
		}

		user_data = users.find_one(user)
		if user_data == None:
			return False, "",""
		elif user_data["status"]=="block":
			return "blocked",user_data["name"],user_data["email"]
		else:
			# history_retrive(user_data["name"],user_data["email"])
			return True, user_data["name"],user_data["email"]

def history_insert(username,ques,reply,email):
	conversation= {}
	conversation['username'] = username
	conversation['email'] = email
	conversation['question'] = ques
	conversation['answer'] = reply
	

	# Get the current date and time
	# Print the current date and time
	conversation['date']=str(datetime.now().date())
	# conversation['date']=datetime.now().date()
	history.insert_one(conversation)

def history_retrive(username,email):
	query= {'username':username,'email':email}
	
	result=history.find(query)
	return result

def updatepassword(username,email):
	if request.method == 'POST':

		oldpassword = request.form['oldpassword']
		newpassword = request.form['newpassword']
		try:
			query= {"name":username,"email":email}
			result=users.find(query)
			for document in result:
				if "password" in document:
					print(document["password"])
					if oldpassword==document['password']:
						myquery = { "password": oldpassword }
						newvalues = { "$set": { "password": newpassword } }
						users.update_one(myquery, newvalues)
						return True
					else:
						return False
				else:
					return False
			
		except Exception as err:
			print("expect",err)

def feedback_insert(username,email,data):
	feedbackdata= {}
	feedbackdata['username'] = username
	feedbackdata['email'] = email
	feedbackdata['message'] = data['message']
	if 'image_path' in data:
		feedbackdata['image_path'] = data['image_path']
	else:
		feedbackdata['image_path'] = ""
	feedbackdata['date']=str(datetime.now().date())
	status=feedback.insert_one(feedbackdata)
	return status

def adminlogin():
	if request.method == 'POST':
		username = request.form.get('username')
		password = request.form.get('password')
		user = {
			"username": username,
			"password": password
		}

		user_data = admin.find_one(user)
		if user_data == None:
			return False
		else:
			return True
		
def admindata():
	
	data={}
	data['users']= users.count_documents({"status": "active"})
	data['blockedusers']= users.count_documents({"status": "block"})
	# Get the count of active users in the collection
	data['feedback']=feedback.count_documents({})
	data['conversations']=history.count_documents({})
	return data

def fetch_feedback():
	
	data=feedback.find()
	return data

def fetch_users():
	data=users.find()
	return data

def update_user():
	if request.method == 'POST':
		status = request.form.get('status')
		userid = request.form.get('id')
		objectid = ObjectId(userid)
		user = {
			"_id": objectid
		}
		data=users.find(user)
		
		for user_data in data: 
			# print(user_data)
			if user_data and 'status' in user_data:
				# print(user_data['status'])
				myquery={"status":user_data['status'],"_id":objectid}
				newvalues={"$set":{"status":status}}
				users.update_one(myquery,newvalues)

# def conversationcount():
# 	data=history.count_documents({})
# 	return data

def fetch_conversation(email):
	data=history.find({'email':email})
	return data
def delete_conversation():
	if request.method == 'POST':
		userid = request.form.get('id')
		history.delete_one({'_id': ObjectId(userid)})

def count_documents_by_email():
    pipeline = [
        {"$group": {"_id": "$email", "count": {"$sum": 1}}}
    ]
    result = history.aggregate(pipeline)
    email_counts = {doc["_id"]: doc["count"] for doc in result}
    return email_counts
